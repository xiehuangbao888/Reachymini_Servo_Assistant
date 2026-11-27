"""Isolated, read-only serial probe. Parent may terminate this process safely."""
import json
import sys

import dynamixel_xl330_backup_restore as core
from microduck_ports import comports


def main():
    port, baud = sys.argv[1], int(sys.argv[2])
    bus = None
    core.print = lambda *args, **kwargs: None
    try:
        if port not in {p.device for p in comports()}:
            raise ValueError('串口不存在，请刷新串口列表。')
        bus = core.DxlBus(port, baud)
        bus.open()
        bus.port.ser.write_timeout = 1.0
        devices = bus.broadcast_scan()
        result = dict(devices=devices)
    except Exception as exc:
        result = dict(error=f'串口连接或扫描失败：{exc}')
    finally:
        if bus:
            bus.close()
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
