"""
Repository: https://github.com/FilMarini/bigbanger
License: Apache License, Version 2.0

Notes:
This file is part of an open-source project. Feel free to contribute or report issues on the project's repository.

"""

import asyncio
from machine import Pin

# User imports
from config import *
from utils import *
from hx711_bb import *
from bb_gatt_server import *

async def BigBanger(name = 'Progressor_BB', device = 'WH-C07'):
    # Define pins
    dataPin = Pin(6, Pin.IN, pull=Pin.PULL_DOWN)
    clkPin = Pin(5, Pin.OUT)
    ledPin = Pin(4, Pin.OUT)
    tarePin = Pin(9, Pin.IN)

    # BLE
    ble = bluetooth.BLE()
    p = BLEBigBanger(
        ble,
        dataPin = dataPin,
        clkPin = clkPin,
        tarePin = tarePin,
        ledPin = ledPin,
        name = name,
        device = device)

    # Keep the main loop running
    while True:
        await asyncio.sleep(1)

asyncio.run(BigBanger(
    name = 'Progressor_BB', # Bluetooth advertising name, must start with "Progressor"
    device = 'WH-C07'       # Host device. Supported values are 'WH-C07', 'WH-C100'
))
