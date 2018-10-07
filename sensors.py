#!/usr/bin/python3

import RPi.GPIO as GPIO
import Adafruit_ADS1x15
import db_utils
import logging
from logging.handlers import RotatingFileHandler
import json
import datetime
import devices as devs
from queue import Queue
import threading
import sensors_utils


class Sensors:
	def __init__(self):
		try:
			self.loggerSetup()
			self.db = db_utils.DB_Connection()

			self.state = [True, False, False, False, False]	#read,fan,heat,light,water. What is currently on
			self.active_control = [False]*4				#fan,heating,light,irrigation. What is to be controlled
			self.cycle_timer = sensors_utils.TimerWrap()
			self.adc = Adafruit_ADS1x15.ADS1115()

			self.moist_sensors = []
			self.temp_hum_sensors = []
			self.fans = []
			self.heating = []
			self.grow_lights = []
			self.irrigation = []
			self.cameras = []

			self.devices = {}

			self.g_lights_schedule = []

			self.parse_devices()
			self.update_thresholds()
			self.update_rates()
			self.read_lights_schedule()
			self.start()

		except Exception as e:
			self.logger.exception(e)
			self.clean_up()

	def loggerSetup(self):
		self.logger = logging.getLogger(__name__)
		self.log_handler = RotatingFileHandler('static/log/sensors.log', maxBytes=1024*1024, backupCount=10)
		formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
		self.log_handler.setFormatter(formatter)
		self.logger.addHandler(self.log_handler)
		self.logger.setLevel(logging.DEBUG)

	def clean_up(self):
		if not self.state: return
		self.logger.info("Cleaning up...")

		self.set_act(self.fans, False)
		self.set_act(self.heating, False)
		self.set_act(self.grow_lights, False)
		self.set_act(self.irrigation, False)

		GPIO.cleanup()

		self.stop()
		self.db.clean_up()
		self.log_handler.close()
		self.logger.removeHandler(self.log_handler)
		self.state = False

	def set_state(self, new_state):
		if new_state[0] and not self.state[0]: self.start()
		elif not new_state[0]: self.stop()
		self.state = new_state

	def get_state(self):
		return self.state + [self.irrigation.get_state[2]]

	def set_act(self, who: list, *state):
		try:
			for name in who:
				dev = self.devices[name]
				now = sensors_utils.unix_now()

				active_since = dev.set_state(*state)
				if active_since>0:
					time = (now-active_since)/1000 #seconds
					if isinstance(dev, devs.Irrigation): l = time/60*dev.flow
					else: l = 0
					kwh = time*dev.wattage/3600000,
					cost = kwh*self.rates["elec_price"]+l*self.rates["water_price"]
					self.db.insert_device_record(dev.name, active_since, now, kwh, l, cost)
		except Exception as e:
			self.logger.warning("[Sensors.set_act]: something bad happened, who='{}' state='{}'\n\n{}".format(who, state, e))

	def get_act_state(self, who=[]):
		act_state = {}
		try:
			for name in who:
				act_state[name] = self.devices[name].get_state()
		except Exception as e:
			self.logger.warning("[Sensors.get_act_state]: something bad happened, what='{}' state='{}'\n\n{}".format(who, e))
		finally:
			return act_state

	def do_water_cycle(self, who=[]):
		if not who: who = self.irrigation
		for name in who:
			try:
				dev = self.devices[name]
				now = sensors_utils.unix_now()
				dev.water_cycle()
				kwh, l = dev.water_time*dev.wattage/60000, dev.water_time*dev.flow
				cost = kwh*self.rates["elec_price"]+l*self.rates["water_price"]
				self.db.insert_device_record((name, now, now+dev.water_time*60000, kwh, l, cost))
			except Exception as e:
				self.logger.warning("[Sensors.do_water_cycle]: something bad happened, who='{}'\n\n{}".format(who, e))

	def check_lights_schedule(self, who=[]):
		if not who: who = self.grow_lights
		now = sensors_utils.get_now()
		try:
			for job in self.g_lights_schedule:
				if job[0]<=now:

					if job[1]<0 and self.active_control[2]: #additional hours of light
						to_provide = self.thresholds['min_light_hours']-sensors_utils.get_day_len()
						if to_provide>0: job[1] = to_provide
						else: continue

					for name in who:
						dev = self.devices[name]
						dev.on_for_x_min(job[1]*60)
						kwh = job[1]*dev.wattage/(3600*1000)
						cost = kwh*self.rates["elec_price"]
						self.db.insert_device_record((name, now, now+job[1]*1000, kwh, 0, cost))
					if job[3]: job[1]+=job[3]
		except Exception as e:
			self.logger.warning("[Sensors.check_lights_schedule]: something bad happened, who='{}'\n\n{}".format(who, e))

	def update_thresholds(self, new_th = None):
		if new_th: self.thresholds = new_th
		else:
			with open('static/config/thresholds.json', 'r') as cfg_file:
				self.thresholds = json.loads(cfg_file.read())

	def update_rates(self, new_rates = None):
		if new_rates: self.rates = new_rates
		else:
			with open('static/config/costs_rates.json', 'r') as rates_file:
				self.rates = json.loads(rates_file.read())

	def read_lights_schedule(self):
		with open('static/config/grow_lights_schedule.json', 'r') as lights_file:
			jobs = json.loads(lights_file.read())
			self.g_light_schedule = []
			for job in jobs:
				when = datetime.datetime.strptime(job[0], '%Y-%m-%d %H:%M')
				hours = job[1]*60
				interval = datetime.timedelta(seconds=job[2])
				self.g_light_schedule.append([when, hours, interval])

	def write_lights_schedule(self):
		with open('static/config/grow_lights_schedule.json', 'w') as lights_file:
			schedule = []
			for job in self.g_light_schedule:
				when = job[0].strftime("%Y-%m-%d %H:%M")
				hours = job[1]
				interval = job[2].total_seconds()
				schedule.append([when, hours, interval])
			lights_file.write(str(schedule).replace("'", '"'))

	def start(self):
		self.logger.info("Initiating...")
		self.cycle()
		for c_name in self.cameras:
			self.devices[c_name].take_snapshot()

	def restart(self, interval=None):
		self.cycle_timer.reset()
		if not interval: interval = self.thresholds["interval_min"]
		self.cycle_timer.start(interval*60, self.cycle)
		self.state[0] = True

	def stop(self):
		self.state[0] = False
		self.cycle_timer.reset()
		for c in self.cameras: self.devices[c].stop()

	def cycle(self):
		try:
			self.logger.debug('Cycle')

			next_interval = None
			if self.state[0]:
				readings = self.read_sensors()
				self.operate(readings)
				if True in self.state[1:]: next_interval = 1 # check after 1 min instead of standard interval
			self.restart(next_interval)
		except Exception as e:
			self.logger.exception(e)
			self.clean_up()

	def sensor_read_wrapper(self, sensor, queue):
		queue.put(sensor.read())

	def read_sensors(self):
		self.logger.debug("Reading sensors...")
		threads, q_moist, q_th = [], Queue(), Queue()

		for s_name in self.moist_sensors:
			t = threading.Thread(target=self.sensor_read_wrapper, args=(self.devices[s_name], q_moist))
			threads.append(t)
			t.start()

		for s_name in self.temp_hum_sensors:
			t = threading.Thread(target=self.sensor_read_wrapper, args=(self.devices[s_name], q_th))
			threads.append(t)
			t.start()

		for t in threads: t.join()

		m_min, m_max, m_avg, m_good = 101, -1, 0, 0
		while not q_moist.empty():
			reading = q_moist.get()
			if reading is not None:
				if reading<m_min: m_min = reading
				if reading>m_max: m_max = reading
				m_avg+=reading
				m_good+=1
		if m_good: m_avg = round(m_avg/m_good, 1)
		else: m_avg = None
		self.logger.debug("[Sensors.read_sensors]: m_min={}, m_max={}, m_avg={}, m_good={}".format(m_min, m_max, m_avg, m_good))
		if (m_max-m_min)>self.thresholds["moist_max_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Moist readings differ too much (min:{}, max:{})".format(m_min, m_max))

		th_min, th_max, th_avg, th_good = [100, 101], [-274, -1], [0, 0], [0, 0]
		while not q_th.empty():
			reading = q_th.get()
			if reading[0] is not None:
				if reading[0]<th_min[0]: th_min[0] = reading[0]
				if reading[0]>th_max[0]: th_max[0] = reading[0]
				th_avg[0]+=reading[0]
				th_good[0]+=1
			if reading[1] is not None:
				if reading[1]<th_min[1]: th_min[1] = reading[1]
				if reading[1]>th_max[1]: th_max[1] = reading[1]
				th_avg[1]+=reading[1]
				th_good[1]+=1
		if th_good[0]: th_avg[0] = round(th_avg[0]/th_good[0], 1)
		else: th_avg[0] = None
		if th_good[1]: th_avg[1] = round(th_avg[1]/th_good[1], 1)
		else: th_avg[1] = None

		self.logger.debug("[Sensors.read_sensors]: th_min={}, th_max={}, th_avg={}, th_good={}".format(th_min, th_max, th_avg, th_good))
		if (th_max[0]-th_min[0])>self.thresholds["dht22_max_temp_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Temp readings differ too much (min:{}, max:{})".format(th_min[0], th_max[0]))
		if (th_max[1]-th_min[1])>self.thresholds["dht22_max_hum_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Hum readings differ too much (min:{}, max:{})".format(th_min[1], th_max[1]))

		readings = [sensors_utils.unix_now()] + th_avg + [m_avg]
		self.db.insert_sensors_reading(readings)

		return readings

	def operate(self, readings): #[dt, temp, hum, moist]
		#fans
		if self.active_control[0]:
			if readings[1]>self.thresholds['max_temp'] and not self.state[1]:
				self.logger.info("Temperature is too high ({}°C), turning on the fans".format(readings[1]))
				self.set_act(self.fans, True, 100)
				self.set_act(self.heating, False)
				self.state[1] = True
			elif readings[2]>self.thresholds['max_hum'] and not self.state[1]:
				self.logger.info("Humidity is too high ({}%), turning on the fans".format(readings[2]))
				self.set_act(self.fans, True, 50)
				self.state[1] = True
			elif self.state[1]:
				self.logger.info("Turning off the fans, no need for them anymore")
				self.set_act(self.fans, False)
				self.state[1] = False

		#heating
		if self.active_control[1]:
			if readings[1]<self.thresholds['min_temp'] and not self.state[2]:
				self.logger.info("Temperature is too low ({}°C), turning on the heating".format(readings[1]))
				self.set_act(self.heating, True)
				self.state[2] = True
			elif self.state[2]:
				self.logger.info("Turning off the heating, no need for it anymore")
				self.set_act(self.heating, False)
				self.state[2] = False

		#grow_lights
		self.check_lights_schedule(self.grow_lights)
		self.write_lights_schedule()

		#irrigation
		if self.active_control[3]:
			ws = self.irrigation.get_state()
			if readings[3]<self.thresholds['min_soil_moist'] and not ws[0] and ws[2]==0:
				self.logger.info("Soil moisture is too low ({}%), turning on the water".format(readings[3]))
				self.set_act(self.irrigation, 'water_cycle')
			elif ws[0] and readings[3]>self.thresholds['max_soil_moist']:
				self.logger.warning("Turning off the water. Soil moisture is {}% (should be under {}), watering_state: {}".format(readings[3], self.thresholds['max_soil_moist'], ws[2]))
				self.set_act(self.irrigation, False)

	def parse_devices(self):
		try:
			with open('static/config/devices.json', 'r') as devs_file:
				devs = json.loads(devs_file.read()):

				for dev in devs['soil_moisture_sensors']:
					if dev['model']=='generic_analog':
						self.devices[dev['name']] = devs.SoilMoistureSensor(self.adc, dev['adc_channel'], dev['100_voltage'], dev['0_voltage'], dev['adc_gain'])
					if dev['enabled']: self.moist_sensors.append(dev['name'])

				for dev in devs['temp_hum_sensors']:
					if dev['model']=='DHT22':
						self.devices[dev['name']] = devs.DHT22(dev['GPIO_pin'], dev['max_reading_attempts'])
					elif dev['model']=='SHT31-D':
						pass #TODO
					if dev['enabled']: self.temp_hum_sensors.append(dev['name'])

				for dev in devs['fans']:
					if dev['model']=='pwm_fan':
						self.devices[dev['name']] = devs.Fan(dev['GPIO_switch_pin'], dev['GPIO_speed_pin'], dev['wattage'], dev['pwm_frequency'])
					if dev['enabled']: self.fans.append(dev['name'])

				for dev in devs['cameras']:
					if dev['model']=='ip_camera':
						self.devices[dev['name']] = devs.IP_Camera(dev['name'], dev['user'], dev['password'], dev['ip'], dev['snapshot_dir'], dev['wattage'], dev['snapshot_interval_h'])
					if dev['enabled']: self.cameras.append(dev['name'])

				for dev in devs['irrigation']:
					if dev['model']=='simple_switch':
						self.devices[dev['name']] = devs.Irrigation(dev['GPIO_switch_pin'], dev['wattage'], dev['water_flow'], dev['cycle_water_time'], dev['cycle_wait_time'])
					if dev['enabled']: self.irrigation.append(dev['name'])

				for dev in devs['heating']:
					if dev['model']=='simple_switch':
						self.devices[dev['name']] = devs.Switch(dev['GPIO_switch_pin'], dev['wattage'])
					if dev['enabled']: self.heating.append(dev['name'])

				for dev in devs['grow_lights']:
					if dev['model']=='simple_switch':
						self.devices[dev['name']] =	devs.GrowLight(dev['GPIO_switch_pin'], dev['wattage'])
					if dev['enabled']: self.grow_lights.append(dev['name'])

		except Exception as e:
			self.logger.exception("[Sensors.parse_devices]: {}".format(e))

		#print("[Sensors.parse_devices]: {}".format(self.devices))
