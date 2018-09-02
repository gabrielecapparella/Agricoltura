#!/usr/bin/python3

from flask import current_app, Blueprint, jsonify, abort, request, session
import datetime
from flask_software_methods import isAuthorized, isAdmin, datetime_tz, fread
import re
import json
import os
import signal

hardware_methods = Blueprint('hardware_methods', __name__)

@hardware_methods.route('/getLastReading')
def last_reading():
	reading = current_app.db.get_last_reading()
	dt = datetime_tz(datetime.datetime.fromtimestamp(reading[0]/1000))
	dt = dt.strftime("%Y-%m-%d %H:%M:%S")
	return jsonify(dt=dt, temp=reading[1], hum=reading[2], moist=reading[3])

@hardware_methods.route('/getActuators')
def get_actuators():
	f_state = current_app.sensors.fan.get_state()

	return jsonify(
		fan_on = f_state[0],
		fan_speed = f_state[1],
		light_on = current_app.sensors.light.get_state(),
		water_on = current_app.sensors.water.get_state()[0],
		sensors_on = current_app.sensors.is_running,
		actuators_on = current_app.sensors.is_operative
		)

@hardware_methods.route('/setActuators', methods = ['POST'])
def set_actuators():
	if isAuthorized():
		state = request.get_json(force=True)['targetState']
		current_app.sensors.is_operative = state
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getSnapshot')
def get_snapshot():
	if isAuthorized():
		current_app.sensors.take_snapshot()
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/setSensors', methods = ['POST'])
def set_sensors():
	if isAuthorized():
		state = request.get_json(force=True)['targetState']
		current_app.sensors.set_running(state)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/setFan', methods = ['POST'])
def set_fan():
	if isAuthorized():
		data = request.get_json(force=True)
		print('get_set.set_fan: ', data)
		state = data['targetState']
		speed = data.get('targetSpeed', 100)
		current_app.sensors.fan.set_state(state, speed)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getFan')
def get_fan():
	f_state = current_app.sensors.fan.get_state()
	return jsonify(fan_on=f_state[0], fan_speed=f_state[1])

@hardware_methods.route('/setLight', methods = ['POST'])
def set_light():
	if isAuthorized():
		target = request.get_json(force=True)['targetState']
		current_app.sensors.light.set_state(target)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getLight')
def get_light():
	l_state = current_app.sensors.light.get_state()
	return jsonify(light_on=l_state)

@hardware_methods.route('/setWater', methods = ['POST'])
def set_water():
	if isAuthorized():
		target = request.get_json(force=True)['targetState']
		current_app.sensors.water.set_state(target)
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getWater')
def get_water():
	w_state = current_app.sensors.water.get_state()[0]
	return jsonify(water_on=w_state)

@hardware_methods.route('/getTempHistory')
def get_temp_history():
	return json.dumps(current_app.db.get_readings(what='datetime, temperature'))

@hardware_methods.route('/setParameters', methods = ['POST'])
def set_parameters():
	if isAuthorized():
		data = request.get_json(force=True)
		floaty_dict = {}
		for k,v in data.items():
			floaty_dict[k] = float(v)

		with open('static/config/sensors_config.json', 'w') as file:
			file.write(json.dumps(floaty_dict))
		current_app.sensors.update_thresholds()
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/getReadings', methods = ['POST'])
def export_readings():
	if isAuthorized():
		data = request.get_json(force=True)
		d_from = data['from']
		d_to = data['to']
		print('from: ',str(d_from),'to: ',str(d_to))
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

@hardware_methods.route('/waterCycle') #for testing
def do_water_cycle():
	if isAuthorized():
		current_app.sensors.water.water_cycle()
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

@hardware_methods.route('/getRpiTemp')
def get_rpi_temp():
	cpu_temp = fread('/sys/class/thermal/thermal_zone0/temp')
	cpu_temp = float(cpu_temp)/1000
	cpu_temp = round(cpu_temp, 1)
	return jsonify(rpi_temp=cpu_temp)

@hardware_methods.route('/getSystemStatus')
def get_system_status():
	if isAdmin():
		uptime = fread('/proc/uptime')
		td = datetime.timedelta(seconds=float(uptime.split()[0]))
		uptime = "{}d {}h {}m".format(td.days, td.seconds//3600, (td.seconds//60)%60)

		cpu_temp = fread('/sys/class/thermal/thermal_zone0/temp')
		cpu_temp = float(cpu_temp)/1000
		cpu_temp = str(round(cpu_temp, 1))+"°C"

		stat = os.statvfs('/')
		tot = stat.f_blocks * stat.f_frsize / 10**9
		free = stat.f_bavail*stat.f_frsize / 10**9
		used = tot-free
		st_perc = round(used*100/tot)

		mem_info = fread('/proc/meminfo')
		mem_tot = int(re.search('MemTotal:\s+([0-9]+)\skB', mem_info).group(1))
		mem_free = int(re.search('MemAvailable:\s+([0-9]+)\skB', mem_info).group(1))
		mem_used = mem_tot-mem_free
		mem_perc = round(mem_used*100/mem_tot)

		return jsonify(uptime=uptime, cpu_temp=cpu_temp, st_perc=st_perc, mem_perc=mem_perc)
	else:
		abort(403)

@hardware_methods.route('/shutdown') #flask
def shutdown_server():
	if session['is_admin']:
		current_app.clean_up()
	else:
		abort(403)

@hardware_methods.route('/poweroff') #rpi
def poweroff():
	if isAdmin():
		soft_clean_up()
		os.system('/usr/bin/sudo /sbin/poweroff')
		return 'ok'
	else:
		abort(403)

@hardware_methods.route('/reboot')
def reboot():
	if isAdmin():
		soft_clean_up()
		os.system('/usr/bin/sudo /sbin/reboot')
		return 'ok'
	else:
		abort(403)
		
def soft_clean_up():
	current_app.access_logger.info('\nShutting down (soft)')
	current_app.db.clean_up()
	current_app.homebridge.send_signal(signal.SIGINT)
	current_app.sensors.clean_up()	
	
	
