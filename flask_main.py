#!/usr/bin/python3

from flask import Flask, render_template, request
import flask_web_interface
import flask_software_methods
import flask_hardware_methods
import db_utils
import sensors
import signal
import sys
import logging
import json
from logging.handlers import RotatingFileHandler
import time
import subprocess

master = Flask(__name__)


with open('static/config/main_app.json', 'r') as cfg_file:
	cfg = json.loads(cfg_file.read())

certs = tuple(cfg["ssl_certs"])

def clean_up():
	master.access_logger.info('\nShutting down.')
	master.db.insert_uptime([master.boot_time, time.time()])
	master.db.clean_up()
	#master.homebridge.send_signal(signal.SIGINT)
	if master.sensors.state: master.sensors.clean_up()

	master.error_log_handler.close()
	master.access_log_handler.close()
	master.logger.removeHandler(master.error_log_handler)
	master.access_logger.removeHandler(master.access_log_handler)

	sys.exit(0)

def key_interrupt(signal, frame):
	clean_up()

def loggingSetup():
	access_log_format = logging.Formatter('%(levelname)s - %(message)s')
	error_log_format = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')

	master.error_log_handler = RotatingFileHandler('static/log/flask_error.log', maxBytes=1024*1024, backupCount=10)
	master.error_log_handler.setFormatter(error_log_format)
	master.error_log_handler.setLevel(logging.DEBUG)

	master.access_log_handler = RotatingFileHandler('static/log/flask_access.log', maxBytes=1024*1024, backupCount=10)
	master.access_log_handler.setFormatter(access_log_format)
	master.access_log_handler.setLevel(logging.DEBUG)

	master.access_logger = logging.getLogger('werkzeug')

	master.logger.addHandler(master.error_log_handler)
	master.access_logger.addHandler(master.access_log_handler)

@master.errorhandler(404)
def pageNotFound(e):
	return render_template('404.html', title = "Page Not Found", pname = request.path)

@master.errorhandler(403)
def forbidden(e):
	return render_template('403.html', title = "Forbidden")

#@master.route('/.well-known/acme-challenge/fN_rNqkFA9wUNq8agN5TGKHmWO_H5BYhmx7o2duL-QU')
#def letsencrypt_check():
#	return 'fN_rNqkFA9wUNq8agN5TGKHmWO_H5BYhmx7o2duL-QU.DHS1QdXKzaTr8pAtIPSedFqRW7dQk4HSRzBTGUkMyEc'

@master.before_request
def before_request():
	if request.url.startswith('http://'):
		return redirect(request.url.replace('http://', 'https://'), code=302)

if __name__ == '__main__':
	try:
		loggingSetup()

		master.boot_time = time.time()

		master.sensors = sensors.Sensors()

		# with open('static/log/homebridge.log', 'a') as hb_log:
		# 	master.homebridge = subprocess.Popen('homebridge', stdout=subprocess.DEVNULL, stderr=hb_log)

		master.db = db_utils.DB_Connection()
		master.register_blueprint(flask_web_interface.web_interface)
		master.register_blueprint(flask_software_methods.software_methods, url_prefix='/methods')
		master.register_blueprint(flask_hardware_methods.hardware_methods, url_prefix='/methods')

		master.secret_key = cfg["session_key"]

		signal.signal(signal.SIGINT, key_interrupt)

		master.run('0.0.0.0', 4242, ssl_context=certs)


	except Exception as e:
		master.logger.exception(e)
		clean_up()
