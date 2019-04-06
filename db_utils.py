#!/usr/bin/python3

import mysql.connector
import mysql.connector.pooling
import time
import random
import os
import logging
import hashlib
import json
from logging.handlers import RotatingFileHandler

class DB_Connection:
	def __init__(self, testing=False, cfg=None): #if testing, a testing db will be used and deleted on clean_up
		self.testing = testing
		self.logger = logging.getLogger(__name__)
		self.log_handler = None
		if not len(self.logger.handlers): self.loggerSetup()
		self.logger.info("[DB_utils]: Initiating...")

		if cfg:
			self.__config = cfg
		else:
			with open('static/config/database.json', 'r') as cfg_file:
				self.__config = json.loads(cfg_file.read())

		if testing:
			self.__config['database'] += '_test'
			setup_db(**self.__config)

		self.__config['autocommit'] = True
		self.pool = self.create_pool(pool_name="db_utils_pool", pool_size=10)

	def create_pool(self, pool_name, pool_size):
		pool = mysql.connector.pooling.MySQLConnectionPool(
			pool_name=pool_name,
			pool_size=pool_size,
			pool_reset_session=True,
			**self.__config)
		return pool

	def connect(self):
		try:
			self.connection = mysql.connector.connect(**self.__config)
			self.cursor = self.connection.cursor()
		except Exception as err:
			self.logger.exception('DB.Connect: "{}"'.format(err))
			self.clean_up()
			return False
		return True

	def clean_up(self):
		self.logger.info("[DB_utils]: cleaning up...")
		# if self.testing: self.insert("DROP DATABASE IF EXISTS {}".format(self.__config['database']), "")
		self.pool._remove_connections()
		if self.log_handler:
			self.log_handler.close()
			self.logger.removeHandler(self.log_handler)

	def loggerSetup(self):
		if self.testing: log_file = 'static/log/db_utils_test.log'
		else: log_file = 'static/log/db_utils.log'

		self.log_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=10)
		formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
		self.log_handler.setFormatter(formatter)
		self.logger.addHandler(self.log_handler)
		self.logger.setLevel(logging.DEBUG)

	def insert(self, model, data):
		try:
			conn = self.pool.get_connection()
			cursor = conn.cursor()
			result = True

			cursor.execute(model, data)
		except Exception as e:
			self.logger.exception('DB.Insert: There was a problem while executing "{}"\n\n{}'.format(model, e))
			result = False
		finally:
			cursor.close()
			conn.close()
			return result

	def select(self, model, data=""): #returns a list of tuples
		try:
			conn = self.pool.get_connection()
			cursor = conn.cursor()
			rows = []
			cursor.execute(model, data)
			rows = cursor.fetchall()
		except Exception as e:
			self.logger.exception('DB.Select: There was a problem while executing "{}"\n\n{}'.format(model, e))
		finally:
			cursor.close()
			conn.close()
			return rows

	def insert_device_record(self, data):
		query = ("INSERT INTO costs"
			" (device, model_type, start, end, kwh, l, cost)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s)")
		return self.insert(query, data)

	def get_costs(self, date_from=None, date_to=None):
		query = "SELECT model_type, SUM(kwh), SUM(l), SUM(cost) FROM costs"

		if (date_from) and (date_to):
			return self.select(query+" WHERE start BETWEEN %s AND %s GROUP BY model_type", (date_from, date_to))
		elif date_from:
			return self.select(query+" WHERE start >= %s GROUP BY model_type", (date_from,))
		elif date_to:
			return self.select(query+" WHERE end <= %s GROUP BY model_type", (date_to,))
		else:
			return self.select(query+" GROUP BY model_type")

	def get_first_day(self):
		query = "SELECT start FROM costs ORDER BY start LIMIT 1"
		first_day = self.select(query)
		if not first_day: return False
		else: return first_day[0][0]

	def insert_sensors_reading(self, data):
		query = ("INSERT INTO sensors_readings "
			"(datetime, temperature, humidity, moisture) "
			"VALUES (%s, %s, %s, %s)")

		return self.insert(query, data)

	def get_readings(self, date_from=None, date_to=None, what="datetime,temperature,humidity,moisture"):
		for c in [';', "'", '"']:
			if c in what:
				self.logger.warn("DB.get_readings: someone tried to inject evil characters -> {}".format(what))
				return []

		query = "SELECT {} FROM sensors_readings".format(what)

		not_null = ''
		for i in what.split(','): not_null+=' AND {} IS NOT NULL'.format(i)
		not_null = not_null.replace(' AND', '', 1)

		if (date_from) and (date_to):
			return self.select(query+" WHERE datetime BETWEEN %s AND %s AND"+not_null, (date_from, date_to))
		elif date_from:
			return self.select(query+" WHERE datetime >= %s AND"+not_null, (date_from,))
		elif (not date_from) and (not date_to):
			return self.select(query+' WHERE'+not_null)
		else:
			return []

	def get_last_reading(self):
		query = "SELECT * FROM sensors_readings ORDER BY datetime DESC LIMIT 1"
		reading = self.select(query)

		if not reading: return ["-", "-", "-", "-"]
		return reading[0]

	def insert_user(self, data):
		query = ("INSERT INTO users "
			"(username, pwd_hash, api_key, is_admin) "
			"VALUES (%s, %s, %s, %s)")
		user_data = (data['username'], self.get_hash(data['password']), self.generate_api_key(), data['is_admin'])
		return self.insert(query, user_data)

	def is_admin(self, username):
		query = 'SELECT * FROM users WHERE username=%s AND is_admin=1'
		if self.select(query, (username,)): return True
		return False

	def delete_user(self, username):
		#print(username)
		query = ('DELETE FROM users WHERE username = %s')
		return self.insert(query, (username,))

	def regenerate_api_key(self, user):
		query = "UPDATE users SET api_key=%s WHERE username=%s"
		new_api_key = self.generate_api_key()
		if self.insert(query, (new_api_key, user)):
			return new_api_key
		return False

	def insert_login_attempt(self, username, dt, result):
		query = ("INSERT INTO logins "
			"(username, datetime, success) "
			"VALUES (%s, %s, %s)")
		return self.insert(query, (username, dt, result))

	def change_password(self, user, new_pwd):
		query = "UPDATE users SET pwd_hash=%s WHERE username=%s"
		return self.insert(query, (self.get_hash(new_pwd), user))

	def check_credentials(self, user, password):
		hashed_pwd = self.get_hash(password)
		query = "SELECT * FROM users WHERE username=%s AND pwd_hash=%s"
		if not self.select(query, (user, hashed_pwd)): return False
		return True

	def generate_api_key(self):
		return hashlib.sha1(os.urandom(64)).hexdigest()

	def check_api_key(self, api_key):
		if not api_key: return False
		query = "SELECT username FROM users WHERE api_key=%s"
		sel = self.select(query, (api_key,))
		#print('check_api_key.sel=', sel)
		if not sel: return False
		return True
		#return self.select(query, (api_key,))

	def get_users(self):
		query = "SELECT username, api_key, is_admin FROM users"
		return self.select(query)

	def insert_random_reading(self): #for testing
		random_data = (
			self.unix_now(),
			random.randint(5, 30),
			random.randint(0, 100),
			random.randint(0, 100)
		)
		return self.insert_sensors_reading(random_data)

	def insert_random_act_record(self): #for testing
		now = self.unix_now()
		random_data = (
			'fan_01',
			'ventilation',
			now,
			now+random.randint(1000, 60000),
			1,
			2,
			3
		)
		return self.insert_device_record(random_data)

	def get_hash(self, pwd):
		return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

	def unix_now(self):
		return int(time.time()*1000)

def datetime2unix(dt):
	return int(time.mktime(dt.timetuple())*1000)

def setup_db(user, password, database):
	admin_pwd = 'raspberry314'

	table_sensors = (
		"CREATE TABLE `sensors_readings` ("
		"  `datetime` BIGINT UNSIGNED NOT NULL,"
		"  `temperature` FLOAT(16, 1),"
		"  `humidity` FLOAT(16, 1),"
		"  `moisture` FLOAT(16, 1),"
		"  PRIMARY KEY (`datetime`)"
		") ENGINE=InnoDB")

	table_costs = (
		"CREATE TABLE `costs` ("
		"  `device` CHAR(64) NOT NULL,"
		"  `model_type` CHAR(64) NOT NULL,"
		"  `start` BIGINT UNSIGNED NOT NULL,"
		"  `end` BIGINT UNSIGNED NOT NULL,"
		"  `kwh` FLOAT(16, 4),"
		"  `l` FLOAT(16, 4),"
		"  `cost` FLOAT(16, 4),"
		"  PRIMARY KEY (`device`, `start`)"
		") ENGINE=InnoDB")

	table_users = (
		"CREATE TABLE `users` ("
		"  `username` CHAR(20) NOT NULL,"
		"  `pwd_hash` CHAR(64) NOT NULL,"
		"  `api_key` CHAR(64) NOT NULL,"
		"  `is_admin` BOOLEAN NOT NULL,"
		"  PRIMARY KEY (`username`),"
		"  UNIQUE (`api_key`)"
		") ENGINE=InnoDB")

	table_logins = (
		"CREATE TABLE `logins` ("
		"  `username` CHAR(20) NOT NULL,"
		"  `datetime` BIGINT UNSIGNED NOT NULL,"
		"  `success` BOOLEAN NOT NULL,"
		"  PRIMARY KEY (`username`, `datetime`)"
		") ENGINE=InnoDB")

	try:
		connection = mysql.connector.connect(user=user, password=password)
		cursor = connection.cursor()

		cursor.execute("DROP DATABASE IF EXISTS {}".format(database))
		cursor.execute("CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(database))
		connection.database = database

		cursor.execute(table_sensors)
		cursor.execute(table_costs)
		cursor.execute(table_users)
		cursor.execute(table_logins)

		admin_pwd_hash = hashlib.sha256(admin_pwd.encode('utf-8')).hexdigest()
		admin_api_key = hashlib.sha1(os.urandom(64)).hexdigest()
		cursor.execute("INSERT INTO users (username, pwd_hash, api_key, is_admin) VALUES (%s, %s, %s, %s)", ('admin', admin_pwd_hash, admin_api_key, True))

		connection.commit()
		cursor.close()
		connection.close()
	except Exception as err:
		print('DB.Setup: "{}"'.format(err))
		return -1
	return 0
