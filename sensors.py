#!/usr/bin/python3

import RPi.GPIO as GPIO
import Adafruit_ADS1x15
import db_utils
import logging
from logging.handlers import RotatingFileHandler
import json
import datetime
import devices as devs
from threading import Thread
import sensors_utils
import traceback

class Sensors:
	def __init__(self):
		try:
			self.loggerSetup()
			self.db = db_utils.DB_Connection()

			self.state = [True, False, False, False, None]	#read,fan,heat,light,water. What is currently on
			self.active_control = [False]*4				#fan,heating,light,irrigation. What is to be controlled
			self.last_reading = None
			self.cycle_timer = sensors_utils.TimerWrap()
			self.reading_thread = None
			self.adc = Adafruit_ADS1x15.ADS1115()

			self.devices = {}
			self.enabled_devs = {
				'soil_moist_sensors': [],
				'temp_hum_sensors': [],
				'fans': [],
				'cameras': [],
				'irrigation': [],
				'heating': [],
				'grow_lights': []
			}

			self.g_lights_schedule = []

			with open('static/config/deltas.json', 'r') as delta_file:
				self.dev_deltas = json.loads(delta_file.read())

			self.parse_devices()
			self.update_thresholds()
			self.update_rates()
			self.read_lights_schedule()
			self.start()

		except Exception as e:
			self.logger.exception(traceback.format_exc())
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

		# add cameras cost
		self.set_act(self.devices.keys(), False)

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
		return self.state

	def set_act(self, who: list, *state):
		try:
			for name in who:
				dev = self.devices[name]
				now = sensors_utils.unix_now()

				active_since = dev.set_state(*state)
				if active_since>0:
					time = (now-active_since)/1000 #seconds
					if isinstance(dev, devs.Irrigation): l = time/60*dev.flow #this is for manual control, not water_cycle
					else: l = 0
					kwh = time*dev.wattage/3600000
					cost = kwh*self.rates["elec_price"]+l*self.rates["water_price"]
					self.db.insert_device_record((dev.name, active_since, now, kwh, l, cost))
		except Exception as e:
			self.logger.warning("[Sensors.set_act]: something bad happened, who='{}' state='{}'\n\n{}".format(who, state, traceback.format_exc()))

	def get_dev_state(self, who): #who can be an object or a list of objects
		try:
			if isinstance(who, list):
				act_state = {}
				for name in who:
					act_state[name] = self.devices[name].get_state()
			else: act_state = self.devices[who].get_state()
		except Exception as e:
			self.logger.warning("[Sensors.get_dev_state]: something bad happened, what='{}' state='{}'\n\n{}".format(who, traceback.format_exc()))
		finally:
			return act_state

	def get_full_state(self):
		full_state = {}
		for dev_type, dev_list in self.enabled_devs.items():
			full_state[dev_type] = self.get_dev_state(dev_list)
		full_state["active_control"] = self.active_control
		full_state["averages"] = self.last_reading
		return full_state

	def water_cycle_callback(self, dev):
		try:
			if dev.name in self.state[4]: self.state[4].remove(dev.name)
			now = sensors_utils.unix_now()
			kwh, l = dev.water_time*dev.wattage/60000, dev.water_time*dev.flow
			cost = kwh*self.rates["elec_price"]+l*self.rates["water_price"]
			self.db.insert_device_record((dev.name, dev.active_since, now, kwh, l, cost))
		except Exception as e:
			self.logger.warning("[Sensors.water_cycle_callback]: something bad happened, who='{}'\n\n{}".format(dev.name, traceback.format_exc()))

	def check_lights_schedule(self, who=[]):
		if not who: who = self.enabled_devs['grow_lights']
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
						self.db.insert_device_record((name, now, now+job[1]*1000, kwh, 0, cost)) #sistemare quel *1000
					if job[3]: job[1]+=job[3]
		except Exception as e:
			self.logger.warning("[Sensors.check_lights_schedule]: something bad happened, who='{}'\n\n{}".format(who, traceback.format_exc()))

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
				hours = job[1]
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
		for c_name in self.enabled_devs['cameras']:
			self.devices[c_name].take_snapshot()

	def restart(self, interval=None):
		self.cycle_timer.reset()
		if not interval: interval = self.thresholds["interval_min"]
		self.cycle_timer.start(interval*60, self.cycle)
		self.state[0] = True

	def stop(self):
		self.state[0] = False
		self.cycle_timer.reset()
		for c in self.enabled_devs['cameras']: self.devices[c].stop()

	def cycle(self):
		try:
			self.logger.debug('Cycle')
			if self.state[0]:
				self.reading_thread = Thread(target=self.read_sensors)
				self.reading_thread.start()
			else: self.restart()
		except Exception as e:
			self.logger.exception(traceback.format_exc())
			self.clean_up()

	def read_sensors_callback(self, results):
		self.logger.debug("[Sensors.read_sensors_callback]: results={}".format(results))
		if (results["moist"]["max"]-results["moist"]["min"])>self.dev_deltas["moist_max_delta"]:
			self.logger.warning("[Sensors.read_sensors]: Moist readings differ too much (min:{}, max:{})".format(results["moist"]["min"], results["moist"]["max"]))
		if (results["temp"]["max"]-results["temp"]["min"])>self.dev_deltas["max_temp_delta"]:
			self.logger.warning("[Sensors.read_sensors]: Temp readings differ too much (min:{}, max:{})".format(results["temp"]["min"], results["temp"]["max"]))
		if (results["hum"]["max"]-results["hum"]["min"])>self.dev_deltas["max_hum_delta"]:
			self.logger.warning("[Sensors.read_sensors]: Hum readings differ too much (min:{}, max:{})".format(results["hum"]["min"], results["hum"]["max"]))

		readings = [sensors_utils.unix_now()]
		readings.append(results["temp"]["avg"])
		readings.append(results["hum"]["avg"])
		readings.append(results["moist"]["avg"])

		self.db.insert_sensors_reading(readings)
		self.last_reading = readings

		self.operate(readings)
		next_interval = None
		if True in self.state[1:]: next_interval = 1 # check after 1 min instead of standard interval
		self.restart(next_interval)

	def read_sensors(self):
		self.logger.debug("Reading sensors...")

		results = {
			"moist": {"min": 101,"max": -1,"avg": 0,"good": 0},
			"temp": {"min": 100,"max": -274,"avg": 0,"good": 0},
			"hum": {"min": 101,"max": -1,"avg": 0,"good": 0}
		}

		for s_name in self.enabled_devs['soil_moist_sensors']:
			reading = self.devices[s_name].read()
			if reading is not None:
				if reading<results["moist"]["min"]: results["moist"]["min"] = reading
				if reading>results["moist"]["max"]: results["moist"]["max"] = reading
				results["moist"]["avg"] += reading
				results["moist"]["good"] += 1
		if results["moist"]["good"]:
			results["moist"]["avg"] = round(results["moist"]["avg"]/results["moist"]["good"], 1)
		else: results["moist"]["avg"] = None

		for s_name in self.enabled_devs['temp_hum_sensors']:
			reading = self.devices[s_name].read()
			if reading[0] is not None:
				if reading[0]<results["temp"]["min"]: results["temp"]["min"] = reading[0]
				if reading[0]>results["temp"]["max"]: results["temp"]["max"] = reading[0]
				results["temp"]["avg"]+=reading[0]
				results["temp"]["good"]+=1
			if reading[1] is not None:
				if reading[1]<results["hum"]["min"]: results["hum"]["min"] = reading[1]
				if reading[1]>results["hum"]["max"]: results["hum"]["max"] = reading[1]
				results["hum"]["avg"]+=reading[1]
				results["hum"]["good"]+=1
		if results["temp"]["good"]: results["temp"]["avg"] = round(results["temp"]["avg"]/results["temp"]["good"], 1)
		else: results["temp"]["avg"] = None
		if results["hum"]["good"]: results["hum"]["avg"] = round(results["hum"]["avg"]/results["hum"]["good"], 1)
		else: results["hum"]["avg"] = None

		self.read_sensors_callback(results)

	def operate(self, readings): #[dt, temp, hum, moist]
		#fans
		if self.active_control[0]:
			if readings[1]>self.thresholds['max_temp'] and not self.state[1]:
				self.logger.info("Temperature is too high ({}°C), turning on the fans".format(readings[1]))
				self.set_act(self.enabled_devs['fans'], True, 100)
				self.set_act(self.enabled_devs['heating'], False)
				self.state[1] = True
			elif readings[2]>self.thresholds['max_hum'] and not self.state[1]:
				self.logger.info("Humidity is too high ({}%), turning on the fans".format(readings[2]))
				self.set_act(self.enabled_devs['fans'], True, 50)
				self.state[1] = True
			elif self.state[1]:
				self.logger.info("Turning off the fans, no need for them anymore")
				self.set_act(self.enabled_devs['fans'], False)
				self.state[1] = False

		#heating
		if self.active_control[1]:
			if readings[1]<self.thresholds['min_temp'] and not self.state[2]:
				self.logger.info("Temperature is too low ({}°C), turning on the heating".format(readings[1]))
				self.set_act(self.enabled_devs['heating'], True)
				self.state[2] = True
			elif self.state[2]:
				self.logger.info("Turning off the heating, no need for it anymore")
				self.set_act(self.enabled_devs['heating'], False)
				self.state[2] = False

		#grow_lights
		self.check_lights_schedule(self.enabled_devs['grow_lights'])
		self.write_lights_schedule()

		#irrigation
		if self.active_control[3]:
			ws = self.irrigation.get_state() #WAT
			if readings[3]<self.thresholds['min_soil_moist'] and not self.state[4]:
				self.logger.info("Soil moisture is too low ({}%), turning on the water".format(readings[3]))
				self.set_act(self.enabled_devs['irrigation'], 'water_cycle')
				self.state[4] = self.enabled_devs['irrigation']
			elif readings[3]>self.thresholds['max_soil_moist']:
				self.logger.warning("Turning off the water. Soil moisture is {}% (should be under {}), watering_state: {}".format(readings[3], self.thresholds['max_soil_moist'], ws[2]))
				self.set_act(self.enabled_devs['irrigation'], False)

	def delete_device(self, name, cfg):
		try:
			dev_type = cfg['model'].split('__')[0]
			if name in self.devices:
				self.set_act([name], False)
				del self.devices[name]
				if name in self.enabled_devs[dev_type]:
					self.enabled_devs[dev_type].remove(name)
		except Exception as e:
			self.logger.exception("[Sensors.delete_device]: {}".format(traceback.format_exc()))

	def update_device(self, old_name, new_cfg):
		self.delete_device(old_name, new_cfg)
		return self.add_device(new_cfg)

	def add_device(self, dev):
		try:
			if dev['model'] == 'soil_moist_sensors__generic_analog':
				self.devices[dev['name']] = devs.SoilMoistureSensor(adc=self.adc, **dev)

			elif dev['model'] == 'temp_hum_sensors__DHT22':
				self.devices[dev['name']] = devs.DHT22(**dev)
			elif dev['model'] == 'temp_hum_sensor__SHT31':
				pass

			elif dev['model'] == 'fans__pwm_fan':
				self.devices[dev['name']] = devs.Fan(**dev)

			elif dev['model'] == 'cameras__ip_camera':
				self.devices[dev['name']] = devs.IP_Camera(**dev)

			elif dev['model'] == 'irrigation__simple_switch':
				self.devices[dev['name']] = devs.Irrigation(**dev)

			elif dev['model'] == 'heating__simple_switch':
				self.devices[dev['name']] = devs.Switch(**dev)

			elif dev['model'] == 'grow_lights__simple_switch':
				self.devices[dev['name']] =	devs.GrowLight(**dev)

			dev_type = dev['model'].split('__')[0]
			if dev['enabled']: self.enabled_devs[dev_type].append(dev['name'])
			return True
		except Exception as e:
			self.logger.exception("[Sensors.add_device]: {}".format(traceback.format_exc()))
			return False

	def parse_devices(self, devs=None):
		try:
			if not devs:
				with open('static/config/devices.json', 'r') as devs_file:
					devs = json.loads(devs_file.read())

			for device in devs:
				self.add_device(device)
		except Exception as e:
			self.logger.exception("[Sensors.parse_devices]: {}".format(traceback.format_exc()))
