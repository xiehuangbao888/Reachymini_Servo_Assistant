"""Include Microduck's onboard UART, which pyserial does not enumerate."""
from pathlib import Path
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo


def comports():
    ports = list(list_ports.comports())
    if Path('/dev/ttyS2').is_char_device() and not any(p.device == '/dev/ttyS2' for p in ports):
        port = ListPortInfo('/dev/ttyS2')
        port.description = 'Microduck onboard servo bus'
        ports.append(port)
    return ports
