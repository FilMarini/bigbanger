"""
Repository: https://github.com/FilMarini/bigbanger
License: Apache License, Version 2.0

Notes:
This file is part of an open-source project. Feel free to contribute or report issues on the project's repository.

"""

import time
from hx711_gpio import HX711

# User imports
from config import *

class HX711BB(HX711):
    def __init__(self, device = 'WH-C07', start_time_us = None, **kwargs):
        super().__init__(**kwargs)
        # Set scale
        if device in PROG_SCALE.keys():
            self.driver.set_scale(PROG_SCALE.get(device))
        else:
            self.driver.set_scale(PROG_SCALE.get('WH-C07'))
        # Tare
        self.driver.tare()
        # Vars
        self._start_time_us = start_time

    def get_ble_units(self):
        """Read weigth with user tare and scale and convert it to bytearray for BLE"""
        weight_raw = self.driver.get_units()
        weight_data = bytearray(struct.pack('f', weight_raw))
        return weight_data

    def get_ble_pkt(self):
        """Get a full BLE packet for Progressor API"""
        # Get weight
        weight_data = self.get_ble_units()
        # Get time
        elapsed_us = time.ticks_diff(time.ticks_us(), self._start_time_us)
        elapsed_us_data = bytearray(elapsed_us.to_bytes(4, "little"))
        # Create packet
        size = 8
        byte_pkt = bytearray([RES_WEIGHT_MEAS, size]) + weight_data + elapsed_us_data
        return byte_pkt

    def set_start_time(self, new_time):
        """Sets start_time to a specific value."""
        self.start_time = new_time

