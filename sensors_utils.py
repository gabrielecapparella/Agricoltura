#!/usr/bin/python3

from threading import Timer
from dateutil import tz
import datetime
import requests
import time


class Scheduler: #not used nor tested
	def __init__(self):
		self.jobs = []

	def add_job(self, when, what, args=[], interval=None):
		# (datetime.datetime, function, list, datetime.timedelta) -> None
		self.jobs.append([when, what, args, interval])

	def run_pending_jobs(self):
		now = get_now()
		for job in self.jobs:
			if job[0]>=now:
				job[1](*job[2])
				if job[3]: job[1]+=job[3]
	def reset(self):
		self.jobs = []

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

def get_today_len(self):
	response = requests.get('http://api.sunrise-sunset.org/json?lat=41.890184&lng=12.492409')
	hms = response.json()['results']['day_length'].split(':')
	return round(int(hms[0])+int(hms[1])/60, 1)