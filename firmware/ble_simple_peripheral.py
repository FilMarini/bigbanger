# This example demonstrates a UART periperhal.

import bluetooth
import random
import struct
import time
from ble_advertising import advertising_payload

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

""" Progressor response codes """
RES_CMD_RESPONSE = 0
RES_WEIGHT_MEAS = 1
RES_RFD_PEAK = 2
RES_RFD_PEAK_SERIES = 3
RES_LOW_PWR_WARNING = 4

"""Progressor variables"""
PROG_VER = "v0.1"

class BLESimplePeripheral:
    def __init__(self, ble, name = "Progressor_1234"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_data, self._handle_control),) = self._ble.gatts_register_services((_PROGRESSOR_SERVICE,))
        self._connections = set()
        self._write_callback = None
        self._payload = advertising_payload(services=[_PROGRESSOR_SERVICE_UUID])
        self._payload_resp = advertising_payload(name = name)
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
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            #print(f'value = {value}') # b'k' = 107
            #print(f'value handle = {value_handle}') # 19
            #print(f'data handle = {self._handle_data}') # 16
            #print(f'control handle = {self._handle_control}') # 19
            if value_handle == self._handle_control:
                for conn_handle in self._connections:
                    if int.from_bytes(value, "big") == CMD_GET_APP_VERSION:
                        byte_array = bytearray([RES_CMD_RESPONSE, len(PROG_VER)]) + bytearray(PROG_VER.encode('utf-8'))
                        self._ble.gatts_notify(conn_handle, self._handle_data, byte_array)
                        #print("app version data sent")


    def send(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._handle_tx, data)

    def is_connected(self):
        return len(self._connections) > 0

    def _advertise(self, interval_us=500000):
        print("Starting advertising")
        self._ble.gap_advertise(interval_us, adv_data=self._payload, resp_data=self._payload_resp)

    def on_write(self, callback):
        self._write_callback = callback


def demo():
    ble = bluetooth.BLE()
    p = BLESimplePeripheral(ble)

    def on_rx(v):
        print("RX", v)

    p.on_write(on_rx)

    i = 0
    while True:
        if p.is_connected():
            # Short burst of queued notifications.
            for _ in range(3):
                data = str(i) + "_"
                print("TX", data)
                p.send(data)
                i += 1
        time.sleep_ms(100)


if __name__ == "__main__":
    demo()
