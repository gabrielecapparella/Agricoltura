#!/usr/bin/python3

import RPi.GPIO as GPIO
import db_utils
import logging
from logging.handlers import RotatingFileHandler
import time
import Adafruit_DHT
import Adafruit_ADS1x15
from threading import Timer
import json
import subprocess
import datetime
from shutil import copyfile
import requests
from dateutil import tz
import devices
from queue import Queue
import threading


class Lightbulb(devices.Switch):
	def __init__(self, pin, db):
		super().__init__(pin)
		self.was_set_by_human = False
		self.db = db

	def set_state(self, target=True, was_set_by_human=True):
		if target: super().on()
		else:
			now = super().off()
			if self.active_since: self.db.insert_actuator_record(("light", self.active_since, now))
		self.was_set_by_human = was_set_by_human


class Irrigation(devices.Pump):
	def __init__(self, pin, db):
		super().__init__(pin)
		self.watering_state = 0 #0:inactive, 1:watering, 2:propagating
		self.was_set_by_human = False
		self.db = db

	def get_state(self):
		return super().get_state()+[self.watering_state]

	def set_state(self, target=True, was_set_by_human=True, w_state=0):
		if target: super().on()
		else:
			now = super().off()
			if self.active_since: self.db.insert_actuator_record(("water", self.active_since, now))
		self.was_set_by_human = was_set_by_human
		self.watering_state = w_state

	def water_cycle(self):
		ws = self.watering_state
		if ws==0:
			self.logger.debug("[Sensors.water_cycle]: water on.")
			self.set_state(True, False, 1)
			self.timer.start(1*60, self.water_cycle)	#water for 1min
		elif ws==1:
			self.logger.debug("[Sensors.water_cycle]: water off.")
			self.set_state(False, False, 2)
			self.timer.start(10*60, self.water_cycle)	#wait for 10min while it spreads
		elif ws==2:
			self.logger.debug("[Sensors.water_cycle]: cycle finished.")
			self.set_state(False, False, 0)


class GH_Fan(devices.Fan):
	def __init__(self, power_pin, speed_pin, db, frequency=25000, default_speed=100.0):
		super().__init__(power_pin, speed_pin, frequency, default_speed)
		self.was_set_by_human = False
		self.db = db

	def set_state(self, target=True, new_speed=None, was_set_by_human=True):
		if new_speed==None: new_speed = self.speed

		if target and new_speed>0: super().on(new_speed)
		elif not target and self.state:
			now = super().off()
			if self.active_since: self.db.insert_actuator_record(("fan", self.active_since, now))
		elif target and self.state: super().set_speed(new_speed)

		self.speed = new_speed
		self.was_set_by_human = was_set_by_human


class Sensors:
	def __init__(self):
		try:
			self.loggerSetup()

			self.db = db_utils.DB_Connection()

			self.is_operative = False
			self.is_running = False
			self.light_hours = False
			self.state = True
			self.gpio_cfg = self.get_gpio_cfg()
			self.cam_cfg = self.get_cam_cfg()

			self.cycle_timer = None
			
			#GPIO.cleanup()

			self.adc = Adafruit_ADS1x15.ADS1115()

			self.moist_sensors = [
				devices.SoilMoistureSensor(
					self.adc,
					self.gpio_cfg['moist_adc_ch_1'],
					self.gpio_cfg['moist_min'],
					self.gpio_cfg['moist_max']
				),
				devices.SoilMoistureSensor(
					self.adc,
					self.gpio_cfg['moist_adc_ch_2'],
					self.gpio_cfg['moist_min'],
					self.gpio_cfg['moist_max']
				)
			]

			self.temp_hum_sensors = [
				devices.DHT22(self.gpio_cfg['dht22_1']),
				devices.DHT22(self.gpio_cfg['dht22_2'])
			]

			self.camera = devices.IP_Camera(
				self.cam_cfg['usr'],
				self.cam_cfg['pwd'],
				self.cam_cfg['ip'],
				self.cam_cfg['snapshot_dir']
			)

			self.water = Irrigation(self.gpio_cfg['water'], self.db)
			self.light = Lightbulb(self.gpio_cfg['light'], self.db)
			self.fan = GH_Fan(self.gpio_cfg['fan'], self.gpio_cfg['fan_speed'], self.db)

			self.update_thresholds()

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

		self.water.set_state(False)
		self.light.set_state(False)
		self.fan.set_state(False)
		GPIO.cleanup()

		self.stop()
		self.db.clean_up()
		self.log_handler.close()
		self.logger.removeHandler(self.log_handler)
		self.state = False

	def set_operative(self, state=True):
		self.is_operative = state

	def set_running(self, state=True):
		if state: self.start()
		else: self.stop()
		
	def get_gpio_cfg(self):
		with open('static/config/devices.json', 'r') as cfg_file:
			return json.loads(cfg_file.read())	
			
	def get_cam_cfg(self):
		with open('static/config/ip_camera.json', 'r') as cfg_file:
			return json.loads(cfg_file.read())

	def update_thresholds(self):
		with open('static/config/sensors_config.json', 'r') as cfg_file:
			self.thresholds = json.loads(cfg_file.read())
			self.camera.interval = self.thresholds['cam_h']*60*60

	def start(self):
		self.logger.info("Initiating...")
		self.cycle()
		self.camera.take_snapshot()


	def restart(self, interval=None):
		if self.cycle_timer and self.cycle_timer.is_alive(): self.cycle_timer.cancel()
		if not interval: interval = self.thresholds["interval_min"]

		self.cycle_timer = Timer(interval*60, self.cycle)
		self.cycle_timer.start()
		self.is_running = True

	def stop(self):
		self.is_running = False
		if self.cycle_timer and self.cycle_timer.is_alive(): self.cycle_timer.cancel()
		self.camera.timer.reset()

	def cycle(self):
		try:
			self.logger.debug('Cycle')
			readings = self.read_sensors()
			next_interval = None

			if self.is_operative:
				op = self.operate(readings)
				self.logger.debug('[Sensors.operate]: {}'.format(op))
				if op: next_interval = 1 #check after 1 min instead of standard interval
			self.restart(next_interval)
		except Exception as e:
			self.logger.exception(e)
			self.clean_up()

	def get_lh_provided(self, day):
		prov = 0
		day = db_utils.datetime2unix(day)
		for i in self.db.get_light_hours(day):
			prov+=(i[2]-i[1])
		h_prov = round(prov/3600000, 1)
		return h_prov

	def get_lh_to_provide(self):
		h = self.thresholds['min_light_hours']
		dl = self.get_day_len()
		h -= dl

		h -= self.get_lh_provided(self.get_now().date())
		return h			
			
	def sensor_read_wrapper(self, sensor, queue):
		queue.put(sensor.read())

	def read_sensors(self):
		self.logger.debug("Reading sensors...")
		threads, q_moist, q_th = [], Queue(), Queue()
		
		for sensor in self.moist_sensors:
			t = threading.Thread(target=self.sensor_read_wrapper, args=(sensor, q_moist))
			threads.append(t)
			t.start()
			
		for sensor in self.temp_hum_sensors:
			t = threading.Thread(target=self.sensor_read_wrapper, args=(sensor, q_th))
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
		if (m_max-m_min)>self.gpio_cfg["moist_max_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Moist readings differ too much (min:{}, max:{})".format(m_min, m_max))

		th_min, th_max, th_avg, th_good = [100,101], [-274,-1], [0,0], [0,0]
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
		if (th_max[0]-th_min[0])>self.gpio_cfg["dht22_max_temp_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Temp readings differ too much (min:{}, max:{})".format(th_min[0], th_max[0]))
		if (th_max[1]-th_min[1])>self.gpio_cfg["dht22_max_hum_delta"]:
				self.logger.warning("[Sensors.read_sensors]: Hum readings differ too much (min:{}, max:{})".format(th_min[1], th_max[1]))

		readings = [self.db.unix_now()] + th_avg + [m_avg]
		self.db.insert_sensors_reading(readings)

		return readings


	#returns 0 if no actuator is on
	def operate(self, readings): #[dt, temp, hum, moist]
		p = 0
		h = self.get_now().hour
		#fan
		if readings[1]>self.thresholds['max_temp']:
			if not self.fan.get_state()[0]:
				self.logger.info("Temperature is {}, turning on the fan".format(readings[1]))
				self.fan.set_state(True, 100, False)
				p+=1
		elif readings[2]>self.thresholds['max_hum']:
			if not self.fan.get_state()[0]:
				self.logger.info("Humidity is {}, turning on the fan".format(readings[2]))
				self.fan.set_state(True, 50, False)
				p+=1
		elif self.fan.get_state()[0] and not self.fan.was_set_by_human:
			self.logger.info("Turning off the fan, no need for it")
			self.fan.set_state(False, False)


		#light
		if readings[1]<self.thresholds['min_temp']:
			if not self.light.get_state():
				self.logger.info("Temperature is too low ({}°C), turning on the light".format(readings[1]))
				self.light.set_state(True, False)
				p+=2
		elif readings[1]>self.thresholds['max_temp'] and self.light.get_state():
			self.logger.info("Temperature is too high ({}°C), turning off the light".format(readings[1]))
			self.light.set_state(False, False)
		elif h>18 and self.get_lh_to_provide()>0:
			self.logger.info("There were not enough light hours today [{}], turning on the light".format(self.light_hours))
			self.light.set_state(True, False)
			p+=2
		elif self.light.get_state() and not self.light.was_set_by_human:
			self.logger.info("Turning off the light, no need for it")
			self.light.set_state(False, False)


		#water
		ws = self.water.get_state()
		if readings[3]<self.thresholds['min_soil_moist'] and not ws[0] and ws[1]==0:
			self.logger.info("Soil moisture is {}, turning on the water".format(readings[3]))
			self.water.water_cycle()
			p+=4
		elif ws[0] and readings[3]>self.thresholds['max_soil_moist']:
			self.logger.warning("Turning off the water. Soil moisture is {}% (should be under {}), was set by human: {}".format(readings[3], self.thresholds['max_soil_moist'], self.water.was_set_by_human) )
			self.water.set_state(False, False)

		return p

	def get_day_len(self):
		self.logger.debug("Getting day len...")
		try:
			response = requests.get('http://api.sunrise-sunset.org/json?lat=41.794940&lng=12.374707')
			hms = response.json()['results']['day_length'].split(':')
			return round(int(hms[0])+int(hms[1])/60, 1)
		except:
			return False

	def get_now(self):
		from_zone = tz.gettz('UTC')
		to_zone = tz.gettz('Europe/Rome')
		dt = datetime.datetime.now()
		dt = dt.replace(tzinfo=from_zone)
		return dt.astimezone(to_zone)
