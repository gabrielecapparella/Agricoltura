#!/usr/bin/python3

from flask import current_app, Blueprint, abort, request, send_file
from flask_users import isAuthorized, isAdmin
from json import dumps as js_dumps, loads as js_loads
import os

manage_files = Blueprint('manage_files', __name__)

@manage_files.route('/getRates')
def get_rates():
	return fread('config/costs_rates.json')

@manage_files.route('/setRates', methods = ['POST'])
def set_rates():
	if isAuthorized():
		data = request.get_json(force=True)
		# floaty_dict = {}
		# for k,v in data.items():
		# 	floaty_dict[k] = float(v)

		with open('config/costs_rates.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		return 'ok'
	else:
		abort(403)

@manage_files.route('/getMainLog')
def get_error_log():
	if isAdmin():
		return fread('log/main.log')
	else:
		abort(403)

@manage_files.route('/getDbLog')
def get_db_log():
	if isAdmin():
		return fread('log/db_utils.log')
	else:
		abort(403)

@manage_files.route('/getSensorsLog')
def get_sensors_log():
	if isAdmin():
		return fread('log/sensors.log')
	else:
		abort(403)

@manage_files.route('/getDevicesCfg')
def get_devices_cfg():
	if isAuthorized():
		with open('config/devices.json', 'r') as devs_file:
			return devs_file.read()
	else:
		abort(403)

@manage_files.route('/editDevCfg', methods = ['POST'])
def edit_device_cfg():
	if isAuthorized():
		data = request.get_json(force=True)
		if current_app.sensors.update_device(data['name'], data['cfg']):
			with open('config/devices.json', 'r+') as devs_file:
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
		with open('config/thresholds.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		current_app.sensors.update_thresholds(data)
		return 'ok'
	else:
		abort(403)

@manage_files.route('/getParameters')
def get_parameters():
	if isAuthorized():
		return fread('config/thresholds.json')
	else:
		abort(403)

@manage_files.route('/getLightSchedule')
def get_light_schedule():
	if isAuthorized():
		return fread('config/grow_lights_schedule.json')
	else:
		abort(403)

@manage_files.route('/setLightSchedule', methods = ['POST'])
def set_light_schedule():
	if isAuthorized():
		data = request.get_json(force=True)
		# TODO some validity check on data
		with open('config/grow_lights_schedule.json', 'w') as file:
			file.write(js_dumps(data, indent=4))
		current_app.sensors.update_lights_schedule(data)
		return js_dumps({"result":True, "new_rules":data})
	else:
		abort(403)

@manage_files.route('/getLastSnapshot', methods = ['POST'])
def snapshot():
	if isAuthorized():
		name = request.get_json(force=True)["camera_name"]
		snap_dir = current_app.sensors.devices[name].snapshots_dir
		ph = os.listdir(snap_dir)
		if ph:
			ph.sort(reverse=True)
			last = os.path.join(snap_dir, ph[0])
			return send_file(last, mimetype='image/jpeg')
		else:
			return 'nope'
	else:
		abort(403)

def fread(filename):
	with open(filename, 'r') as file:
		return file.read()
