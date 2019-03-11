#!/usr/bin/python3

from flask import current_app, Blueprint, jsonify, abort, request, session
import datetime
from flask_software_methods import isAuthorized, isAdmin, fread
import re
import json
import os
#import signal

hardware_methods = Blueprint('hardware_methods', __name__)

@hardware_methods.route('/getFullState')
def get_full_state():
	state = current_app.sensors.get_full_state()
	return json.dumps(state)

@hardware_methods.route('/setActuator', methods = ['POST'])
def setActuator():
	if isAuthorized():
		data = request.get_json(force=True)
		current_app.sensors.set_act([data['name']], *data['target_state'])
		new_state = current_app.sensors.get_dev_state(data['name'])
		if not isinstance(new_state, list): new_state = [new_state]
		return json.dumps(new_state)
	else:
		abort(403)

@hardware_methods.route('/getDevicesCfg')
def get_devices_cfg():
	if isAuthorized():
		with open('static/config/devices.json', 'r') as devs_file:
			return devs_file.read()
	else:
		abort(403)

@hardware_methods.route('/editDevCfg', methods = ['POST'])
def edit_device_cfg():
	if isAuthorized():
		data = request.get_json(force=True)
		if current_app.sensors.update_device(data['name'], data['cfg']):
			with open('static/config/devices.json', 'r+') as devs_file:
				new_cfg = devs_file.read()
				devs = json.loads(new_cfg)
				devs[data['index']] = data['cfg']
				devs_file.seek(0)
				devs_file.write(json.dumps(devs, indent=4))
				devs_file.truncate()
			print(type(devs), devs)
			return json.dumps({"result":True, "new_cfg":devs})
		else:
			return json.dumps({"result":False})
	else:
		abort(403)

@hardware_methods.route('/setSensorsState', methods = ['POST'])
def set_sensors_state():
	if isAuthorized():
		state = request.get_json(force=True)
		current_app.sensors.set_state(state)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getTempHistory')
def get_temp_history():
	return json.dumps(current_app.db.get_readings(what='datetime, temperature'))

@hardware_methods.route('/getHumHistory')
def get_hum_history():
	return json.dumps(current_app.db.get_readings(what='datetime, humidity'))

@hardware_methods.route('/getMoistHistory')
def get_moist_history():
	return json.dumps(current_app.db.get_readings(what='datetime, moisture'))

@hardware_methods.route('/setParameters', methods = ['POST'])
def set_parameters():
	if isAuthorized():
		data = request.get_json(force=True)
		floaty_dict = {}
		for k,v in data.items():
			floaty_dict[k] = float(v)

		with open('static/config/thresholds.json', 'w') as file:
			file.write(json.dumps(floaty_dict, indent=4))
		current_app.sensors.update_thresholds(floaty_dict)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getParameters')
def get_parameters():
	if isAuthorized():
		return fread('static/config/thresholds.json')
	else:
		abort(403)

@hardware_methods.route('/getLightSchedule')
def get_light_schedule():
	if isAuthorized():
		return fread('static/config/grow_lights_schedule.json')
	else:
		abort(403)

@hardware_methods.route('/setLightSchedule', methods = ['POST'])
def set_light_schedule():
	if isAuthorized():
		data = request.get_json(force=True)
		# TODO some validity check on data
		with open('static/config/grow_lights_schedule.json', 'w') as file:
			file.write(json.dumps(data, indent=4))
		current_app.sensors.update_lights_schedule(data)
		return json.dumps({"result":True, "new_rules":data})
	else:
		abort(403)

@hardware_methods.route('/getReadings', methods = ['POST'])
def export_readings():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		return json.dumps(current_app.db.get_readings(d_from, d_to))
	else:
		abort(403)

@hardware_methods.route('/getActuators', methods = ['POST'])
def export_actuators():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		return json.dumps(current_app.db.get_actuators_records(d_from, d_to))
	else:
		abort(403)

@hardware_methods.route('/getRpiTemp')
def get_rpi_temp():
	cpu_temp = fread('/sys/class/thermal/thermal_zone0/temp')
	cpu_temp = float(cpu_temp)/1000
	cpu_temp = round(cpu_temp, 1)
	return jsonify(rpi_temp=cpu_temp)

@hardware_methods.route('/getSystemStatus')
def get_system_status():
	if isAdmin():
		return json.dumps(sys_status())
	else:
		abort(403)

def sys_status():
	status = {}

	uptime = fread('/proc/uptime')
	td = datetime.timedelta(seconds=float(uptime.split()[0]))
	status['uptime'] = "{}d {}h {}m".format(td.days, td.seconds//3600, (td.seconds//60)%60)

	cpu_temp = fread('/sys/class/thermal/thermal_zone0/temp')
	cpu_temp = float(cpu_temp)/1000
	status['cpu_temp'] = round(cpu_temp, 1)

	stat = os.statvfs('/')
	status['disk_tot'] = round(stat.f_blocks * stat.f_frsize / 10**9, 1)
	free = stat.f_bavail*stat.f_frsize / 10**9
	status['disk_used'] = round(status['disk_tot']-free, 1)

	mem_info = fread('/proc/meminfo')
	mem_tot = int(re.search('MemTotal:\s+([0-9]+)\skB', mem_info).group(1))
	status['mem_tot'] = round(mem_tot / 10**6, 1)
	mem_free = int(re.search('MemAvailable:\s+([0-9]+)\skB', mem_info).group(1))/ 10**6
	status['mem_used'] = round(status['mem_tot']-mem_free, 1)

	return status

@hardware_methods.route('/shutdown') #flask
def shutdown_server():
	if session['is_admin']:
		current_app.clean_up()
	else:
		abort(403)

@hardware_methods.route('/poweroff') #rpi
def poweroff():
	if isAdmin():
		current_app.clean_up()
		os.system('/usr/bin/sudo /sbin/poweroff')
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/reboot')
def reboot():
	if isAdmin():
		current_app.clean_up()
		os.system('/usr/bin/sudo /sbin/reboot')
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/waterCycle') #for testing
def do_water_cycle():
	if isAuthorized():
		current_app.sensors.do_water_cycle()
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/sensorsCycle') #for testing
def do_sensors_cycle():
	if isAuthorized():
		current_app.sensors.cycle()
		return 'ok'
	else:
		abort(403)

# @hardware_methods.route('/getSnapshot') #for testing
# def get_snapshot():
# 	if isAuthorized():
# 		current_app.sensors.take_snapshot()
# 		return 'ok'
# 	else:
# 		abort(403)
