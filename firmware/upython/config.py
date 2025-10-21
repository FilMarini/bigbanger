"""
Repository: https://github.com/FilMarini/bigbanger
License: Apache License, Version 2.0

Notes:
This file is part of an open-source project. Feel free to contribute or report issues on the project's repository.

"""

import bluetooth
from micropython import const

""" Event IDs """
IRQ_CENTRAL_CONNECT = const(1)
IRQ_CENTRAL_DISCONNECT = const(2)
IRQ_GATTS_WRITE = const(3)

""" BLE Flags """
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

""" Progressor UUIDs """
PROGRESSOR_SERVICE_UUID = bluetooth.UUID("7e4e1701-1ea6-40c9-9dcc-13d34ffead57")
_PROGRESSOR_DATA_CHAR = (
    bluetooth.UUID("7e4e1702-1ea6-40c9-9dcc-13d34ffead57"),
    _FLAG_READ | _FLAG_NOTIFY,
)
_PROGRESSOR_CONTROL_POINT = (
    bluetooth.UUID("7e4e1703-1ea6-40c9-9dcc-13d34ffead57"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)
PROGRESSOR_SERVICE = (
    PROGRESSOR_SERVICE_UUID,
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

""" Progressor variables """
PROG_VER = "1.2.3.4"
BATTERY_VOLTAGE = 3000 #mV
DEVICE_ID = 43
CRASH_MSG = "No crash"

""" Progressor constants """
PROG_SCALE = {'WH-C07': 32640, 'WH-C100': 30682}

