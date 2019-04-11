#!/usr/bin/python3

from flask import current_app, Blueprint, abort, request, send_file
from datetime import timedelta
from flask_users import isAuthorized, isAdmin
from flask_files import fread
from re import search
from json import dumps as js_dumps
from os import statvfs, listdir
from os.path import join

sensors_api = Blueprint('sensors_api', __name__)

@sensors_api.route('/getFullState')
def get_full_state():
	state = current_app.sensors.get_full_state()
	return js_dumps(state)

@sensors_api.route('/setActuator', methods = ['POST'])
def set_actuator():
	if isAuthorized():
		data = request.get_json(force=True)
		current_app.sensors.set_act([data['name']], *data['target_state'])
		new_state = current_app.sensors.get_dev_state(data['name'])
		if not isinstance(new_state, list): new_state = [new_state]
		return js_dumps(new_state)
	else:
		abort(403)

@sensors_api.route('/setActiveControl', methods = ['POST'])
def set_active_control():
	if isAuthorized():
		data = request.get_json(force=True)
		result = current_app.sensors.set_single_active_control(data['state_index'], data['state'])
		return js_dumps({"result":result, "state_index":data['state_index']})
	else:
		abort(403)

@sensors_api.route('/setSensorsState', methods = ['POST'])
def set_sensors_state():
	if isAuthorized():
		state = request.get_json(force=True)
		current_app.sensors.set_state(state)
		return 'ok'
	else:
		abort(403)

@sensors_api.route('/getCosts', methods = ['POST'])
def get_costs():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		if not d_from: d_from = current_app.db.get_first_day()
		if not d_to: d_to = current_app.db.unix_now()
		total_days = (d_to-d_from)/86400
		if total_days<1: total_days = 1

		costs = {}
		past_costs = current_app.db.get_costs(d_from, d_to)
		for entry in past_costs: # entry = [model_type, kwh, l, cost]
			model_type = [None]*4
			model_type[0] = entry[1] # kwh
			model_type[1] = entry[2] # l
			model_type[2] = round(entry[3]/total_days, 4) # daily avg
			model_type[3] = entry[3] # total
			costs[entry[0]] = model_type

		# I expect very few 'current costs'
		current_costs = current_app.sensors.get_system_costs()
		for entry in current_costs: # entry = [name, model_type, start, end, kwh, l, cost]
			model_type = costs.get(entry[1], [0]*4)
			model_type[0] += round(entry[4], 4) # kwh
			model_type[1] += round(entry[5], 4) # l
			model_type[3] += round(entry[6], 4) # total
			model_type[2] = round(model_type[3]/total_days, 4) # daily avg

			costs[entry[1]] = model_type

		return js_dumps(costs) # costs: {type:[kwh, l, daily avg, tot]}
	else:
 		abort(403)

@sensors_api.route('/getTempHistory')
def get_temp_history():
	return js_dumps(current_app.db.get_readings(what='datetime, temperature'))

@sensors_api.route('/getHumHistory')
def get_hum_history():
	return js_dumps(current_app.db.get_readings(what='datetime, humidity'))

@sensors_api.route('/getMoistHistory')
def get_moist_history():
	return js_dumps(current_app.db.get_readings(what='datetime, moisture'))

@sensors_api.route('/getReadings', methods = ['POST'])
def export_readings():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		return js_dumps(current_app.db.get_readings(d_from, d_to))
	else:
		abort(403)

@sensors_api.route('/getActuators', methods = ['POST'])
def export_actuators():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		return js_dumps(current_app.db.get_actuators_records(d_from, d_to))
	else:
		abort(403)

@sensors_api.route('/getLastSnapshot', methods = ['POST']) # TODO
def get_last_snapshot():
	camera_name = request.get_json(force=True)["camera_name"]
	camera = current_app.sensors.devices.get(camera_name, None)
	if not camera: return 'camera not found'
	ph = listdir(camera.snapshots_dir)
	if ph:
		ph.sort(reverse=True)
		full_path = join(camera.snapshots_dir, ph[0])
		return send_file(full_path, mimetype='image/jpeg')
	else:
		return 'snapshots dir not found'

@sensors_api.route('/getSystemStatus')
def get_system_status():
	if isAdmin():
		return js_dumps(sys_status())
	else:
		abort(403)

def sys_status():
	status = {}

	uptime = fread('/proc/uptime')
	td = timedelta(seconds=float(uptime.split()[0]))
	status['uptime'] = "{}d {}h {}m".format(td.days, td.seconds//3600, (td.seconds//60)%60)

	cpu_temp = fread('/sys/class/thermal/thermal_zone0/temp')
	cpu_temp = float(cpu_temp)/1000
	status['cpu_temp'] = round(cpu_temp, 1)

	stat = statvfs('/')
	status['disk_tot'] = round(stat.f_blocks * stat.f_frsize / 10**9, 1)
	free = stat.f_bavail*stat.f_frsize / 10**9
	status['disk_used'] = round(status['disk_tot']-free, 1)

	mem_info = fread('/proc/meminfo')
	mem_tot = int(search('MemTotal:\s+([0-9]+)\skB', mem_info).group(1))
	status['mem_tot'] = round(mem_tot / 10**6, 1)
	mem_free = int(search('MemAvailable:\s+([0-9]+)\skB', mem_info).group(1))/ 10**6
	status['mem_used'] = round(status['mem_tot']-mem_free, 1)

	return status

@sensors_api.route('/waterCycle') #for testing
def do_water_cycle():
	if isAuthorized():
		current_app.sensors.do_water_cycle()
		return 'ok'
	else:
		abort(403)

@sensors_api.route('/sensorsCycle') #for testing
def do_sensors_cycle():
	if isAuthorized():
		current_app.sensors.cycle()
		return 'ok'
	else:
		abort(403)
