#!/usr/bin/python3

from flask import current_app, Blueprint, jsonify, abort, request, session
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

@software_methods.route('/getRates')
def get_rates():
	return fread('static/config/costs_rates.json')

@software_methods.route('/setRates', methods = ['POST'])
def set_rates():
	if isAuthorized():
		data = request.get_json(force=True)
		floaty_dict = {}
		for k,v in data.items():
			floaty_dict[k] = float(v)

		with open('static/config/costs_rates.json', 'w') as file:
			file.write(json.dumps(floaty_dict, indent=4))
		return 'ok'
	else:
		abort(403)

@software_methods.route('/getCosts', methods = ['POST'])
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

		return json.dumps(costs) # costs: {type:[kwh, l, daily avg, tot]}
	else:
 		abort(403)

@software_methods.route('/getMainLog')
def get_error_log():
	if isAdmin():
		return fread('static/log/main.log')
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
	return True # REMOVE BEFORE FLIGHT
	return (isAuthorized() and current_app.db.is_admin(session['user']))

def isAuthorized():
	return True # REMOVE BEFORE FLIGHT
	if 'logged_in' in session: return True

	if not request.method == 'POST': return False
	data = request.get_json(force=True)
	if not data: return False

	key = data.get('api_key', False)
	return current_app.db.check_api_key(key)
