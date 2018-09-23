#!/usr/bin/python3

from flask import Flask, render_template, request
import flask_web_interface
import flask_software_methods
import flask_hardware_methods
import db_utils
import sensors
import signal
import logging
import json
from logging.handlers import RotatingFileHandler
import subprocess
import sensors_utils

master = Flask(__name__, static_url_path="/agricoltura/static")
master.register_blueprint(flask_web_interface.web_interface, url_prefix='/agricoltura')
master.register_blueprint(flask_software_methods.software_methods, url_prefix='/agricoltura/methods')
master.register_blueprint(flask_hardware_methods.hardware_methods, url_prefix='/agricoltura/methods')

def setup():
	global master

	with open('static/config/main_app.json', 'r') as cfg_file:
		master.cfg = json.loads(cfg_file.read())
	master.secret_key = master.cfg["session_key"]
	loggingSetup()
	master.logger.debug('[flask_main]: setup')
	master.boot_time = sensors_utils.unix_now()
	master.sensors = sensors.Sensors()
	master.db = db_utils.DB_Connection()
	master.clean_up = clean_up

	if master.cfg['homebridge']:
		with open('static/log/homebridge.log', 'a') as hb_log:
			master.homebridge = subprocess.Popen('homebridge', stdout=subprocess.DEVNULL, stderr=hb_log)

	signal.signal(signal.SIGTERM, teardown_handler)
	signal.signal(signal.SIGINT, teardown_handler)

def teardown_handler(signal, frame): clean_up()

def clean_up():
	global master

	master.logger.debug('[flask_main]: cleanup')
	now = sensors_utils.unix_now()
	uptime = (now-master.boot_time)/(3600*1000) # hours
	kwh = master.sensors.rates['server_w']*uptime/1000
	master.db.insert_device_record(('server', master.boot_time, now, kwh, 0, kwh*master.sensors.rates['elec_price']))
	# add cameras cost

	master.db.clean_up()
	if master.cfg['homebridge']: master.homebridge.send_signal(signal.SIGINT)
	master.sensors.clean_up()

	master.log_handler.close()
	master.logger.removeHandler(master.log_handler)

def loggingSetup():
	global master

	log_format = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')

	master.log_handler = RotatingFileHandler('static/log/gunicorn_error.log', maxBytes=1024*1024, backupCount=10)
	master.log_handler.setFormatter(log_format)
	master.log_handler.setLevel(logging.DEBUG)

	master.logger = logging.getLogger('gunicorn.error')
	master.logger.setLevel(logging.DEBUG)

	master.logger.addHandler(master.log_handler)


@master.errorhandler(404)
def pageNotFound(e):
	return render_template('404.html', title = "Page Not Found", pname = request.path)

@master.errorhandler(403)
def forbidden(e):
	return render_template('403.html', title = "Forbidden")


#if __name__ == '__main__':
try:
	setup()
except Exception as e:
	master.logger.exception(e)
	clean_up()