#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DYNAMIXEL XL330 backup / restore tool
Supports:
  - XL330-M288 (Model Number 1200)
  - XL330-M077 (Model Number 1190)
  - Protocol 2.0
  - Windows / Ubuntu Linux / macOS

Install:
    pip install dynamixel-sdk pyserial

Safety:
  - Backup reads the full Control Table defined below.
  - Restore writes only configuration items, RAM tuning/configuration and
    Indirect Address mappings.
  - Runtime status is never written.
  - Goal Position / Goal Velocity / Goal Current / Goal PWM are NOT restored
    automatically to prevent unexpected motion.
  - Torque remains OFF after restore.
  - Every restored register is checked, and a final verification scan/readback
    is performed.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from serial.tools import list_ports
except ImportError:
    print("ERROR: pyserial is not installed.")
    print("Install with: pip install pyserial")
    sys.exit(1)

try:
    from dynamixel_sdk import (
        PortHandler,
        PacketHandler,
        COMM_SUCCESS,
    )
except ImportError:
    print("ERROR: dynamixel-sdk is not installed.")
    print("Install with: pip install dynamixel-sdk")
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

PROTOCOL_VERSION = 2.0

SUPPORTED_MODELS = {
    1190: "XL330-M077",
    1200: "XL330-M288",
}

BAUD_CODE_TO_BPS = {
    0: 9_600,
    1: 57_600,
    2: 115_200,
    3: 1_000_000,
    4: 2_000_000,
    5: 3_000_000,
    6: 4_000_000,
}

BPS_TO_BAUD_CODE = {v: k for k, v in BAUD_CODE_TO_BPS.items()}

COMMON_BAUDRATES = [
    9_600,
    57_600,
    115_200,
    1_000_000,
    2_000_000,
    3_000_000,
    4_000_000,
]

ADDR_ID = 7
ADDR_BAUD_RATE = 8
ADDR_OPERATING_MODE = 11
ADDR_PROTOCOL_TYPE = 13
ADDR_TORQUE_ENABLE = 64
ADDR_STATUS_RETURN_LEVEL = 68

# Delay between TxOnly write and readback.
WRITE_VERIFY_DELAY = 0.010


# =============================================================================
# XL330-M077 / XL330-M288 common Control Table
#
# tuple:
#   (name, address, size, signed, access, area, category)
#
# The two models use the same Control Table layout; model number is used
# to prevent writing an M288 profile into an M077 and vice versa.
# =============================================================================

CONTROL_TABLE = [
    # EEPROM - Device information
    ("Model Number",            0,   2, False, "R",  "EEPROM", "device_info"),
    ("Model Information",       2,   4, False, "R",  "EEPROM", "device_info"),
    ("Firmware Version",        6,   1, False, "R",  "EEPROM", "device_info"),

    # EEPROM - Configuration
    ("ID",                      7,   1, False, "RW", "EEPROM", "configuration"),
    ("Baud Rate",               8,   1, False, "RW", "EEPROM", "configuration"),
    ("Return Delay Time",       9,   1, False, "RW", "EEPROM", "configuration"),
    ("Drive Mode",             10,   1, False, "RW", "EEPROM", "configuration"),
    ("Operating Mode",         11,   1, False, "RW", "EEPROM", "configuration"),
    ("Secondary ID",           12,   1, False, "RW", "EEPROM", "configuration"),
    ("Protocol Type",          13,   1, False, "RW", "EEPROM", "configuration"),
    ("Homing Offset",          20,   4, True,  "RW", "EEPROM", "configuration"),
    ("Moving Threshold",       24,   4, False, "RW", "EEPROM", "configuration"),
    ("Temperature Limit",      31,   1, False, "RW", "EEPROM", "configuration"),
    ("Max Voltage Limit",      32,   2, False, "RW", "EEPROM", "configuration"),
    ("Min Voltage Limit",      34,   2, False, "RW", "EEPROM", "configuration"),
    ("PWM Limit",              36,   2, False, "RW", "EEPROM", "configuration"),
    ("Current Limit",          38,   2, False, "RW", "EEPROM", "configuration"),
    ("Velocity Limit",         44,   4, False, "RW", "EEPROM", "configuration"),
    ("Max Position Limit",     48,   4, False, "RW", "EEPROM", "configuration"),
    ("Min Position Limit",     52,   4, False, "RW", "EEPROM", "configuration"),
    ("Startup Configuration",  60,   1, False, "RW", "EEPROM", "configuration"),
    ("PWM Slope",              62,   1, False, "RW", "EEPROM", "configuration"),
    ("Shutdown",               63,   1, False, "RW", "EEPROM", "configuration"),

    # RAM
    ("Torque Enable",          64,   1, False, "RW", "RAM", "runtime_command"),
    ("LED",                    65,   1, False, "RW", "RAM", "runtime_command"),
    ("Status Return Level",    68,   1, False, "RW", "RAM", "ram_configuration"),
    ("Registered Instruction", 69,   1, False, "R",  "RAM", "runtime_status"),
    ("Hardware Error Status",  70,   1, False, "R",  "RAM", "runtime_status"),

    ("Velocity I Gain",        76,   2, False, "RW", "RAM", "ram_configuration"),
    ("Velocity P Gain",        78,   2, False, "RW", "RAM", "ram_configuration"),
    ("Position D Gain",        80,   2, False, "RW", "RAM", "ram_configuration"),
    ("Position I Gain",        82,   2, False, "RW", "RAM", "ram_configuration"),
    ("Position P Gain",        84,   2, False, "RW", "RAM", "ram_configuration"),
    ("Feedforward 2nd Gain",   88,   2, False, "RW", "RAM", "ram_configuration"),
    ("Feedforward 1st Gain",   90,   2, False, "RW", "RAM", "ram_configuration"),

    ("Bus Watchdog",           98,   1, False, "RW", "RAM", "ram_configuration"),

    # Runtime commands - backed up for inspection, not restored by default
    ("Goal PWM",              100,   2, True,  "RW", "RAM", "runtime_command"),
    ("Goal Current",          102,   2, True,  "RW", "RAM", "runtime_command"),
    ("Goal Velocity",         104,   4, True,  "RW", "RAM", "runtime_command"),

    # RAM configuration
    ("Profile Acceleration",  108,   4, False, "RW", "RAM", "ram_configuration"),
    ("Profile Velocity",      112,   4, False, "RW", "RAM", "ram_configuration"),

    # Runtime command
    ("Goal Position",         116,   4, True,  "RW", "RAM", "runtime_command"),

    # Runtime status
    ("Realtime Tick",         120,   2, False, "R",  "RAM", "runtime_status"),
    ("Moving",                122,   1, False, "R",  "RAM", "runtime_status"),
    ("Moving Status",         123,   1, False, "R",  "RAM", "runtime_status"),
    ("Present PWM",           124,   2, True,  "R",  "RAM", "runtime_status"),
    ("Present Current",       126,   2, True,  "R",  "RAM", "runtime_status"),
    ("Present Velocity",      128,   4, True,  "R",  "RAM", "runtime_status"),
    ("Present Position",      132,   4, True,  "R",  "RAM", "runtime_status"),
    ("Velocity Trajectory",   136,   4, True,  "R",  "RAM", "runtime_status"),
    ("Position Trajectory",   140,   4, True,  "R",  "RAM", "runtime_status"),
    ("Present Input Voltage", 144,   2, False, "R",  "RAM", "runtime_status"),
    ("Present Temperature",   146,   1, False, "R",  "RAM", "runtime_status"),
    ("Backup Ready",          147,   1, False, "R",  "RAM", "runtime_status"),
]


# =============================================================================
# Utility
# =============================================================================

def model_name(model_number):
    return SUPPORTED_MODELS.get(model_number, f"Unknown({model_number})")


def to_signed(value, size):
    bits = size * 8
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        return value - (1 << bits)
    return value


def to_unsigned(value, size):
    return value & ((1 << (size * 8)) - 1)


def hex_value(value, size):
    return "0x" + format(to_unsigned(value, size), f"0{size * 2}X")


def get_indirect_table(firmware_version):
    """
    Firmware >= V53:
      Indirect Address 1..28 = 168..222
      Indirect Data    1..28 = 224..251

    Firmware < V53:
      Indirect Address 1..20 = 168..206
      Indirect Data    1..20 = 208..227
    """
    if firmware_version >= 53:
        count = 28
        indirect_address_start = 168
        indirect_data_start = 224
    else:
        count = 20
        indirect_address_start = 168
        indirect_data_start = 208

    result = []

    for index in range(count):
        number = index + 1
        result.append((
            f"Indirect Address {number}",
            indirect_address_start + index * 2,
            2,
            False,
            "RW",
            "RAM",
            "indirect_address",
        ))

    for index in range(count):
        number = index + 1
        result.append((
            f"Indirect Data {number}",
            indirect_data_start + index,
            1,
            False,
            "RW",
            "RAM",
            "indirect_data",
        ))

    return result


def get_full_control_table(firmware_version):
    return list(CONTROL_TABLE) + get_indirect_table(firmware_version)


def item_by_name(profile, name):
    return profile.get("items", {}).get(name)


def item_value(profile, name, default=None):
    item = item_by_name(profile, name)
    if item is None:
        return default
    return item.get("value", default)


# =============================================================================
# Serial port / baud selection
# =============================================================================

def choose_serial_port():
    while True:
        ports = list(list_ports.comports())

        print("\nDetected serial ports:")
        if ports:
            for i, p in enumerate(ports, start=1):
                description = p.description or ""
                print(f"  {i}. {p.device:24s} {description}")
        else:
            print("  (No serial ports automatically detected)")

        print("  M. Enter port manually")
        print("  R. Refresh port list")

        choice = input("\nSelect serial port: ").strip()

        if choice.lower() == "r":
            continue

        if choice.lower() == "m":
            manual = input(
                "Enter port path (e.g. COM51, /dev/ttyUSB0, /dev/cu.usbserial-xxxx): "
            ).strip()
            if manual:
                return manual
            continue

        try:
            index = int(choice)
        except ValueError:
            print("Invalid selection.")
            continue

        if 1 <= index <= len(ports):
            return ports[index - 1].device

        print("Invalid selection.")


def choose_baudrate(default=1_000_000):
    while True:
        print("\nBaud rate:")
        for i, baud in enumerate(COMMON_BAUDRATES, start=1):
            suffix = "  [default]" if baud == default else ""
            print(f"  {i}. {baud:,} bps{suffix}")
        print("  C. Custom baud rate")

        choice = input(
            f"\nSelect baud rate (Enter = {default:,}): "
        ).strip()

        if not choice:
            return default

        if choice.lower() == "c":
            text = input("Enter baud rate in bps: ").strip().replace(",", "")
            try:
                baud = int(text)
                if baud > 0:
                    return baud
            except ValueError:
                pass
            print("Invalid baud rate.")
            continue

        try:
            index = int(choice)
        except ValueError:
            print("Invalid selection.")
            continue

        if 1 <= index <= len(COMMON_BAUDRATES):
            return COMMON_BAUDRATES[index - 1]

        print("Invalid selection.")


# =============================================================================
# SDK communication wrapper
# =============================================================================

class DxlBus:
    def __init__(self, device, baudrate):
        self.device = device
        self.baudrate = baudrate
        self.port = PortHandler(device)
        self.packet = PacketHandler(PROTOCOL_VERSION)
        self.alert_warned_ids = set()

    def open(self):
        if not self.port.openPort():
            raise RuntimeError(f"Cannot open serial port: {self.device}")

        if not self.port.setBaudRate(self.baudrate):
            self.port.closePort()
            raise RuntimeError(f"Cannot set baud rate: {self.baudrate}")

    def close(self):
        try:
            self.port.closePort()
        except Exception:
            pass

    def set_baudrate(self, baudrate):
        if self.baudrate == baudrate:
            return
        if not self.port.setBaudRate(baudrate):
            raise RuntimeError(f"Cannot change host baud rate to {baudrate}")
        self.baudrate = baudrate
        time.sleep(0.02)

    def _check_error(self, dxl_id, address, comm_result, dxl_error, operation):
        if comm_result != COMM_SUCCESS:
            raise RuntimeError(
                f"{operation} ID={dxl_id} Address={address}: "
                f"{self.packet.getTxRxResult(comm_result)}"
            )

        # Protocol 2.0: bit 7 is Hardware Alert, bits 0..6 are instruction error.
        hardware_alert = bool(dxl_error & 0x80)
        instruction_error = dxl_error & 0x7F

        if instruction_error:
            raise RuntimeError(
                f"{operation} ID={dxl_id} Address={address}: "
                f"Instruction Error 0x{instruction_error:02X}: "
                f"{self.packet.getRxPacketError(instruction_error)}"
            )

        if hardware_alert and dxl_id not in self.alert_warned_ids:
            self.alert_warned_ids.add(dxl_id)
            print(
                f"\n[WARNING] ID {dxl_id}: Hardware Alert is active. "
                "Communication continues; check Hardware Error Status(70).\n"
            )

    def read_register(self, dxl_id, address, size, signed=False):
        if size == 1:
            value, comm_result, dxl_error = self.packet.read1ByteTxRx(
                self.port, dxl_id, address
            )
        elif size == 2:
            value, comm_result, dxl_error = self.packet.read2ByteTxRx(
                self.port, dxl_id, address
            )
        elif size == 4:
            value, comm_result, dxl_error = self.packet.read4ByteTxRx(
                self.port, dxl_id, address
            )
        else:
            raise ValueError(f"Unsupported register size: {size}")

        self._check_error(
            dxl_id, address, comm_result, dxl_error, "READ"
        )

        return to_signed(value, size) if signed else value

    def write_register_txonly(self, dxl_id, address, size, value):
        raw = to_unsigned(value, size)

        if size == 1:
            comm_result = self.packet.write1ByteTxOnly(
                self.port, dxl_id, address, raw
            )
        elif size == 2:
            comm_result = self.packet.write2ByteTxOnly(
                self.port, dxl_id, address, raw
            )
        elif size == 4:
            comm_result = self.packet.write4ByteTxOnly(
                self.port, dxl_id, address, raw
            )
        else:
            raise ValueError(f"Unsupported register size: {size}")

        if comm_result != COMM_SUCCESS:
            raise RuntimeError(
                f"WRITE ID={dxl_id} Address={address}: "
                f"{self.packet.getTxRxResult(comm_result)}"
            )

    def write_and_verify(self, dxl_id, item, value=None):
        name = item["name"]
        address = int(item["address"])
        size = int(item["size"])
        signed = bool(item.get("signed", False))
        expected = item["value"] if value is None else value

        self.write_register_txonly(dxl_id, address, size, expected)
        time.sleep(WRITE_VERIFY_DELAY)

        actual = self.read_register(dxl_id, address, size, signed=signed)
        if actual != expected:
            raise RuntimeError(
                f"VERIFY FAILED ID={dxl_id} {name}({address}): "
                f"expected={expected}, actual={actual}"
            )
        return actual

    def ping(self, dxl_id):
        model, comm_result, dxl_error = self.packet.ping(self.port, dxl_id)
        self._check_error(dxl_id, 0, comm_result, dxl_error, "PING")
        return model

    def broadcast_scan(self, quiet=False):
        devices, comm_result = self.packet.broadcastPing(self.port)
        if comm_result != COMM_SUCCESS:
            # A broadcast ping with no devices can result in an RX timeout
            # depending on SDK/adapter state. Treat it as empty here.
            if not quiet:
                print(self.packet.getTxRxResult(comm_result))
            return {}
        return devices


# =============================================================================
# Display / scan
# =============================================================================

def print_scan(devices, baudrate):
    print(f"\nDYNAMIXEL scan @ {baudrate:,} bps")
    print("-" * 72)

    if not devices:
        print("No DYNAMIXEL detected.")
        return

    print(f"{'ID':>4}  {'MODEL':>7}  {'NAME':<16} {'FW':>4}  {'SUPPORTED'}")
    print("-" * 72)

    for dxl_id in sorted(devices):
        info = devices[dxl_id]
        model = int(info[0])
        fw = int(info[1])
        supported = "YES" if model in SUPPORTED_MODELS else "NO"
        print(
            f"{dxl_id:4d}  {model:7d}  {model_name(model):<16} "
            f"{fw:4d}  {supported}"
        )


def scan_or_raise(bus):
    devices = bus.broadcast_scan()
    print_scan(devices, bus.baudrate)
    if not devices:
        raise RuntimeError(
            f"No DYNAMIXEL detected on {bus.device} @ {bus.baudrate} bps"
        )
    return devices


# =============================================================================
# Backup
# =============================================================================

def read_item(bus, dxl_id, item_tuple):
    name, address, size, signed, access, area, category = item_tuple
    value = bus.read_register(dxl_id, address, size, signed=signed)

    return {
        "name": name,
        "address": address,
        "size": size,
        "area": area,
        "access": access,
        "signed": signed,
        "category": category,
        "value": value,
        "raw_unsigned": to_unsigned(value, size),
        "hex": hex_value(value, size),
    }


def read_servo_full(bus, dxl_id, model_number, firmware_version):
    name = model_name(model_number)

    print("\n" + "=" * 88)
    print(
        f"READING ID {dxl_id}  {name}  "
        f"Model={model_number}  Firmware={firmware_version}"
    )
    print("=" * 88)

    items = {}
    errors = []

    print(
        f"{'ADDR':>4}  {'ITEM':<28} {'DECIMAL':>12} "
        f"{'HEX':>12} {'ACC':>3}"
    )
    print("-" * 88)

    for item_tuple in get_full_control_table(firmware_version):
        name_item = item_tuple[0]
        address = item_tuple[1]

        try:
            data = read_item(bus, dxl_id, item_tuple)
            items[name_item] = data
            print(
                f"{data['address']:4d}  "
                f"{data['name']:<28} "
                f"{str(data['value']):>12} "
                f"{data['hex']:>12} "
                f"{data['access']:>3}"
            )
        except Exception as exc:
            errors.append({
                "name": name_item,
                "address": address,
                "error": str(exc),
            })
            print(
                f"{address:4d}  {name_item:<28} "
                f"READ ERROR: {exc}"
            )

    return {
        "id": dxl_id,
        "model_name": name,
        "model_number": model_number,
        "firmware_version": firmware_version,
        "indirect_count": 28 if firmware_version >= 53 else 20,
        "complete": len(errors) == 0,
        "items": items,
        "errors": errors,
    }


def choose_output_path():
    default_name = (
        "DYNAMIXEL_XL330_BACKUP_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )

    text = input(
        f"\nOutput JSON path (Enter = ./{default_name}): "
    ).strip().strip('"')

    if not text:
        return Path.cwd() / default_name

    path = Path(text).expanduser()
    if path.is_dir():
        return path / default_name

    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")

    return path


def export_backup(bus):
    devices = scan_or_raise(bus)

    supported = [
        dxl_id
        for dxl_id, info in sorted(devices.items())
        if int(info[0]) in SUPPORTED_MODELS
    ]

    if not supported:
        print("\nNo supported XL330-M077 / XL330-M288 found.")
        return

    backup = {
        "format": "dynamixel-xl330-backup",
        "format_version": 3,
        "created_at": datetime.now().isoformat(),
        "connection": {
            "port": bus.device,
            "baudrate": bus.baudrate,
            "protocol": PROTOCOL_VERSION,
        },
        "supported_models": [
            {"name": name, "model_number": number}
            for number, name in sorted(SUPPORTED_MODELS.items())
        ],
        "servos": [],
        "unsupported_devices": [],
    }

    for dxl_id, info in sorted(devices.items()):
        model_number = int(info[0])
        firmware_version = int(info[1])

        if model_number not in SUPPORTED_MODELS:
            backup["unsupported_devices"].append({
                "id": dxl_id,
                "model_number": model_number,
                "firmware_version": firmware_version,
            })
            print(
                f"\nSKIP ID {dxl_id}: unsupported model {model_number}"
            )
            continue

        servo = read_servo_full(
            bus, dxl_id, model_number, firmware_version
        )
        backup["servos"].append(servo)

    output_path = choose_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            backup,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + "=" * 88)
    print(f"BACKUP SAVED: {output_path}")

    complete = all(s.get("complete", False) for s in backup["servos"])
    if complete:
        print("All supported servos were read successfully.")
    else:
        print("WARNING: Some registers could not be read. Check errors in JSON.")

    print("=" * 88)


# =============================================================================
# Backup loading / mapping
# =============================================================================

def list_json_files():
    files = sorted(
        Path.cwd().glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files


def choose_backup_path():
    while True:
        candidates = list_json_files()

        print("\nJSON files in current directory:")
        if candidates:
            for i, path in enumerate(candidates[:20], start=1):
                print(f"  {i}. {path.name}")
        else:
            print("  (none)")

        print("  M. Enter path manually")
        print("  Q. Cancel")

        choice = input("\nSelect backup JSON: ").strip()

        if choice.lower() == "q":
            return None

        if choice.lower() == "m":
            text = input("Enter JSON path: ").strip().strip('"')
            if not text:
                continue
            path = Path(text).expanduser()
        else:
            try:
                index = int(choice)
            except ValueError:
                print("Invalid selection.")
                continue

            if not (1 <= index <= min(len(candidates), 20)):
                print("Invalid selection.")
                continue

            path = candidates[index - 1]

        if not path.exists():
            print(f"File not found: {path}")
            continue

        return path


def load_backup(path):
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "servos" not in data or not isinstance(data["servos"], list):
        raise ValueError("Invalid backup JSON: missing 'servos' list")

    # Compatible with previous v2 single-model file and this v3 file.
    fmt = data.get("format", "")
    if fmt not in (
        "dynamixel-xl330-backup",
        "xl330-m288-full-backup",
    ):
        print(
            f"WARNING: Unknown backup format '{fmt}'. "
            "Will validate individual profiles."
        )

    profiles = {}
    for profile in data["servos"]:
        backup_id = int(profile["id"])
        model_number = int(profile["model_number"])
        if model_number not in SUPPORTED_MODELS:
            continue
        profiles[backup_id] = profile

    if not profiles:
        raise ValueError(
            "Backup contains no supported XL330-M077 / XL330-M288 profiles"
        )

    return data, profiles


def print_backup_profiles(profiles):
    print("\nBackup profiles")
    print("-" * 72)
    print(f"{'ID':>4}  {'MODEL':>7}  {'NAME':<16} {'FW':>4} {'COMPLETE'}")
    print("-" * 72)

    for backup_id, profile in sorted(profiles.items()):
        model = int(profile["model_number"])
        fw = int(profile.get("firmware_version", -1))
        complete = "YES" if profile.get("complete", True) else "NO"
        print(
            f"{backup_id:4d}  {model:7d}  {model_name(model):<16} "
            f"{fw:4d} {complete}"
        )


def parse_mapping(text):
    """
    Input:
        1:10,2:11,3:12
    Meaning:
        current ID 1  <- backup profile ID 10
        current ID 2  <- backup profile ID 11
    """
    mapping = {}

    for part in text.split(","):
        part = part.strip()
        if not part:
            continue

        if ":" not in part:
            raise ValueError(
                f"Bad mapping '{part}', expected currentID:backupID"
            )

        current_text, backup_text = part.split(":", 1)
        current_id = int(current_text.strip())
        backup_id = int(backup_text.strip())

        if not (0 <= current_id <= 252):
            raise ValueError(f"Invalid current ID {current_id}")
        if not (0 <= backup_id <= 252):
            raise ValueError(f"Invalid backup ID {backup_id}")

        if current_id in mapping:
            raise ValueError(f"Duplicate current ID {current_id}")

        mapping[current_id] = backup_id

    if not mapping:
        raise ValueError("Empty mapping")

    if len(set(mapping.values())) != len(mapping):
        raise ValueError("One backup profile cannot be mapped to two servos")

    return mapping


def choose_restore_mapping(devices, profiles):
    while True:
        print("\nRestore mapping mode:")
        print("  1. Same ID (current ID == backup ID)")
        print("  2. Manual mapping, e.g. 1:10,2:11,3:12")
        print("  3. Restore one servo")
        print("  Q. Cancel")

        choice = input("\nSelect mode: ").strip().lower()

        if choice == "q":
            return None

        if choice == "1":
            mapping = {}
            for current_id, info in devices.items():
                if current_id not in profiles:
                    continue
                current_model = int(info[0])
                backup_model = int(profiles[current_id]["model_number"])
                if current_model == backup_model:
                    mapping[current_id] = current_id

            if not mapping:
                print("No same-ID/model matches between bus and backup.")
                continue

            return mapping

        if choice == "2":
            text = input(
                "Enter mapping currentID:backupID separated by commas: "
            ).strip()
            try:
                return parse_mapping(text)
            except Exception as exc:
                print(f"Invalid mapping: {exc}")
                continue

        if choice == "3":
            try:
                current_id = int(input("Current servo ID: ").strip())
                backup_id = int(input("Backup profile ID to restore: ").strip())
                return {current_id: backup_id}
            except ValueError:
                print("ID must be an integer.")
                continue

        print("Invalid selection.")


def validate_mapping(devices, profiles, mapping):
    desired_ids = []
    mapping_current_ids = set(mapping.keys())

    for current_id, backup_id in mapping.items():
        if current_id not in devices:
            raise RuntimeError(
                f"Current ID {current_id} is not detected at the selected baud."
            )

        if backup_id not in profiles:
            raise RuntimeError(
                f"Backup profile ID {backup_id} does not exist."
            )

        current_model = int(devices[current_id][0])
        backup_model = int(profiles[backup_id]["model_number"])

        if current_model != backup_model:
            raise RuntimeError(
                f"MODEL MISMATCH: current ID {current_id} is "
                f"{model_name(current_model)}({current_model}), but backup ID "
                f"{backup_id} is {model_name(backup_model)}({backup_model})."
            )

        desired_id = int(item_value(profiles[backup_id], "ID", backup_id))
        desired_ids.append(desired_id)

        # Block ID collisions. Even if the occupying ID is another mapped servo,
        # automatic cyclic renumbering is intentionally not attempted.
        if desired_id in devices and desired_id != current_id:
            raise RuntimeError(
                f"Target ID {desired_id} is already occupied on the bus. "
                "For safety, assign temporary unique IDs first, then retry."
            )

        protocol_type = item_value(profiles[backup_id], "Protocol Type", 2)
        if protocol_type != 2:
            raise RuntimeError(
                f"Backup ID {backup_id} has Protocol Type={protocol_type}. "
                "This tool only restores Protocol 2.0."
            )

    if len(set(desired_ids)) != len(desired_ids):
        raise RuntimeError("Two selected profiles would end with the same ID.")


# =============================================================================
# Restore helpers
# =============================================================================

def profile_restore_items(profile):
    """
    Return items that are safe/meaningful to restore BEFORE ID/Baud changes.

    Excludes:
      - read-only data
      - runtime status
      - runtime commands (Goal Position/Velocity/Current/PWM, LED, Torque)
      - ID and Baud Rate (deferred)
      - Status Return Level (deferred until after final verification)
      - Indirect Data (aliases RAM and can trigger commands)
    """
    items = []

    for name, item in profile.get("items", {}).items():
        if item.get("access") != "RW":
            continue

        category = item.get("category")

        if category == "configuration":
            if name in ("ID", "Baud Rate"):
                continue
            items.append(item)

        elif category == "ram_configuration":
            if name == "Status Return Level":
                continue
            items.append(item)

        elif category == "indirect_address":
            items.append(item)

    # Explicit ordering:
    # Operating Mode first because changing it resets gains/profile.
    def sort_key(item):
        name = item["name"]
        address = int(item["address"])

        if name == "Operating Mode":
            return (0, address)

        # Other EEPROM configuration.
        if item.get("area") == "EEPROM":
            return (1, address)

        # Gains / RAM configuration.
        if item.get("category") == "ram_configuration":
            return (2, address)

        # Indirect Address after normal RAM config.
        if item.get("category") == "indirect_address":
            return (3, address)

        return (9, address)

    return sorted(items, key=sort_key)


def profile_verification_items(profile):
    """
    Final readback set, before restoring Status Return Level.
    Includes ID/Baud and all safe restored settings.
    """
    items = profile_restore_items(profile)

    for special_name in ("ID", "Baud Rate"):
        item = item_by_name(profile, special_name)
        if item:
            items.append(item)

    # deduplicate by address/name
    dedup = {}
    for item in items:
        dedup[(int(item["address"]), item["name"])] = item

    return sorted(
        dedup.values(),
        key=lambda item: int(item["address"]),
    )


def prepare_servo_for_restore(bus, current_id):
    """
    Put servo into a predictable communication state:
      - Torque OFF (EEPROM must only be written with torque disabled)
      - Status Return Level = 2 temporarily, so readback verification works
    """
    # TxOnly so this also works if current Status Return Level is 0/1.
    bus.write_register_txonly(
        current_id, ADDR_TORQUE_ENABLE, 1, 0
    )
    time.sleep(WRITE_VERIFY_DELAY)

    bus.write_register_txonly(
        current_id, ADDR_STATUS_RETURN_LEVEL, 1, 2
    )
    time.sleep(WRITE_VERIFY_DELAY)

    # Confirm communication. Ping always returns a status packet.
    model = bus.ping(current_id)

    # Now Status Return Level should allow reads.
    try:
        torque = bus.read_register(
            current_id, ADDR_TORQUE_ENABLE, 1, signed=False
        )
        if torque != 0:
            raise RuntimeError(
                f"ID {current_id}: Torque Enable is still {torque}"
            )

        srl = bus.read_register(
            current_id, ADDR_STATUS_RETURN_LEVEL, 1, signed=False
        )
        if srl != 2:
            raise RuntimeError(
                f"ID {current_id}: cannot set temporary Status Return Level=2"
            )
    except Exception as exc:
        raise RuntimeError(
            f"ID {current_id}: failed to prepare servo for restore: {exc}"
        ) from exc

    return model


def restore_profile_on_current_bus(bus, current_id, profile):
    backup_id = int(profile["id"])
    expected_model = int(profile["model_number"])

    print("\n" + "=" * 88)
    print(
        f"RESTORE current ID {current_id} <- backup ID {backup_id} "
        f"{model_name(expected_model)}"
    )
    print("=" * 88)

    detected_model = prepare_servo_for_restore(bus, current_id)

    if detected_model != expected_model:
        raise RuntimeError(
            f"ID {current_id}: model changed/mismatch during restore. "
            f"Detected {detected_model}, expected {expected_model}"
        )

    items = profile_restore_items(profile)

    # If current firmware cannot support all indirect items in backup, skip
    # unsupported indirect address numbers.
    current_fw = bus.read_register(current_id, 6, 1, signed=False)
    current_indirect_count = 28 if current_fw >= 53 else 20

    for item in items:
        name = item["name"]

        if item.get("category") == "indirect_address":
            try:
                number = int(name.rsplit(" ", 1)[1])
            except Exception:
                number = 999

            if number > current_indirect_count:
                print(
                    f"[SKIP] ID {current_id} {name}: current firmware "
                    f"V{current_fw} supports only {current_indirect_count} "
                    "Indirect Address entries."
                )
                continue

        expected = item["value"]

        print(
            f"[WRITE] ID {current_id:3d} "
            f"{name:<28} = {expected}"
        )
        bus.write_and_verify(current_id, item)

    return current_fw


def change_id_and_verify(bus, old_id, new_id, expected_model):
    if old_id == new_id:
        return old_id

    print(f"[ID] {old_id} -> {new_id}")

    # TxOnly avoids ambiguity about which ID is used in the status packet
    # immediately after the ID register changes.
    bus.write_register_txonly(old_id, ADDR_ID, 1, new_id)
    time.sleep(0.03)

    model = bus.ping(new_id)
    if model != expected_model:
        raise RuntimeError(
            f"After ID change, ID {new_id} model={model}, "
            f"expected={expected_model}"
        )

    return new_id


def change_baud_txonly(bus, dxl_id, baud_code):
    if baud_code not in BAUD_CODE_TO_BPS:
        raise RuntimeError(
            f"Unsupported XL330 Baud Rate code: {baud_code}"
        )

    target_bps = BAUD_CODE_TO_BPS[baud_code]

    if target_bps == bus.baudrate:
        return target_bps

    print(
        f"[BAUD] ID {dxl_id}: "
        f"{bus.baudrate:,} -> {target_bps:,} bps"
    )

    # Servo switches communication speed immediately. Do not wait for a
    # status packet at the old baud.
    bus.write_register_txonly(
        dxl_id, ADDR_BAUD_RATE, 1, baud_code
    )
    time.sleep(0.03)

    return target_bps


def verify_profile(bus, target_id, profile, current_firmware):
    expected_model = int(profile["model_number"])
    model = bus.ping(target_id)

    if model != expected_model:
        return [
            f"Model Number expected {expected_model}, detected {model}"
        ]

    mismatches = []
    current_indirect_count = 28 if current_firmware >= 53 else 20

    for item in profile_verification_items(profile):
        name = item["name"]

        if item.get("category") == "indirect_address":
            try:
                number = int(name.rsplit(" ", 1)[1])
            except Exception:
                number = 999
            if number > current_indirect_count:
                continue

        address = int(item["address"])
        size = int(item["size"])
        signed = bool(item.get("signed", False))
        expected = item["value"]

        try:
            actual = bus.read_register(
                target_id, address, size, signed=signed
            )
        except Exception as exc:
            mismatches.append(
                f"{name}({address}) read failed: {exc}"
            )
            continue

        if actual != expected:
            mismatches.append(
                f"{name}({address}) expected={expected}, actual={actual}"
            )

    # Torque must intentionally stay OFF.
    try:
        torque = bus.read_register(
            target_id, ADDR_TORQUE_ENABLE, 1, signed=False
        )
        if torque != 0:
            mismatches.append(
                f"Torque Enable(64) expected safety value 0, actual={torque}"
            )
    except Exception as exc:
        mismatches.append(f"Torque Enable(64) read failed: {exc}")

    return mismatches


def restore_status_return_level(bus, target_id, profile):
    item = item_by_name(profile, "Status Return Level")
    if item is None:
        return True, "not present in backup"

    target = int(item["value"])

    print(
        f"[WRITE-LAST] ID {target_id:3d} "
        f"Status Return Level = {target}"
    )

    bus.write_register_txonly(
        target_id,
        ADDR_STATUS_RETURN_LEVEL,
        1,
        target,
    )
    time.sleep(WRITE_VERIFY_DELAY)

    if target >= 1:
        try:
            actual = bus.read_register(
                target_id,
                ADDR_STATUS_RETURN_LEVEL,
                1,
                signed=False,
            )
            if actual != target:
                return False, f"expected={target}, actual={actual}"
            return True, f"verified={actual}"
        except Exception as exc:
            return False, str(exc)

    # Status Return Level 0 intentionally prevents normal read status packets.
    # Ping still returns, so confirm the servo is alive.
    try:
        bus.ping(target_id)
        return True, "set to 0; ping verified (readback unavailable by design)"
    except Exception as exc:
        return False, f"set to 0 but ping failed: {exc}"


def restore_from_backup(bus):
    path = choose_backup_path()
    if path is None:
        return

    data, profiles = load_backup(path)
    print(f"\nLoaded backup: {path}")
    print_backup_profiles(profiles)

    devices = scan_or_raise(bus)
    mapping = choose_restore_mapping(devices, profiles)
    if mapping is None:
        return

    validate_mapping(devices, profiles, mapping)

    print("\nRestore plan")
    print("-" * 88)
    print(
        f"{'CURRENT':>7} -> {'BACKUP':>6} -> {'FINAL':>5}  "
        f"{'MODEL':<16} {'TARGET BAUD':>12}"
    )
    print("-" * 88)

    for current_id, backup_id in mapping.items():
        profile = profiles[backup_id]
        final_id = int(item_value(profile, "ID", backup_id))
        baud_code = int(item_value(profile, "Baud Rate", 3))
        target_baud = BAUD_CODE_TO_BPS.get(baud_code, -1)

        print(
            f"{current_id:7d} -> {backup_id:6d} -> {final_id:5d}  "
            f"{model_name(int(profile['model_number'])):<16} "
            f"{target_baud:12,d}"
        )

    print("\nRestore policy:")
    print("  - Torque will be forced OFF and left OFF.")
    print("  - EEPROM configuration will be restored.")
    print("  - PID/PI gains, profile settings, watchdog and Indirect Address will be restored.")
    print("  - Read-only runtime status will NOT be written.")
    print("  - Goal Position/Velocity/Current/PWM and Indirect Data will NOT be written.")
    print("  - Every setting is read back; a final full verification is performed.")

    confirm = input(
        "\nType RESTORE to start writing, anything else cancels: "
    ).strip()

    if confirm != "RESTORE":
        print("Restore cancelled.")
        return

    initial_host_baud = bus.baudrate

    # State for each mapping.
    states = []

    try:
        # ---------------------------------------------------------------------
        # Phase 1: all safe settings while every selected device is still on
        # the currently selected bus baud.
        # ---------------------------------------------------------------------
        print("\nPHASE 1/5 - Restore configuration at current bus baud")

        for current_id, backup_id in mapping.items():
            profile = profiles[backup_id]
            current_fw = restore_profile_on_current_bus(
                bus, current_id, profile
            )

            states.append({
                "original_id": current_id,
                "current_id": current_id,
                "backup_id": backup_id,
                "profile": profile,
                "current_firmware": current_fw,
                "expected_model": int(profile["model_number"]),
                "final_id": int(item_value(profile, "ID", backup_id)),
                "baud_code": int(item_value(profile, "Baud Rate", 3)),
                "target_baud": BAUD_CODE_TO_BPS[
                    int(item_value(profile, "Baud Rate", 3))
                ],
            })

        # ---------------------------------------------------------------------
        # Phase 2: change IDs, still at current baud.
        # ---------------------------------------------------------------------
        print("\nPHASE 2/5 - Set final IDs")

        for state in states:
            state["current_id"] = change_id_and_verify(
                bus,
                state["current_id"],
                state["final_id"],
                state["expected_model"],
            )

        # ---------------------------------------------------------------------
        # Phase 3: change servo baud rates as the final operation on the old bus.
        # ---------------------------------------------------------------------
        print("\nPHASE 3/5 - Set final baud rates")

        for state in states:
            change_baud_txonly(
                bus,
                state["current_id"],
                state["baud_code"],
            )

        # ---------------------------------------------------------------------
        # Phase 4: switch host to each target baud and perform final verification
        # before restoring Status Return Level.
        # ---------------------------------------------------------------------
        print("\nPHASE 4/5 - Final readback verification")

        all_ok = True
        verification_results = []

        target_bauds = sorted({state["target_baud"] for state in states})

        for target_baud in target_bauds:
            bus.set_baudrate(target_baud)
            print(f"\nVerify @ {target_baud:,} bps")

            for state in states:
                if state["target_baud"] != target_baud:
                    continue

                target_id = state["current_id"]
                profile = state["profile"]

                mismatches = verify_profile(
                    bus,
                    target_id,
                    profile,
                    state["current_firmware"],
                )

                if mismatches:
                    all_ok = False
                    print(
                        f"[FAIL] ID {target_id} "
                        f"{model_name(state['expected_model'])}"
                    )
                    for mismatch in mismatches:
                        print(f"       - {mismatch}")
                else:
                    print(
                        f"[OK]   ID {target_id} "
                        f"{model_name(state['expected_model'])}"
                    )

                verification_results.append(
                    (state, mismatches)
                )

        # ---------------------------------------------------------------------
        # Phase 5: restore Status Return Level LAST, then ping detection.
        # ---------------------------------------------------------------------
        print("\nPHASE 5/5 - Restore Status Return Level and final detection")

        for target_baud in target_bauds:
            bus.set_baudrate(target_baud)

            for state in states:
                if state["target_baud"] != target_baud:
                    continue

                ok, detail = restore_status_return_level(
                    bus,
                    state["current_id"],
                    state["profile"],
                )

                if not ok:
                    all_ok = False
                    print(
                        f"[FAIL] ID {state['current_id']} "
                        f"Status Return Level: {detail}"
                    )
                else:
                    print(
                        f"[OK]   ID {state['current_id']} "
                        f"Status Return Level: {detail}"
                    )

            # Final broadcast detection on each target baud.
            detected = bus.broadcast_scan(quiet=True)
            print_scan(detected, target_baud)

        print("\n" + "=" * 88)
        if all_ok:
            print("RESTORE + VERIFY SUCCESS")
            print("All selected servos passed final configuration verification.")
        else:
            print("RESTORE FINISHED WITH VERIFY ERRORS")
            print("Review [FAIL] lines above before using the servos.")

        print("Torque remains OFF on restored servos.")
        print("=" * 88)

    finally:
        # Return host adapter to the baud selected by the user so the main menu
        # state remains predictable. The servos themselves keep their restored baud.
        try:
            bus.set_baudrate(initial_host_baud)
        except Exception:
            pass


# =============================================================================
# Main menu
# =============================================================================

def print_header(device, baudrate):
    print("\n" + "=" * 88)
    print("DYNAMIXEL XL330 BACKUP / RESTORE")
    print("Supports: XL330-M288 (1200), XL330-M077 (1190), Protocol 2.0")
    print(f"Port: {device}")
    print(f"Host baud: {baudrate:,} bps")
    print("=" * 88)


def main():
    print("\nDYNAMIXEL XL330 Backup / Restore Tool")
    print("Windows / Ubuntu Linux / macOS")

    device = choose_serial_port()
    baudrate = choose_baudrate()

    bus = DxlBus(device, baudrate)

    try:
        bus.open()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        return 1

    try:
        while True:
            print_header(bus.device, bus.baudrate)

            # Initial scan each time the menu is shown.
            devices = bus.broadcast_scan(quiet=True)
            print_scan(devices, bus.baudrate)

            print("\nMenu:")
            print("  1. Scan bus again")
            print("  2. Export / backup ALL supported servos to JSON")
            print("  3. Restore / write parameters from JSON + final verification")
            print("  4. Change serial port / baud rate")
            print("  5. Exit")

            choice = input("\nSelect: ").strip()

            try:
                if choice == "1":
                    devices = bus.broadcast_scan()
                    print_scan(devices, bus.baudrate)
                    input("\nPress Enter to continue...")

                elif choice == "2":
                    export_backup(bus)
                    input("\nPress Enter to continue...")

                elif choice == "3":
                    restore_from_backup(bus)
                    input("\nPress Enter to continue...")

                elif choice == "4":
                    bus.close()
                    device = choose_serial_port()
                    baudrate = choose_baudrate()
                    bus = DxlBus(device, baudrate)
                    bus.open()

                elif choice == "5":
                    print("Bye.")
                    return 0

                else:
                    print("Invalid selection.")
                    time.sleep(0.5)

            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                input("Press Enter to continue...")

            except Exception as exc:
                print("\n" + "!" * 88)
                print(f"ERROR: {exc}")
                print("!" * 88)
                input("\nPress Enter to continue...")

    finally:
        bus.close()


if __name__ == "__main__":
    sys.exit(main())
