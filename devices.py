#!/usr/bin/python3

import RPi.GPIO as GPIO
import Adafruit_DHT
import Adafruit_ADS1x15
import time
from threading import Timer
from dateutil import tz
import datetime
import subprocess
import threading


class Switch:
	def __init__(self, pin):
		self.pin = pin #BCM
		self.state = False
		self.active_since = None

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, True) #off

	def get_state(self):
		return self.state

	def on(self):
		if self.state: return False

		GPIO.output(self.pin, False)
		self.state = True
		self.active_since = unix_now()
		return True

	def off(self):
		if not self.state: return 0
		GPIO.output(self.pin, True)
		self.state = False
		self.active_since = None
		return unix_now()


class Pump(Switch):
	def __init__(self, pin):
		super().__init__(pin)
		self.timer = TimerWrap()

	def get_state(self):
		return [self.state, self.timer.remaining()]

	def on(self, seconds=-1):
		if seconds>0: self.timer.start(seconds, self.off)
		return super().on()


class Fan(Switch):
	def __init__(self, power_pin, speed_pin, frequency=25000, default_speed=100.0):
		super().__init__(power_pin)
		self.speed = default_speed

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(speed_pin, GPIO.OUT)
		self.speed_ctrl = GPIO.PWM(speed_pin, frequency)

	def get_state(self):
		return [self.state, self.speed]

	def on(self, speed=-1):
		speed = float(speed)
		if speed<0: speed = self.speed
		if speed==0: super().off()
		if super().get_state(): self.set_speed(speed)
		else:
			super().on()
			self.speed_ctrl.start(speed)

	def off(self):
		self.speed_ctrl.stop()
		return super().off()

	def set_speed(self, new_speed):
		new_speed = float(new_speed)
		self.speed_ctrl.ChangeDutyCycle(new_speed)


class SoilMoistureSensor:
	def __init__(self, adc, channel, min_v, max_v, gain=2/3):
		self.adc = adc
		self.channel = channel
		self.min_v = min_v #100%
		self.max_v = max_v #0%
		self.gain = gain

	def read(self): #throws
		raw_value = self.adc.read_adc(self.channel, self.gain)
		perc = (raw_value-self.min_v)*100/(self.max_v-self.min_v)
		perc = round(abs(100-perc), 1)
		if perc<0: perc = 0
		elif perc>100: perc = 100
		return perc


class DHT22:
	def __init__(self, pin, attempts=3):
		self.pin = pin
		self.attempts = attempts

	def read(self): #throws
		for attempt in range(self.attempts):
			h,t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.pin)
			if h!=None and t!=None and h<=100:
				return [round(t, 1),round(h, 1)]
			time.sleep(5)
		return [None, None]

class IP_Camera:
	def __init__(self, usr, pwd, ip, snapshot_dir, interval=-1):
		self.usr = usr
		self.pwd = pwd
		self.ip = ip
		self.snapshot_dir = snapshot_dir
		self.interval = interval
		self.timer = TimerWrap()
		self.last_returncode = None

	def take_snapshot(self):
		filename = self.snapshot_dir+get_now().strftime("%Y-%m-%d_%H-%M-%S")+'.jpg'
		cmd = 'ffmpeg -y -rtsp_transport tcp -i "rtsp://'+self.usr+':'+self.pwd+'@'+self.ip+'/11" -frames 1 '+filename
		t = threading.Thread(target=self.call_ffmpeg, args=(cmd,))
		t.start()
		if self.interval>0: self.timer.start(self.interval, self.take_snapshot)
		
	def call_ffmpeg(self, cmd):
		sub = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		self.last_returncode = sub.returncode


class TimerWrap:
	def __init__(self):
		self.active_since = None
		self.current_timer = None

	def start(self, seconds, callback, args=None):
		self.reset()
		self.current_timer = Timer(seconds, callback, args)
		self.active_since = unix_now()
		self.current_timer.start()

	def reset(self):
		if self.current_timer: self.current_timer.cancel()
		self.active_since = None

	def elapsed(self):
		if self.active_since: return unix_now() - self.active_since
		else: return 0

	def remaining(self):
		if self.active_since: return self.current_timer.interval - self.elapsed()
		else: return 0


def get_now():
	from_zone = tz.gettz('UTC')
	to_zone = tz.gettz('Europe/Rome')
	dt = datetime.datetime.now()
	dt = dt.replace(tzinfo=from_zone)
	return dt.astimezone(to_zone)

def unix_now():
	return int(time.time()*1000)
