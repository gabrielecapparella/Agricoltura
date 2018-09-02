#!/usr/bin/python3

from flask import current_app, Blueprint, jsonify, abort, request, session
import time
import json
from dateutil import tz

software_methods = Blueprint('software_methods', __name__)

@software_methods.route('/usrlogin', methods=['POST'])
def usr_login():
	data = request.get_json(force=True)
	user = data.get('user', '')
	password = data.get('password', '')
	if not user.isalnum(): return jsonify(result=1) #bad username

	if current_app.db.check_credentials(user, password):
		current_app.db.insert_login_attempt(user, current_app.db.unix_now(), True)
		session['logged_in'] = True
		session['user'] = user
		session.permanent = True
		return jsonify(result=0)
	else:
		current_app.db.insert_login_attempt(user, current_app.db.unix_now(), False)

	return jsonify(result=2) #wrong credentials




@software_methods.route('/getHumHistory')
def get_hum_history():
	return json.dumps(current_app.db.get_readings(what='datetime, humidity'))

@software_methods.route('/getMoistHistory')
def get_moist_history():
	return json.dumps(current_app.db.get_readings(what='datetime, moisture'))

@software_methods.route('/getActHistory')
def get_act_history():
	return json.dumps(current_app.db.get_actuators_records())

@software_methods.route('/getParameters')
def get_parameters():
	return fread('static/config/sensors_config.json')

@software_methods.route('/getRates')
def get_rates():
	return fread('static/config/actuators_rates.json')

@software_methods.route('/setRates', methods = ['POST'])
def set_rates():
	if isAuthorized():
		data = request.get_json(force=True)
		floaty_dict = {}
		for k,v in data.items():
			floaty_dict[k] = float(v)

		with open('static/config/actuators_rates.json', 'w') as file:
			file.write(json.dumps(floaty_dict))
		return 'ok'
	else:
		abort(403)

@software_methods.route('/getCosts', methods = ['POST'])
def get_costs():
	if isAuthorized():
		data = request.get_json(force=True)

		d_from = data['from']
		d_to = data['to']

		rates = json.loads(fread('static/config/actuators_rates.json'))
		act = current_app.db.get_actuators_records(d_from, d_to)
		upt = current_app.db.get_uptimes(d_from, d_to)

		water_used, pump_used, fan_used, light_used, server_used = 0, 0, 0, 0, 0
		for i in act:
			time_s = (i[2]-i[1])/1000
			time_min = time_s/60
			time_h = time_min/60

			if i[0]=='water':
				water_used += (time_min*rates['pump_f'])		#l
				pump_used += (time_h*rates['pump_w'])/1000		#KWh
			elif i[0]=='fan':
				fan_used += (time_h*rates['fan_w'])/1000
			elif i[0]=='light':
				light_used += (time_h*rates['light_w'])/1000

		for i in upt:
			time_h = (i[1]-i[0])/3600
			server_used += time_h*rates['server_w']/1000		#KWh

		pump_cost = pump_used*rates['elec_price']
		water_cost = water_used*rates['water_price']/1000
		fan_cost = fan_used*rates['elec_price']
		light_cost = light_used*rates['elec_price']
		server_cost = server_used*rates['elec_price']

		elec_used = pump_used + fan_used + light_used + server_used
		elec_cost = pump_cost + fan_cost + light_cost + server_cost

		if not d_from: d_from = upt[0][0]
		else: d_from/=1000
		if not d_to: d_to = current_app.db.unix_now()/1000
		else: d_to/=1000
		total_days = (d_to-d_from)/86400
		if total_days<1: total_days = 1

		elec_avg = elec_cost/total_days
		water_avg =water_cost/total_days
		pump_avg = pump_cost/total_days
		fan_avg = fan_cost/total_days
		light_avg = light_cost/total_days
		server_avg = server_cost/total_days

		costs = [		#qnt, avg, tot
			['{:.3f} Kwh'.format(elec_used), '{:.3f} €/d'.format(elec_avg), '{:.3f} €'.format(elec_cost)],
			['{:.3f} L'.format(water_used), '{:.3f} €/d'.format(water_avg), '{:.3f} €'.format(water_cost)],
			['{:.3f} Kwh'.format(fan_used), '{:.3f} €/d'.format(fan_avg), '{:.3f} €'.format(fan_cost)],
			['{:.3f} Kwh'.format(pump_used), '{:.3f} €/d'.format(pump_avg), '{:.3f} €'.format(pump_cost)],
			['{:.3f} Kwh'.format(light_used), '{:.3f} €/d'.format(light_avg), '{:.3f} €'.format(light_cost)],
			['{:.3f} Kwh'.format(server_used), '{:.3f} €/d'.format(server_avg), '{:.3f} €'.format(server_cost)]]

		return json.dumps(costs)
	else:
		abort(403)

@software_methods.route('/getAccessLog')
def get_access_log():
	if isAdmin():
		return fread('static/log/flask_access.log')
	else:
		abort(403)

@software_methods.route('/getErrorLog')
def get_error_log():
	if isAdmin():
		return fread('static/log/flask_error.log')
	else:
		abort(403)

@software_methods.route('/getDbLog')
def get_db_log():
	if isAdmin():
		return fread('static/log/db_utils.log')
	else:
		abort(403)

@software_methods.route('/getSensorsLog')
def get_sensors_log():
	if isAdmin():
		return fread('static/log/sensors.log')
	else:
		abort(403)

@software_methods.route('/getUsers')
def get_users():
	if isAdmin():
		return json.dumps(current_app.db.get_users())
	else:
		abort(403)

@software_methods.route('/addUser', methods = ['POST'])
def add_user():
	if isAdmin():
		data = request.get_json(force=True)
		if not data['username'].isalnum(): return jsonify(result=False)
		res = current_app.db.insert_user(data)
		return jsonify(result=res)
	else:
		abort(403)

@software_methods.route('/deleteUser', methods = ['POST'])
def del_user():
	if isAdmin():
		data = request.get_json(force=True)
		if current_app.db.delete_user(data['username']): return jsonify(result=True)
		return jsonify(result=False)
	else:
		abort(403)

@software_methods.route('/regenerateApiKey', methods = ['POST'])
def new_api():
	if isAdmin():
		data = request.get_json(force=True)
		if current_app.db.regenerate_api_key(data['username']): return jsonify(result=True)
		return jsonify(result=False)
	else:
		abort(403)

def datetime_tz(dt):
	from_zone = tz.gettz('UTC')
	to_zone = tz.gettz('Europe/Rome')
	dt = dt.replace(tzinfo=from_zone)
	return dt.astimezone(to_zone)

def fread(filename):
	with open(filename, 'r') as file:
 		return file.read()

def isAdmin():
	return (isAuthorized() and current_app.db.is_admin(session['user']))

def isAuthorized():
	if 'logged_in' in session: return True

	if not request.method == 'POST': return False
	data = request.get_json(force=True)
	if not data: return False

	key = data.get('api_key', False)
	return current_app.db.check_api_key(key)
