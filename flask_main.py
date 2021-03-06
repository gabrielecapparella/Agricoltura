#!/usr/bin/python3

from flask import Flask, render_template, request
import flask_web_interface
import flask_users
import flask_files
import flask_sensors
import db_utils
import sensors
import signal
import logging
import json
from logging.handlers import RotatingFileHandler
import subprocess
import sensors_utils
from os import urandom

master = Flask(__name__, static_url_path="/agricoltura/static")
master.register_blueprint(flask_web_interface.web_interface, url_prefix='/agricoltura')
master.register_blueprint(flask_users.manage_users, url_prefix='/agricoltura/methods')
master.register_blueprint(flask_files.manage_files, url_prefix='/agricoltura/methods')
master.register_blueprint(flask_sensors.sensors_api, url_prefix='/agricoltura/methods')

def setup():
	global master

	master.config['TEMPLATES_AUTO_RELOAD'] = True

	with open('config/main_app.json', 'r') as cfg_file:
		master.cfg = json.loads(cfg_file.read())

	master.secret_key = urandom(42)

	loggingSetup()#master.cfg["debug"])
	master.logger.info('[flask_main]: setup')

	master.boot_time = sensors_utils.unix_now()
	master.sensors = sensors.Sensors(debug=master.cfg["debug"])
	master.db = db_utils.DB_Connection()
	master.clean_up = clean_up

	if master.cfg['homebridge']:
		with open('log/homebridge.log', 'a') as hb_log:
			master.homebridge = subprocess.Popen('homebridge', stdout=subprocess.DEVNULL, stderr=hb_log)

	signal.signal(signal.SIGTERM, teardown_handler)
	signal.signal(signal.SIGINT, teardown_handler)

def teardown_handler(signal, frame):
	clean_up()
	raise SystemExit #KeyboardInterrupt

def clean_up():
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	global master
	master.logger.info('[flask_main]: cleanup')

	master.db.clean_up()
	if master.cfg['homebridge']: master.homebridge.send_signal(signal.SIGINT)
	master.sensors.clean_up()

	master.log_handler.close()
	master.logger.removeHandler(master.log_handler)

def loggingSetup():
	global master

	log_format = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')

	master.log_handler = RotatingFileHandler('log/main.log', maxBytes=1024*1024, backupCount=10)
	master.log_handler.setFormatter(log_format)
	master.log_handler.setLevel(logging.DEBUG)

	master.logger = logging.getLogger('main.error')
	master.logger.setLevel(logging.DEBUG)

	master.logger.addHandler(master.log_handler)


@master.errorhandler(404)
def pageNotFound(e):
	return render_template('404.html', title = "Page Not Found", pname = request.path)

@master.errorhandler(403)
def forbidden(e):
	return render_template('403.html', title = "Forbidden")

try:
	setup()
	if __name__ == '__main__': master.run(host='0.0.0.0', port=80)
except Exception as e:
	master.logger.exception(e)
	clean_up()
