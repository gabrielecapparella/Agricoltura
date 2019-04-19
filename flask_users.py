#!/usr/bin/python3

from flask import current_app, Blueprint, jsonify, abort, request, session
from json import dumps as js_dumps
import traceback

manage_users = Blueprint('manage_users', __name__)

@manage_users.route('/usrlogin', methods=['POST'])
def usr_login():
	try:
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
	except Exception as e:
		current_app.logger.exception("[/methods/usrlogin]: {}"
			.format(traceback.format_exc()))
		abort(422)

@manage_users.route('/getUsers')
def get_users():
	if isAdmin():
		return js_dumps(current_app.db.get_users())
	else:
		abort(403)

@manage_users.route('/addUser', methods = ['POST'])
def add_user():
	if isAdmin():
		try:
			data = request.get_json(force=True)
			if not data['username'].isalnum(): return jsonify(result=False)
			res = current_app.db.insert_user(data)
			return jsonify(result=res)
		except Exception as e:
			current_app.logger.exception("[/methods/addUser]: {}"
				.format(traceback.format_exc()))
			abort(422)
	else:
		abort(403)

@manage_users.route('/deleteUser', methods = ['POST'])
def del_user():
	if isAdmin():
		try:
			data = request.get_json(force=True)
			if current_app.db.delete_user(data['username']): return jsonify(result=True)
			return jsonify(result=False)
		except Exception as e:
			current_app.logger.exception("[/methods/deleteUser]: {}"
				.format(traceback.format_exc()))
			abort(422)
	else:
		abort(403)

@manage_users.route('/regenerateApiKey', methods = ['POST'])
def new_api():
	if isAdmin():
		try:
			data = request.get_json(force=True)
			if current_app.db.regenerate_api_key(data['username']): return jsonify(result=True)
			return jsonify(result=False)
		except Exception as e:
			current_app.logger.exception("[/methods/regenerateApiKey]: {}"
				.format(traceback.format_exc()))
			abort(422)
	else:
		abort(403)

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
