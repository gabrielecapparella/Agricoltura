#!/usr/bin/python3

import unittest
from sensors import Sensors
from time import sleep
from datetime import datetime, timedelta

# venv-agricoltura/bin/python3 -m unittest -v sensors_test.py
# these are not unit tests, I want to test for collateral effects too
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

		self.rates = {
			"elec_price": 0.2,
			"water_price": 1.8
		}

		self.sensors = Sensors(
			testing=True,
			devices_cfg="",
			thresholds_cfg=self.thresholds,
			deltas_cfg=self.deltas,
			rates_cfg=self.rates,
			light_cfg=[]
		)

	def tearDown(self):
		self.sensors.clean_up()

	def test_operate_ventilation(self):
		self.sensors.add_device({
				"name": "arctic_f8_pwm",
				"power_pin": 21,
				"wattage": 5,
				"speed_pin": 20,
				"enabled": True,
				"model": "ventilation__pwm_fan",
				"pwm_frequency": 25000
			})

		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing is on
		self.assertFalse(self.sensors.get_dev_state("arctic_f8_pwm")[0])
		self.assertEqual(self.sensors.get_active_control(), [False]*4) # nothing is to be controlled

		self.sensors.operate([None, 32, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("arctic_f8_pwm")[0])


		self.sensors.operate([None, 34, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("arctic_f8_pwm")[0])

		self.sensors.set_single_active_control(0, True) # ventilation is now controlled

		self.sensors.operate([None, 32, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("arctic_f8_pwm")[0])

		self.sensors.operate([None, 34, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, True, False, False, None]) # ventilation should be switched on
		self.assertTrue(self.sensors.get_dev_state("arctic_f8_pwm")[0])

		self.sensors.operate([None, 32, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # ventilation should be switched off
		self.assertFalse(self.sensors.get_dev_state("arctic_f8_pwm")[0])

	def test_operate_heating(self):
		self.sensors.add_device({
				"enabled": True,
				"model": "heating__simple_switch",
				"power_pin": 21,
				"wattage": 150,
				"name": "halogen_light_150W"
			})

		self.sensors.operate([None, 14, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("halogen_light_150W"))

		self.sensors.set_single_active_control(1, True) # heating is now controlled

		self.sensors.operate([None, 16, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("halogen_light_150W"))

		self.sensors.operate([None, 14, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, True, False, None]) # heating should be switched on
		self.assertTrue(self.sensors.get_dev_state("halogen_light_150W"))

		self.sensors.operate([None, 16, 0, 0]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # heating should be switched off
		self.assertFalse(self.sensors.get_dev_state("halogen_light_150W"))

	def test_operate_irrigation(self):
		self.sensors.parse_devices([
			{
				"name": "drippers_1",
				"power_pin": 21,
				"water_flow": 0.1,
				"cycle_spread_time": 10,
				"wattage": 5,
				"model": "irrigation__simple_switch",
				"enabled": True,
				"cycle_water_time": 5
			},
			{
				"name": "drippers_2",
				"power_pin": 21,
				"water_flow": 0.1,
				"cycle_spread_time": 10,
				"wattage": 5,
				"model": "irrigation__simple_switch",
				"enabled": True,
				"cycle_water_time": 5
			}
		])

		self.sensors.operate([None, 0, 0, 4]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("drippers_1")[0])
		self.assertFalse(self.sensors.get_dev_state("drippers_2")[0])

		self.sensors.set_single_active_control(3, True) # irrigation is now controlled

		self.sensors.operate([None, 0, 0, 6]) # [dt, temp, hum, moist]
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, None]) # nothing should be on
		self.assertFalse(self.sensors.get_dev_state("drippers_1")[0])
		self.assertFalse(self.sensors.get_dev_state("drippers_2")[0])

		self.sensors.operate([None, 0, 0, 4]) # [dt, temp, hum, moist]
		# both drippers should be switched on and with watering_state = 1
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, ["drippers_1", "drippers_2"]])
		drippers_states = self.sensors.get_dev_state(["drippers_1", "drippers_2"])
		self.assertTrue(drippers_states["drippers_1"][0])
		self.assertEqual(drippers_states["drippers_1"][2], 1)
		self.assertTrue(drippers_states["drippers_2"][0])
		self.assertEqual(drippers_states["drippers_2"][2], 1)

		# I force the drippers to finish one at a time
		self.sensors.devices["drippers_1"].set_state(False)
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, ["drippers_2"]])
		self.sensors.devices["drippers_2"].set_state(False)
		self.assertEqual(self.sensors.get_state(), [True, False, False, False, []])
		drippers_states = self.sensors.get_dev_state(["drippers_1", "drippers_2"])
		self.assertFalse(drippers_states["drippers_1"][0])
		self.assertEqual(drippers_states["drippers_1"][2], 0)
		self.assertFalse(drippers_states["drippers_2"][0])
		self.assertEqual(drippers_states["drippers_2"][2], 0)

	def test_check_lights_schedule(self):
		self.sensors.add_device({
			"enabled": True,
			"model": "grow_lights__simple_switch",
			"power_pin": 21,
			"wattage": 50,
			"name": "led_light_50W"
		})

		# no jobs, no activity expected
		self.assertEqual(self.sensors.g_lights_schedule, [])
		self.sensors.check_lights_schedule()
		self.assertFalse(self.sensors.get_dev_state("led_light_50W"))

		# light does not exists, no activity expected
		self.sensors.update_lights_schedule([["different_name", "1983-03-21 00:00", 1, 2, True]])
		self.sensors.check_lights_schedule()
		self.assertFalse(self.sensors.get_dev_state("led_light_50W"))

		# simple job, no activity expected because when is too old
		self.sensors.update_lights_schedule([["led_light_50W", "1983-03-21 00:00", 0.001, 1, True]]) # 0.001h = 3.6s
		self.sensors.check_lights_schedule()
		self.assertFalse(self.sensors.get_dev_state("led_light_50W"))

