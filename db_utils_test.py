#!/usr/bin/python3

import unittest
import db_utils
from db_utils import datetime2unix as d2u
from datetime import datetime as dt

#python3 -m unittest -v db_utils_test.py
class db_utils_test(unittest.TestCase):

	def setUp(self):
		self.db = db_utils.DB_Connection(testing=True)

	def tearDown(self):
		self.db.clean_up()

	def test_insertTrue(self):
		self.assertTrue(self.db.insert_random_reading())

	def test_insertWithoutKey(self):
		test_data = (None, 1, 2, 3)
		self.assertFalse(self.db.insert_sensors_reading(test_data))

	def test_rawSelectEmpty(self):
		self.assertEqual(self.db.select("SELECT * FROM sensors_readings"), [])

	def test_rawSelect(self):
		self.db.insert_random_reading()
		self.assertEqual(len(self.db.select("SELECT * FROM sensors_readings")), 1)

	def test_get_last_reading(self):
		test_data1 = (d2u(dt(1973, 3, 1, 0, 0, 0)), 1, 2, 3)
		test_data2 = (d2u(dt(1973, 3, 1, 0, 0, 5)), 4, 5, 6)

		self.db.insert_sensors_reading(test_data1)
		self.db.insert_sensors_reading(test_data2)

		query = self.db.get_last_reading()

		self.assertEqual(query, test_data2)

	def test_get_readings_between(self):
		test_data1 = (d2u(dt(1975, 9, 12, 0, 0, 0)), 1, 2, 3)
		test_data2 = (d2u(dt(1977, 1, 23, 0, 0, 0)), 4, 5, 6)
		test_data3 = (d2u(dt(1979, 11, 30, 0, 0, 0)), 7, 8, 9)

		self.db.insert_sensors_reading(test_data1)
		self.db.insert_sensors_reading(test_data2)
		self.db.insert_sensors_reading(test_data3)

		query1 = self.db.get_readings(d2u(dt(1976, 1, 2, 3, 4, 5)), d2u(dt(1978, 1, 2, 3, 4, 5)))
		query2 = self.db.get_readings(d2u(dt(1983, 3, 21, 0, 0, 0)), d2u(dt(1994, 3, 28, 0, 0, 0)))
		query3 = self.db.get_readings(d2u(dt(1968, 6, 29, 0, 0, 0)), d2u(dt(1977, 1, 24, 0, 0, 0)))

		self.assertEqual(query1, [test_data2])
		self.assertEqual(query2, [])
		self.assertEqual(query3, [test_data1, test_data2])

	def test_get_readings_from(self):
		test_data1 = (d2u(dt(1975, 9, 12, 0, 0, 0)), 1, 2, 3)
		test_data2 = (d2u(dt(1977, 1, 23, 0, 0, 0)), 4, 5, 6)
		test_data3 = (d2u(dt(1979, 11, 30, 0, 0, 0)), 7, 8, 9)

		self.db.insert_sensors_reading(test_data1)
		self.db.insert_sensors_reading(test_data2)
		self.db.insert_sensors_reading(test_data3)

		query1 = self.db.get_readings(d2u(dt(1975, 9, 12, 0, 0, 0)))
		query2 = self.db.get_readings(d2u(dt(1976, 3, 21, 0, 0, 0)))
		query3 = self.db.get_readings(d2u(dt(1980, 1, 1, 0, 0, 0)))

		self.assertEqual(query1, [test_data1, test_data2, test_data3])
		self.assertEqual(query2, [test_data2, test_data3])
		self.assertEqual(query3, [])

	def test_get_readings_all(self):
		test_data1 = (d2u(dt(1975, 9, 12, 0, 0, 0)), 1, 2, 3)
		test_data2 = (d2u(dt(1977, 1, 23, 0, 0, 0)), 4, 5, 6)
		test_data3 = (d2u(dt(1979, 11, 30, 0, 0, 0)), 7, 8, 9)

		self.db.insert_sensors_reading(test_data1)
		self.db.insert_sensors_reading(test_data2)
		self.db.insert_sensors_reading(test_data3)

		query = self.db.get_readings()

		self.assertEqual(query, [test_data1, test_data2, test_data3])

	def test_get_readings_with_null(self):
		test_data1 = (d2u(dt(1975, 9, 12, 0, 0, 0)), None, 2, 3)
		test_data2 = (d2u(dt(1977, 1, 23, 0, 0, 0)), None, None, 6)
		test_data3 = (d2u(dt(1979, 11, 30, 0, 0, 0)), None, None, None)

		self.db.insert_sensors_reading(test_data1)
		self.db.insert_sensors_reading(test_data2)
		self.db.insert_sensors_reading(test_data3)

		query1 = self.db.get_readings()
		query2 = self.db.get_readings(what='temperature,humidity')
		query3 = self.db.get_readings(what='humidity,moisture')
		query4 = self.db.get_readings(what='moisture')

		self.assertEqual(query1, [])
		self.assertEqual(query2, [])
		self.assertEqual(query3, [(2,3)])
		self.assertEqual(query4, [(3,), (6,)])

	def test_insert_user(self):
		self.assertTrue(self.db.insert_user({'username':'david', 'password':'gilmour', 'is_admin':False}))

	def test_two_user_with_same_username(self):
		self.db.insert_user({'username':'david', 'password':'gilmour', 'is_admin':False})
		self.assertFalse(self.db.insert_user({'username':'david', 'password':'jon', 'is_admin':False}))

	def test_check_credentials_true(self):
		self.db.insert_user({'username':'david', 'password':'gilmour123', 'is_admin':False})
		self.assertTrue(self.db.check_credentials('david', 'gilmour123'))

	def test_check_credentials_false(self):
		self.db.insert_user({'username':'david', 'password':'gilmour', 'is_admin':False})
		self.assertFalse(self.db.check_credentials('david', 'waters'))
		self.assertFalse(self.db.check_credentials('roger', 'gilmour'))

if __name__ == '__main__':
	unittest.main(warnings='ignore')
