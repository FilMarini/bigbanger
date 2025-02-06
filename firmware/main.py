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

    # Check if tarePin is pressed
    if tarePin.value():
        # BigBanger BLE
        ble = bluetooth.BLE()
        p = BLEBigBanger(ble, dataPin = dataPin, clkPin = clkPin, name = name, device = device)

        # Start the data sending loop
        asyncio.create_task(p.send_data_loop())

        # Keep the main loop running
        while True:
            await asyncio.sleep(1)
    else:
        # Turn on LED
        ledPin.value(1)
        # Wait until tarePin is released
        while tarePin.value() == 0:
            await asyncio.sleep(0.1)
        # Define a flag to indicate if button is pressed
        button_pressed = {"state": False}
        # Define driver
        driver = HX711BB(clock = clkPin, data = dataPin, device = device)
        # Attach interrupt with a lambda function
        tarePin.irq(trigger=Pin.IRQ_FALLING, handler=lambda p: button_pressed.update(state = True))
        # Wait for the button to be pressed
        while not button_pressed["state"]:
            await asyncio.sleep(0.1)
        # Calibrate with 5 kg on
        driver.calibrate()

asyncio.run(BigBanger(
    name = 'Progressor_BB', # Bluetooth advertising name, must start with "Progressor"
    device = 'WH-C07'       # Host device. Supported values are 'WH-C07', 'WH-C100'
))
