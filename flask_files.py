#!/usr/bin/python3

from flask import current_app, Blueprint, abort, request
from flask_users import isAuthorized, isAdmin
from json import dumps as js_dumps, loads as js_loads

manage_files = Blueprint('manage_files', __name__)

@manage_files.route('/getRates')
def get_rates():
	return fread('static/config/costs_rates.json')

@manage_files.route('/setRates', methods = ['POST'])
def set_rates():
	if isAuthorized():
		data = request.get_json(force=True)
		# floaty_dict = {}
		# for k,v in data.items():
		# 	floaty_dict[k] = float(v)

		with open('static/config/costs_rates.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		return 'ok'
	else:
		abort(403)

@manage_files.route('/getMainLog')
def get_error_log():
	if isAdmin():
		return fread('static/log/main.log')
	else:
		abort(403)

@manage_files.route('/getDbLog')
def get_db_log():
	if isAdmin():
		return fread('static/log/db_utils.log')
	else:
		abort(403)

@manage_files.route('/getSensorsLog')
def get_sensors_log():
	if isAdmin():
		return fread('static/log/sensors.log')
	else:
		abort(403)

@manage_files.route('/getDevicesCfg')
def get_devices_cfg():
	if isAuthorized():
		with open('static/config/devices.json', 'r') as devs_file:
			return devs_file.read()
	else:
		abort(403)

@manage_files.route('/editDevCfg', methods = ['POST'])
def edit_device_cfg():
	if isAuthorized():
		data = request.get_json(force=True)
		if current_app.sensors.update_device(data['name'], data['cfg']):
			with open('static/config/devices.json', 'r+') as devs_file:
				new_cfg = devs_file.read()
				devs = js_loads(new_cfg)
				devs[data['index']] = data['cfg']
				devs_file.seek(0)
				devs_file.write(js_dumps(devs, indent=4))
				devs_file.truncate()
			print(type(devs), devs)
			return js_dumps({"result":True, "new_cfg":devs})
		else:
			return js_dumps({"result":False})
	else:
		abort(403)

@manage_files.route('/setParameters', methods = ['POST'])
def set_parameters():
	if isAuthorized():
		data = request.get_json(force=True)
		# floaty_dict = {}
		# for k,v in data.items():
		# 	floaty_dict[k] = float(v)

		with open('static/config/thresholds.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		current_app.sensors.update_thresholds(data)
		return 'ok'
	else:
		abort(403)

@manage_files.route('/getParameters')
def get_parameters():
	if isAuthorized():
		return fread('static/config/thresholds.json')
	else:
		abort(403)

@manage_files.route('/getLightSchedule')
def get_light_schedule():
	if isAuthorized():
		return fread('static/config/grow_lights_schedule.json')
	else:
		abort(403)

@manage_files.route('/setLightSchedule', methods = ['POST'])
def set_light_schedule():
	if isAuthorized():
		data = request.get_json(force=True)
		# TODO some validity check on data
		with open('static/config/grow_lights_schedule.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		current_app.sensors.update_lights_schedule(data)
		return js_dumps({"result":True, "new_rules":data})
	else:
		abort(403)

def fread(filename):
	with open(filename, 'r') as file:
		return file.read()
