#!/usr/bin/python3

import RPi.GPIO as GPIO
import Adafruit_DHT
import time
import subprocess
import threading
import sensors_utils
import os

class Passive:
	def __init__(self, name, model, wattage, **kwargs):
		self.name = name
		self.model_type = model.split("__")[0]
		self.wattage = wattage
		self.start_time = sensors_utils.unix_now()

	def get_state(self):
		uptime = sensors_utils.unix_now()-self.start_time
		uptime /= (3600*1000) # hours
		kwh = self.wattage*uptime/1000
		return [uptime, kwh, 0]

	def set_state(self, target):
		return False

class Switch:
	def __init__(self, name, model, power_pin, wattage, **kwargs):
		self.name = name
		self.model_type = model.split("__")[0]
		self.pin = power_pin #BCM
		self.state = False
		self.active_since = None
		self.wattage = wattage

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.pin, GPIO.OUT)
		GPIO.output(self.pin, True) #off

	def get_state(self):
		return self.state

	def set_state(self, target=True):
		if target: return self.on()
		else: return self.off()

	def on(self):
		if self.state: return False
		GPIO.output(self.pin, False)
		self.state = True
		self.active_since = sensors_utils.unix_now()
		return 0

	def off(self):
		if not self.state: return False
		GPIO.output(self.pin, True)
		self.state = False
		return self.active_since

class Irrigation(Switch):
	def __init__(self, name, model, power_pin, wattage, water_flow, cycle_water_time=1, cycle_spread_time=10, **kwargs):
		super().__init__(name, model, power_pin, wattage)
		self.watering_state = 0 #0:inactive, 1:watering, 2:propagating
		self.water_time = cycle_water_time
		self.spread_time = cycle_spread_time
		self.flow = water_flow
		self.timer = sensors_utils.TimerWrap()
		self.callback = None

	def get_state(self):
		return [self.state, self.timer.remaining(), self.watering_state]

	def set_state(self, target=True, w_state=-1):
		if not target and w_state==-1:
			self.timer.reset()
			self.watering_state = 0
			if self.callback: self.callback(self)
			return super().set_state(False)

		self.watering_state = w_state
		return super().set_state(target)


	def water_cycle(self, callback=None):
		ws = self.watering_state
		if ws==0:
			self.set_state(True, 1)
			self.timer.start(self.water_time*60, self.water_cycle)
			if callback: self.callback = callback
		elif ws==1:
			self.set_state(False, 2)
			self.timer.start(self.spread_time*60, self.water_cycle)	#wait while it spreads
		elif ws==2:
			if self.callback:
				self.callback(self)
				self.callback = None

class Fan(Switch):
	def __init__(self, name, model, power_pin, speed_pin, wattage, pwm_frequency=25000, **kwargs):
		super().__init__(name, model, power_pin, wattage)
		self.speed = 100

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(speed_pin, GPIO.OUT)
		self.speed_ctrl = GPIO.PWM(speed_pin, pwm_frequency)

	def get_state(self):
		return [self.state, self.speed]

	def set_state(self, target=True, new_speed=None):
		if new_speed==None: new_speed = self.speed

		self.speed = new_speed
		if target and new_speed>0: return self.on(new_speed)
		elif not target and self.state:	return self.off()
		elif target and self.state: return self.set_speed(new_speed)
		return 0

	def on(self, speed=-1):
		if speed<0: speed = self.speed
		speed = float(speed)
		if speed==0: return super().off()
		if super().get_state(): return self.set_speed(speed)
		else:
			self.speed_ctrl.start(speed)
			return super().on()

	def off(self):
		self.speed_ctrl.stop()
		return super().off()

	def set_speed(self, new_speed):
		new_speed = float(new_speed)
		self.speed_ctrl.ChangeDutyCycle(new_speed)
		return 0

class GrowLight(Switch):
	def __init__(self, name, model, power_pin, wattage, **kwargs):
		super().__init__(name, model, power_pin, wattage)
		self.timer = sensors_utils.TimerWrap()

	def on_for_x_min(self, minutes):
		self.on()
		self.timer.start(minutes*60, self.off)

class SoilMoistureSensor:
	def __init__(self, name, adc, adc_channel, wet_voltage, dry_voltage, adc_gain=2/3, **kwargs):
		self.name = name
		self.adc = adc
		self.channel = adc_channel
		self.wet_voltage = wet_voltage #100%
		self.dry_voltage = dry_voltage #0%
		self.gain = adc_gain
		self.last_reading = None

	def get_state(self):
		return self.last_reading

	def set_state(self, state):
		return False

	def read(self): #throws
		raw_value = self.adc.read_adc(self.channel, gain=self.gain)
		perc = (raw_value-self.wet_voltage)*100/(self.dry_voltage-self.wet_voltage)
		perc = round(abs(100-perc), 1)
		if perc<0: perc = 0
		elif perc>100: perc = 100
		self.last_reading = perc
		return self.last_reading

class SHT31:
	def __init__(self, name, model, bus, address, **kwargs):
		self.name = name
		self.model_type = model.split("__")[0]
		self.bus = bus
		if isinstance(address, str): address = int(address, 16)
		self.address = address
		self.last_reading = None

	def get_state(self):
		return self.last_reading

	def set_state(self, state):
		return False

	def read(self): #throws
		self.bus.write_i2c_block_data(self.address, 0x2C, [0x06])
		time.sleep(0.5)
		data = self.bus.read_i2c_block_data(self.address, 0x00, 6)
		temp = data[0] * 256 + data[1]
		cTemp = -45 + (175 * temp / 65535.0) # celsius
		humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
		self.last_reading = [round(cTemp,1), round(humidity,1)]
		return self.last_reading

class DHT22:
	def __init__(self, name, model, read_pin, max_reading_attempts=3, **kwargs):
		self.name = name
		self.model_type = model.split("__")[0]
		self.pin = read_pin
		self.attempts = max_reading_attempts
		self.last_reading = None

	def get_state(self):
		return self.last_reading

	def set_state(self, state):
		return False

	def read(self): #throws
		reading = [None, None]
		for attempt in range(self.attempts):
			h,t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.pin)
			if h!=None and t!=None and h<=100:
				reading = [round(t, 1),round(h, 1)]
				break
			time.sleep(5)
		self.last_reading = reading
		return self.last_reading

class IP_Camera(Passive):
	def __init__(self, name, model, usr, pwd, ip, snapshot_dir, wattage, interval=-1, **kwargs):
		super().__init__(name, model, wattage)
		self.usr = usr
		self.pwd = pwd
		self.ip = ip
		self.snapshot_dir = snapshot_dir
		self.interval = interval
		self.timer = sensors_utils.TimerWrap()
		self.last_returncode = None

	def take_snapshot(self):
		now = sensors_utils.get_now()
		folder = self.snapshot_dir+now.strftime("%Y-%m-%d")
		filename = folder+now.strftime("%Y-%m-%d_%H-%M-%S")+'_'+self.name+'.jpg'
		os.makedirs(folder,exist_ok=True)

		cmd = 'ffmpeg -y -rtsp_transport tcp -i "rtsp://'+self.usr+':'+self.pwd+'@'+self.ip+'/11" -frames 1 '+filename
		t = threading.Thread(target=self.call_ffmpeg, args=(cmd,))
		t.start()
		if self.interval>0: self.timer.start(self.interval, self.take_snapshot)

	def call_ffmpeg(self, cmd):
		sub = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		self.last_returncode = sub.wait()

	def stop(self):
		self.interval = -1
		self.timer.reset()

	def get_state(self):
		return super().get_state()+[self.timer.remaining()]

	def set_state(self, state):
		return False
