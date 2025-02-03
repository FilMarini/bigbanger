from bb_gatt_server import *

asyncio.run(demo(
    name = 'Progressor_BB', # Bluetooth advertising name, must start with "Progressor"
    device = 'WH-C07'       # Host device. Supported values are 'WH-C07', 'WH-C100'
))
