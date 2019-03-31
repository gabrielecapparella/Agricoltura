#!/usr/bin/python3

import unittest
from sensors import Sensors

# python3 -m unittest -v sensors_test.py
# these are not unit testing
class sensor_test(unittest.TestCase):

	def setUp(self):
		# I put these dict here because sometimes I change their values during tests
		self.thresholds = {
			"min_soil_moist": 5.0,
			"interval_min": 1.0,
			"max_temp": 33.0,
			"max_soil_moist": 60.0,
			"min_temp": 15.0,
			"max_hum": 30.0
		}

		self.deltas = {
			"moist_max_delta": 20.0,
			"max_temp_delta": 5.0,
			"max_hum_delta": 10.0
		}

		self.devices_cfg = [
			{
				"name": "arctic_f8_pwm",
				"power_pin": 20,
				"wattage": 5,
				"speed_pin": 16,
				"enabled": True,
				"model": "ventilation__pwm_fan",
				"pwm_frequency": 25000
			}
		]

		self.rates = {
			"elec_price": 0.2,
			"water_price": 1.8
		}

		self.light_cfg = []

		self.sensors = Sensors(testing=True,
			devices_cfg=self.devices_cfg,
			thresholds_cfg=self.thresholds,
			deltas_cfg=self.deltas,
			rates_cfg=self.rates,
			light_cfg=self.light_cfg)

	def tearDown(self):
		self.sensors.clean_up()

	def test_operate_ventilation(self):
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing is on
		self.assertEqual(self.sensors.get_active_control(), [False]*4) # nothing is to be controlled

		self.sensors.operate([None, 32, 0, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on

		self.sensors.operate([None, 34, 0, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on

		self.sensors.set_single_active_control(0, True) # ventilation is now controlled
		self.sensors.operate([None, 32, 0, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on

		self.sensors.operate([None, 34, 0, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, True, False, False, None]) # ventilation should be switched on

		self.sensors.operate([None, 32, 0, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # ventilation should be switched off
