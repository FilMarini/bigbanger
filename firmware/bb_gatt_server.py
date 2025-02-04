"""
Repository: https://github.com/FilMarini/bigbanger
License: Apache License, Version 2.0

Notes:
This file is part of an open-source project. Feel free to contribute or report issues on the project's repository.

"""

import bluetooth
import random
import struct
import time
import asyncio
from micropython import const
from ble_advertising import advertising_payload
from machine import Pin

# User imports
from config import *
from utils import *
from hx711_bb import *

class BLEBigBanger:
    def __init__(self, ble, name = 'Progressor_BB', device = 'WH-C07'):
        # Initialize BLE
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_data, self._handle_control),) = self._ble.gatts_register_services((PROGRESSOR_SERVICE,))
        self._conn_handle = None
        self._write_callback = None
        self._payload = advertising_payload(services=[PROGRESSOR_SERVICE_UUID])
        self._payload_resp = advertising_payload(name = name)
        # Initialize flags
        self._sending_data = False
        self._tare_scale = False
        self._advertise()
        # Define HX711 driver
        pin_OUT = Pin(6, Pin.IN, pull=Pin.PULL_DOWN)
        pin_SCK = Pin(5, Pin.OUT)
        self.driver = HX711BB(clock = pin_SCK, data = pin_OUT, device = device)

    def _irq(self, event, data):
        """BLE connection manager"""
        # Track connections so we can send notifications.
        if event == IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            if self._conn_handle is None:  # Only accept the first connection
                #self.logger.debug("New connection", conn_handle)
                self._conn_handle = conn_handle
            else:
                #self.logger.warning("Already connected. Ignoring additional connection.")
                self._ble.gap_disconnect(conn_handle)
        elif event == IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                #self.logger.debug("Disconnected", conn_handle)
                self._conn_handle = None
                self._sending_data = False
                self._advertise()
        elif event == IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            if value_handle == self._handle_control:
                self._process_command(value)

    def _process_command(self, value):
        """Define BLE commands and responses"""
        value_int = int.from_bytes(value, "big")
        #self.logger.debug(f'Command {value_int} received!')
        if value_int == CMD_GET_APP_VERSION:
            size = len(PROG_VER)
            byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(PROG_VER.encode('utf-8'))
            self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
        elif value_int == CMD_GET_BATTERY_VOLTAGE:
            pre_size = byte_length(BATTERY_VOLTAGE)
            size = pre_size if pre_size > 4 else 4
            byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(BATTERY_VOLTAGE.to_bytes(size, "little"))
            self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
        elif value_int == CMD_GET_DEVICE_ID:
            pre_size = byte_length(DEVICE_ID)
            size = pre_size if pre_size > 8 else 8
            byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(DEVICE_ID.to_bytes(size, "little"))
            self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
        elif value_int == CMD_GET_ERROR_INFORMATION:
            size = len(CRASH_MSG)
            byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(CRASH_MSG.encode('utf-8'))
            self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
        elif value_int == CMD_START_WEIGHT_MEAS:
            self._sending_data = True
            self.driver.set_start_time(time.ticks_us())  # Record the start time in microseconds
        elif value_int == CMD_STOP_WEIGHT_MEAS:
            self._sending_data = False
            self.driver.set_start_time_us(None)
        elif value_int == CMD_TARE_SCALE:
            self._tare_scale = True

    def is_connected(self):
        """Is the BigBanger connected?"""
        return self._conn_handle is not None

    def _advertise(self, interval_us=500000):
        """Start BLE advertising if not connected"""
        #self.logger.debug("Starting advertising")
        self._ble.gap_advertise(interval_us, adv_data=self._payload, resp_data=self._payload_resp)

    async def send_data_loop(self):
        """Send weight data over BLE"""
        while True:
            if self._sending_data:
                # Tare scale if tare command is received from the app
                if self._tare_scale:
                    self.driver.tare()
                    self._tare_scale = False
                # Get weight measurement
                byte_array = self.driver.get_ble_pkt()
                # Send packet
                if self.is_connected():
                    self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
            await asyncio.sleep_ms(10)  # 100 Hz, Ok for 80 Hz of HX711


async def demo(name = 'Progressor_BB', device = 'WH-C07'):
    ble = bluetooth.BLE()
    p = BLEBigBanger(ble, name = name, device = device)

    # Start the data sending loop
    asyncio.create_task(p.send_data_loop())

    # Keep the main loop running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(demo())
