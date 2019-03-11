#!/usr/bin/python3

from flask import current_app, Blueprint, redirect, url_for, render_template, session, abort, send_file
from flask_software_methods import isAuthorized, isAdmin
from flask_hardware_methods import sys_status
import os

web_interface = Blueprint('web_interface', __name__, template_folder='templates', static_folder="static")


@web_interface.route('/')
def index():
	return render_template('index.html', title="Agricoltura")

@web_interface.route('/login')
def login():
	return render_template('login.html', title="Login")

@web_interface.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('web_interface.index'))

@web_interface.route('/devices')
def devices():
	full_state = current_app.sensors.get_full_state()
	return render_template('devices.html', title="Devices", devs=full_state)

@web_interface.route('/control')
def control():
	if isAuthorized():
		return render_template('control.html', title="Control")#, user=session['user']) REMOVE BEFORE FLIGHT
	else: abort(403)

@web_interface.route('/system')
def system():
	if isAdmin():
		return render_template('system.html', title="System", status=sys_status())
	else: abort(403)

@web_interface.route('/snapshot')
def snapshot():
	ph = os.listdir('static/photos/')
	if ph:
		ph.sort(reverse=True)
		last = ph[0]
		return send_file('static/photos/'+last, mimetype='image/jpeg')
	else:
		return 'nope'
