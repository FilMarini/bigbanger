# This example demonstrates a UART periperhal.

import bluetooth
import random
import struct
import time
from ble_advertising import advertising_payload
import asyncio

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
#WEIGHTS = [0, 0, 0, 0.2, 0.5, 0.9, 1.5, 2, 3, 5, 6, 7, 8, 9, 9, 9, 9, 9, 9, 9, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
WEIGHTS = [1.1, 1.0, 1.2, 1.0, 1.0, 1.0, 1.1, 1.1, 1.2, 1.0, 1.1]

def byte_length(n):
    if n == 0:
        return 1  # Even 0 requires at least 1 byte
    bytes_count = 0
    while n:
        n >>= 8  # Shift 8 bits (1 byte) at a time
        bytes_count += 1
    return bytes_count

class BLESimplePeripheral:
    def __init__(self, ble, name = "Progressor_BB"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_data, self._handle_control),) = self._ble.gatts_register_services((_PROGRESSOR_SERVICE,))
        self._connections = set()
        self._write_callback = None
        self._payload = advertising_payload(services=[_PROGRESSOR_SERVICE_UUID])
        self._payload_resp = advertising_payload(name = name)
        self._sending_data = False
        self._start_time_us = None
        self.tare_scale = False
        self.weight_tare = 0
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("New connection", conn_handle)
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Disconnected", conn_handle)
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection. Alsways connects when there is an available node.
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
        for conn_handle in self._connections:
            if value_int == CMD_GET_APP_VERSION:
                size = len(PROG_VER)
                byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(PROG_VER.encode('utf-8'))
                self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
            elif value_int == CMD_GET_BATTERY_VOLTAGE:
                pre_size = byte_length(BATTERY_VOLTAGE)
                size = pre_size if pre_size > 4 else 4
                byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(BATTERY_VOLTAGE.to_bytes(size, "little"))
                self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
            elif value_int == CMD_GET_DEVICE_ID:
                pre_size = byte_length(DEVICE_ID)
                size = pre_size if pre_size > 8 else 8
                byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(DEVICE_ID.to_bytes(size, "little"))
                self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
            elif value_int == CMD_GET_ERROR_INFORMATION:
                size = len(CRASH_MSG)
                byte_array = bytearray([RES_CMD_RESPONSE, size]) + bytearray(CRASH_MSG.encode('utf-8'))
                self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
            elif value_int == CMD_START_WEIGHT_MEAS:
                self._sending_data = True
                self._start_time_us = time.ticks_us()  # Record the start time in microseconds
            elif value_int == CMD_STOP_WEIGHT_MEAS:
                self._sending_data = False
                self._start_time_us = None
            elif value_int == CMD_TARE_SCALE:
                self.tare_scale = True

    def is_connected(self):
        return len(self._connections) > 0

    def _advertise(self, interval_us=500000):
        print("Starting advertising")
        self._ble.gap_advertise(interval_us, adv_data=self._payload, resp_data=self._payload_resp)

    async def send_data_loop(self):
        i = 0
        while True:
            if self._sending_data and self.is_connected():
                # Raw values to send
                elapsed_us = time.ticks_diff(time.ticks_us(), self._start_time_us)  # Calculate elapsed microseconds
                weight = WEIGHTS[i%len(WEIGHTS)] - self.weight_tare
                if self.tare_scale:
                    self.weight_tare = weight
                    self.tare_scale = False
                # Values to send
                weight_data = bytearray(struct.pack('f', weight))
                elapsed_us_data = bytearray(elapsed_us.to_bytes(4, "little"))
                # Create packet
                size = 8
                byte_array = bytearray([RES_WEIGHT_MEAS, size]) + weight_data + elapsed_us_data
                for conn_handle in self._connections:
                    data = f"Data {i}, Elapsed: {elapsed_us} µs"
                    print(f"Sending: {data}")
                    self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
                    i += 1
            await asyncio.sleep(0.2)  # Adjust the interval as needed



async def demo():
    ble = bluetooth.BLE()
    p = BLESimplePeripheral(ble)

    # Start the data sending loop
    asyncio.create_task(p.send_data_loop())

    # Keep the main loop running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(demo())
