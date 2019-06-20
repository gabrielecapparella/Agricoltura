#!/usr/bin/python3

import devices
import Adafruit_ADS1x15
import sys


if __name__ == '__main__':
    adc = Adafruit_ADS1x15.ADS1115()
    adc.read_adc(sys.argv[1], gain=1)