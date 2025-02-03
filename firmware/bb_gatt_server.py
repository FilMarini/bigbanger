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
from ble_advertising import advertising_payload
import asyncio
from hx711_gpio import HX711
from machine import Pin

from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_PROGRESSOR_SERVICE_UUID = bluetooth.UUID("7e4e1701-1ea6-40c9-9dcc-13d34ffead57")
_PROGRESSOR_DATA_CHAR = (
    bluetooth.UUID("7e4e1702-1ea6-40c9-9dcc-13d34ffead57"),
    _FLAG_READ | _FLAG_NOTIFY,
)
_PROGRESSOR_CONTROL_POINT = (
    bluetooth.UUID("7e4e1703-1ea6-40c9-9dcc-13d34ffead57"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)
_PROGRESSOR_SERVICE = (
    _PROGRESSOR_SERVICE_UUID,
    (_PROGRESSOR_DATA_CHAR, _PROGRESSOR_CONTROL_POINT),
)

""" Progressor Commands """
CMD_TARE_SCALE = 100
CMD_START_WEIGHT_MEAS = 101
CMD_STOP_WEIGHT_MEAS = 102
CMD_START_PEAK_RFD_MEAS = 103
CMD_START_PEAK_RFD_MEAS_SERIES = 104
CMD_ADD_CALIBRATION_POINT = 105
CMD_SAVE_CALIBRATION = 106
CMD_GET_APP_VERSION = 107
CMD_GET_ERROR_INFORMATION = 108
CMD_CLR_ERROR_INFORMATION = 109
CMD_ENTER_SLEEP = 110
CMD_GET_BATTERY_VOLTAGE = 111
CMD_GET_DEVICE_ID = 112

""" Progressor response codes """
RES_CMD_RESPONSE = 0
RES_WEIGHT_MEAS = 1
RES_RFD_PEAK = 2
RES_RFD_PEAK_SERIES = 3
RES_LOW_PWR_WARNING = 4

"""Progressor variables"""
PROG_VER = "1.2.3.4"
BATTERY_VOLTAGE = 3000 #mV
DEVICE_ID = 43
CRASH_MSG = "No crash"

"""Progressor constants"""
PROG_SCALE = {'WH-C07': 32640, 'WH-C100': 30682}

def byte_length(n):
    if n == 0:
        return 1  # Even 0 requires at least 1 byte
    bytes_count = 0
    while n:
        n >>= 8  # Shift 8 bits (1 byte) at a time
        bytes_count += 1
    return bytes_count

class BLEBigBanger:
    def __init__(self, ble, name = 'Progressor_BB', device = 'WH-C07'):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_data, self._handle_control),) = self._ble.gatts_register_services((_PROGRESSOR_SERVICE,))
        self._conn_handle = None
        self._write_callback = None
        self._payload = advertising_payload(services=[_PROGRESSOR_SERVICE_UUID])
        self._payload_resp = advertising_payload(name = name)
        self._sending_data = False
        self._start_time_us = None
        self.tare_scale = False
        self.weight_tare = 0
        self._advertise()
        # Define driver
        pin_OUT = Pin(6, Pin.IN, pull=Pin.PULL_DOWN)
        pin_SCK = Pin(5, Pin.OUT)
        self.driver = HX711(pin_SCK, pin_OUT)
        if device in PROG_SCALE.keys():
            self.driver.set_scale(PROG_SCALE.get(device))
        else:
            self.driver.set_scale(PROG_SCALE.get('WH-C07'))
        self.driver.tare()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            if self._conn_handle is None:  # Only accept the first connection
                print("New connection", conn_handle)
                self._conn_handle = conn_handle
            else:
                print("Already connected. Ignoring additional connection.")
                self._ble.gap_disconnect(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                print("Disconnected", conn_handle)
                self._conn_handle = None
                self._sending_data = False
                self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            if value_handle == self._handle_control:
                self.process_command(value)

    def process_command(self, value):
        value_int = int.from_bytes(value, "big")
        print(f'Command {value_int} received!')
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
            self._start_time_us = time.ticks_us()  # Record the start time in microseconds
        elif value_int == CMD_STOP_WEIGHT_MEAS:
            self._sending_data = False
            self._start_time_us = None
        elif value_int == CMD_TARE_SCALE:
            self.tare_scale = True

    def is_connected(self):
        return self._conn_handle is not None

    def _advertise(self, interval_us=500000):
        print("Starting advertising")
        self._ble.gap_advertise(interval_us, adv_data=self._payload, resp_data=self._payload_resp)

    async def send_data_loop(self):
        while True:
            if self._sending_data:
                # Raw values to send
                weight_raw = self.driver.get_units()
                elapsed_us = time.ticks_diff(time.ticks_us(), self._start_time_us)
                if abs(weight_raw) > 1:
                    print("{:.1f}".format(abs(weight_raw)))
                weight = weight_raw - self.weight_tare
                if self.tare_scale:
                    self.driver.tare()
                    self.tare_scale = False
                # Values to send
                weight_data = bytearray(struct.pack('f', weight))
                elapsed_us_data = bytearray(elapsed_us.to_bytes(4, "little"))
                # Create packet
                size = 8
                byte_array = bytearray([RES_WEIGHT_MEAS, size]) + weight_data + elapsed_us_data
                # Send packet
                if self.is_connected():
                    self._ble.gatts_notify(self._conn_handle, self._handle_data, byte_array)
            await asyncio.sleep_ms(10)  # 10 Hz, give control back to application


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
