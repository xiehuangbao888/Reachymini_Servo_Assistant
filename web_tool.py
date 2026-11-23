#!/usr/bin/env python3
"""Local browser UI for the original XL330 tool. Never starts a hardware write itself."""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import webbrowser
from dynamixel_sdk import COMM_RX_TIMEOUT

import dynamixel_xl330_backup_restore as core

ROOT = Path(__file__).resolve().parent
SCAN_TIMEOUT = 8.0
DEFAULT_PROFILE_SOURCE = 'backup_all_20261120_153857_997605.json'


def isolated_scan(port, baud, cancel, timeout=SCAN_TIMEOUT, command=None):
    """Bound open/driver/SDK/close hangs without leaving a serial thread behind."""
    process = subprocess.Popen(
        command or [sys.executable, str(ROOT / 'serial_probe.py'), port, str(baud)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    deadline = time.monotonic() + timeout
    try:
        while True:
            if cancel.is_set():
                raise RuntimeError('扫描已取消，请重新选择 U2D2 串口。')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f'扫描超时（{timeout:g} 秒），已停止本次连接。请检查 U2D2 串口、供电和波特率后重试。')
            try:
                output, errors = process.communicate(timeout=min(0.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode:
            raise RuntimeError('扫描进程异常退出：' + errors.decode('utf-8', errors='replace')[-500:])
        result = json.loads(output)
        if result.get('error'):
            raise RuntimeError(result['error'])
        return result['devices']
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=1)


class WebBus(core.DxlBus):
    def open(self):
        super().open()
        self.port.ser.write_timeout = 1.0

    def ensure_id_free(self, sid):
        _, result, _ = self.packet.ping(self.port, sid)
        if result == core.COMM_SUCCESS:
            raise ValueError(f'新 ID {sid} 已被占用。')
        if result != COMM_RX_TIMEOUT:
            raise RuntimeError(f'无法确认 ID {sid} 是否空闲：{self.packet.getTxRxResult(result)}')


def normalize_backup(data):
    """Use trusted register definitions; JSON cannot turn a goal register into config."""
    if not isinstance(data, dict) or data.get('format') not in (
        'dynamixel-xl330-backup', 'xl330-m288-full-backup'
    ) or not isinstance(data.get('servos'), list) or not data['servos']:
        raise ValueError('参数文件格式无效，需使用原工具导出的 JSON。')
    profiles = {}
    for source in data['servos']:
        sid, model, fw = (source.get(k) for k in ('id', 'model_number', 'firmware_version'))
        if type(sid) is not int or not 0 <= sid <= 252 or sid in profiles:
            raise ValueError('参数文件包含无效或重复 ID。')
        if type(model) is not int or model not in core.SUPPORTED_MODELS:
            raise ValueError(f'ID {sid} 型号不受支持。')
        if type(fw) is not int or not 0 <= fw <= 255:
            raise ValueError(f'ID {sid} 固件版本无效。')
        if source.get('complete') is not True or source.get('errors'):
            raise ValueError(f'ID {sid} 档案不完整，请使用完整备份。')
        definitions = {x[0]: x for x in core.get_full_control_table(fw)}
        incoming = source.get('items')
        if not isinstance(incoming, dict):
            raise ValueError(f'ID {sid} 缺少寄存器。')
        items = {}
        for name, item in incoming.items():
            if name not in definitions or not isinstance(item, dict):
                raise ValueError(f'ID {sid} 存在未知寄存器 {name}。')
            n, addr, size, signed, access, area, category = definitions[name]
            expected = dict(name=n, address=addr, size=size, signed=signed,
                            access=access, area=area, category=category)
            if any(type(item.get(k)) is not type(v) or item[k] != v for k, v in expected.items()):
                raise ValueError(f'ID {sid} {name} 寄存器定义不匹配。')
            value = item.get('value')
            low = -(1 << (size * 8 - 1)) if signed else 0
            high = (1 << (size * 8 - (1 if signed else 0))) - 1
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'ID {sid} {name} 数值超出范围。')
            items[name] = dict(expected, value=value)
        required = {x[0] for x in definitions.values() if x[6] in (
            'configuration', 'ram_configuration', 'indirect_address')}
        if required - items.keys():
            raise ValueError(f'ID {sid} 缺少配置项：{", ".join(sorted(required - items.keys()))}')
        if items['ID']['value'] != sid or items['Protocol Type']['value'] != 2:
            raise ValueError(f'ID {sid} 的 ID / Protocol Type 不匹配。')
        if 'Model Number' in items and items['Model Number']['value'] != model:
            raise ValueError(f'ID {sid} Model Number 不匹配。')
        if items['Baud Rate']['value'] not in core.BAUD_CODE_TO_BPS:
            raise ValueError(f'ID {sid} 波特率代码无效。')
        profiles[sid] = dict(id=sid, model_number=model, firmware_version=fw,
                             complete=True, items=items, errors=[])
    return profiles


class DemoBus:
    """Memory-only adapter. No serial API is invoked in demo mode."""
    def __init__(self, device, baudrate, memory):
        self.device, self.baudrate, self.memory = device, baudrate, memory

    def open(self):
        pass

    def close(self):
        pass

    def broadcast_scan(self, quiet=False):
        return {sid: [p['model_number'], p['firmware_version']] for sid, p in self.memory.items()}

    def ping(self, sid):
        return self.memory[sid]['model_number']

    def ensure_id_free(self, sid):
        if sid in self.memory:
            raise ValueError(f'新 ID {sid} 已被占用。')

    def read_register(self, sid, address, size, signed=False):
        for item in self.memory[sid]['items'].values():
            if item['address'] == address and item['size'] == size:
                return item['value']
        raise RuntimeError(f'Unknown register {address}')

    def write_register_txonly(self, sid, address, size, value):
        for item in self.memory[sid]['items'].values():
            if item['address'] == address and item['size'] == size:
                if address == core.ADDR_ID:
                    self.ensure_id_free(value)
                    profile = self.memory.pop(sid)
                    profile['id'] = value
                    self.memory[value] = profile
                item['value'] = value
                return
        raise RuntimeError(f'Unknown register {address}')

    write_and_verify = core.DxlBus.write_and_verify


class Tool:
    def __init__(self, demo=False, output_dir=None, bus_factory=None):
        self.demo = demo
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.cancel_scan = threading.Event()
        self.use_isolated_scan = not demo and bus_factory is None
        self.output_dir = Path(output_dir or ROOT / 'artifacts' / ('demo' if demo else 'hardware'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        data = json.loads((ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text(encoding='utf-8-sig'))
        self.profiles = normalize_backup(data)
        self.profile_name = DEFAULT_PROFILE_SOURCE + '（内置默认）'
        self.connection = None
        self.devices = {}
        self.backup = None
        self.plan = None
        self.logs = []
        self.files = {}
        self.job = dict(status='idle', kind=None, message='等待连接串口')
        self.memory = {sid: copy.deepcopy(p) for sid, p in self.profiles.items() if sid in range(11, 17)}
        self.memory[15]['items']['Position P Gain']['value'] = 320
        self.bus_factory = bus_factory or (lambda port, baud: DemoBus(port, baud, self.memory)
                                          if demo else WebBus(port, baud))

    def log(self, *args, **kwargs):
        line = kwargs.get('sep', ' ').join(str(x) for x in args)
        with self.lock:
            for part in line.splitlines():
                if part.strip():
                    self.logs.append(dict(index=len(self.logs), time=datetime.now().strftime('%H:%M:%S'), text=part))

    def state(self):
        with self.lock:
            return copy.deepcopy(dict(demo=self.demo, token=self.token, connection=self.connection,
                devices=[dict(id=sid, model_number=v[0], model=core.model_name(v[0]), firmware=v[1],
                              supported=v[0] in core.SUPPORTED_MODELS) for sid, v in sorted(self.devices.items())],
                profiles=[dict(id=sid, model=core.model_name(p['model_number'])) for sid, p in self.profiles.items()],
                profile_name=self.profile_name, backup=self.backup, plan=self.plan, job=self.job))

    def start(self, kind, payload):
        with self.lock:
            if kind == 'cancel-scan':
                if self.job['status'] != 'running' or self.job['kind'] != 'scan':
                    raise ValueError('当前没有进行中的扫描。')
                self.cancel_scan.set()
                self.job['message'] = '正在取消扫描并释放串口…'
                return
            if self.job['status'] == 'running':
                raise ValueError('已有操作正在执行，请等待结束。')
            if kind not in ('scan', 'backup', 'profile', 'default_profile', 'plan', 'restore',
                            'id_plan', 'change_id', 'disconnect'):
                raise ValueError('未知操作。')
            self.cancel_scan.clear()
            self.job = dict(status='running', kind=kind, message=(
                f'正在连接并扫描，最多等待 {SCAN_TIMEOUT:g} 秒…' if kind == 'scan' else '操作进行中'))
            thread = threading.Thread(target=self.run, args=(kind, copy.deepcopy(payload)), daemon=True)
            thread.start()

    def run(self, kind, payload):
        completed_job = dict(status='error', kind=kind, message='操作未完成')
        try:
            self.log(f'[{kind.upper()}] 开始' + (' · 演示模式，无硬件写入' if self.demo else ''))
            message = getattr(self, 'do_' + kind)(payload)
            completed_job = dict(status='success', kind=kind, message=message)
            self.log('[OK]', message)
        except Exception as exc:
            self.log('[FAIL]', str(exc))
            self.plan = None
            completed_job = dict(status='error', kind=kind, message=str(exc))
        finally:
            try:
                with self.lock:
                    report = '\n'.join(f"{x['time']} {x['text']}" for x in self.logs)
                name = 'session_log.txt'
                (self.output_dir / name).write_text(report, encoding='utf-8')
                self.files[name] = self.output_dir / name
            except OSError as exc:
                self.log('[WARNING] 日志文件保存失败，请保留页面日志：', str(exc))
            with self.lock:
                self.job = completed_job

    def bus(self):
        if not self.connection:
            raise ValueError('请先连接并扫描舵机。')
        return self.bus_factory(self.connection['port'], self.connection['baudrate'])

    def checked_scan(self, bus):
        detected = bus.broadcast_scan()
        detected = {int(sid): [int(v[0]), int(v[1])] for sid, v in detected.items()}
        if not detected:
            raise ValueError('未发现舵机，请检查供电、U2D2 连接和波特率。')
        if detected != self.devices:
            self.backup = self.plan = None
            raise ValueError('总线上的 ID、型号或固件已变化，请重新扫描并备份。')
        return detected

    def do_scan(self, payload):
        self.backup = self.plan = None
        self.devices = {}
        self.connection = None
        port = payload.get('port')
        baud = payload.get('baudrate')
        if not isinstance(port, str) or not port or len(port) > 256 or type(baud) is not int or baud not in core.COMMON_BAUDRATES:
            raise ValueError('请选择有效串口和波特率。')
        if self.use_isolated_scan:
            detected = isolated_scan(port, baud, self.cancel_scan)
        else:
            bus = self.bus_factory(port, baud)
            try:
                bus.open()
                detected = bus.broadcast_scan()
            finally:
                bus.close()
        if self.cancel_scan.is_set():
            raise ValueError('扫描已取消，请重新选择 U2D2 串口。')
        if not detected:
            raise ValueError('未发现舵机，请检查供电、U2D2 连接和波特率。')
        self.devices = {int(k): [int(v[0]), int(v[1])] for k, v in detected.items()}
        self.connection = dict(port=port, baudrate=baud)
        for sid, info in sorted(self.devices.items()):
            self.log(f'ID {sid} · {core.model_name(info[0])} · Firmware V{info[1]}')
        return f'发现 {len(self.devices)} 台舵机，请核对型号和实际 ID。'

    def do_disconnect(self, payload):
        self.connection = self.backup = self.plan = None
        self.devices = {}
        return '已断开连接。'

    def save_json(self, name, data):
        path = self.output_dir / name
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)
        self.files[name] = path
        return '/files/' + name

    def do_backup(self, payload):
        self.backup = self.plan = None
        bus = self.bus()
        try:
            bus.open()
            detected = self.checked_scan(bus)
            result = dict(format='dynamixel-xl330-backup', format_version=3,
                created_at=datetime.now().isoformat(), connection=dict(self.connection, protocol=2.0),
                servos=[], unsupported_devices=[], demo=self.demo)
            for sid, (model, fw) in sorted(detected.items()):
                if model not in core.SUPPORTED_MODELS:
                    result['unsupported_devices'].append(dict(id=sid, model_number=model, firmware_version=fw))
                    continue
                result['servos'].append(core.read_servo_full(bus, sid, model, fw))
            self.checked_scan(bus)
            complete = bool(result['servos']) and all(p['complete'] for p in result['servos'])
            name = ('DEMO_' if self.demo else '') + 'backup_all_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json'
            url = self.save_json(name, result)
            self.backup = dict(name=name, url=url, complete=complete, count=len(result['servos']),
                               valid=complete, created_at=result['created_at'])
            if not complete:
                raise ValueError('备份有读取失败项；已保存诊断文件，但不能开始恢复。请下载备份并检查日志。')
            return f'已完整备份 {len(result["servos"])} 台支持的舵机。'
        finally:
            bus.close()

    def do_profile(self, payload):
        self.plan = None
        profiles = normalize_backup(payload.get('data'))
        if not self.demo and payload['data'].get('demo'):
            raise ValueError('演示备份不能用于真实硬件。')
        self.profiles = profiles
        self.profile_name = Path(str(payload.get('name', 'uploaded.json')).replace('\\', '/')).name[:150]
        return f'已载入 {len(profiles)} 台舵机参数档案。'

    def do_default_profile(self, payload):
        data = json.loads((ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text(encoding='utf-8-sig'))
        self.do_profile(dict(data=data, name=DEFAULT_PROFILE_SOURCE))
        self.profile_name = DEFAULT_PROFILE_SOURCE + '（内置默认）'
        return '已切回 2026-11-20 15:38 的默认恢复参数。'

    def require_backup(self):
        if not self.backup or not self.backup['complete'] or not self.backup.get('valid'):
            raise ValueError('写入前必须先完成当前连接的全量备份。')

    def check_id_target(self, old_id, new_id):
        if type(old_id) is not int or old_id not in self.devices:
            raise ValueError('请选择已扫描到的当前舵机 ID。')
        if self.devices[old_id][0] not in core.SUPPORTED_MODELS:
            raise ValueError('该舵机型号不支持修改 ID。')
        if type(new_id) is not int or not 0 <= new_id <= 252:
            raise ValueError('新 ID 必须是 0～252 的整数。')
        if old_id == new_id:
            raise ValueError('新 ID 不能与当前 ID 相同。')
        if new_id in self.devices:
            raise ValueError(f'新 ID {new_id} 已被占用。')

    def do_id_plan(self, payload):
        self.plan = None
        self.require_backup()
        old_id, new_id = payload.get('old_id'), payload.get('new_id')
        self.check_id_target(old_id, new_id)
        bus = self.bus()
        try:
            bus.open()
            self.checked_scan(bus)
            bus.ensure_id_free(new_id)
            if bus.read_register(old_id, core.ADDR_ID, 1) != old_id:
                raise RuntimeError('当前 ID 回读不一致，请检查连接。')
            # A successful read is required before any torque or ID write.
            bus.read_register(old_id, core.ADDR_TORQUE_ENABLE, 1)
            model, fw = self.devices[old_id]
            self.plan = dict(kind='id', id=secrets.token_urlsafe(24), current_id=old_id,
                             new_id=new_id, model=core.model_name(model), firmware=fw)
            return f'修改 ID 计划：{old_id} → {new_id}，请核对后确认。'
        finally:
            bus.close()

    def do_change_id(self, payload):
        self.require_backup()
        if not self.plan or self.plan.get('kind') != 'id' or payload.get('plan_id') != self.plan['id']:
            raise ValueError('请先生成并核对最新的修改 ID 计划。')
        plan = copy.deepcopy(self.plan)
        old_id, new_id = plan['current_id'], plan['new_id']
        if payload.get('confirm') != f'CHANGE {old_id} TO {new_id}':
            raise ValueError('请在最新修改计划弹窗中点击“确定修改”。')
        self.check_id_target(old_id, new_id)
        expected = copy.deepcopy(self.devices)
        expected[new_id] = expected.pop(old_id)
        bus = self.bus()
        self.backup['valid'] = False
        self.plan = None
        id_write_started = False
        torque_write_started = False
        try:
            bus.open()
            self.checked_scan(bus)
            bus.ensure_id_free(new_id)
            if bus.read_register(old_id, core.ADDR_ID, 1) != old_id:
                raise RuntimeError('当前 ID 回读不一致，未修改 ID。')
            torque_write_started = True
            bus.write_register_txonly(old_id, core.ADDR_TORQUE_ENABLE, 1, 0)
            time.sleep(core.WRITE_VERIFY_DELAY)
            if bus.read_register(old_id, core.ADDR_TORQUE_ENABLE, 1) != 0:
                raise RuntimeError('Torque 未关闭，未修改 ID。')
            id_write_started = True
            core.change_id_and_verify(bus, old_id, new_id, expected[new_id][0])
            if bus.read_register(new_id, core.ADDR_ID, 1) != new_id:
                raise RuntimeError('新 ID 回读校验失败。')
            if bus.read_register(new_id, core.ADDR_TORQUE_ENABLE, 1) != 0:
                raise RuntimeError('新 ID 的 Torque OFF 校验失败。')
            detected = {int(k): [int(v[0]), int(v[1])] for k, v in bus.broadcast_scan().items()}
            if detected != expected:
                raise RuntimeError('修改后的总线列表与计划不一致。')
            self.devices = detected
            self.log(f'[OK] ID {old_id} → {new_id}，新 ID、型号及 Torque OFF 校验通过。')
            return f'ID CHANGE + VERIFY SUCCESS · {old_id} → {new_id}。Torque 保持关闭；再次写入前请重新备份。'
        except Exception:
            if id_write_started:
                self.log(f'[WARNING] ID 写入已尝试，实际 ID 可能为 {old_id} 或 {new_id}；请重新扫描确认，不自动回滚。')
            elif torque_write_started:
                self.log('[WARNING] 未写入 ID；Torque 关闭状态未完成确认，请托稳机构并检查连接。')
            self.devices = {}
            self.connection = None
            raise
        finally:
            bus.close()

    def check_targets(self, ids):
        if not isinstance(ids, list) or not ids or any(type(sid) is not int for sid in ids) or len(ids) != len(set(ids)):
            raise ValueError('请选择至少一台舵机，ID 不得重复。')
        for sid in ids:
            if sid not in self.devices or sid not in self.profiles:
                raise ValueError(f'ID {sid} 未检测到或缺少同 ID 参数档案。')
            model, fw = self.devices[sid]
            p = self.profiles[sid]
            if model != p['model_number']:
                raise ValueError(f'MODEL MISMATCH: ID {sid} 当前 {core.model_name(model)}，档案 {core.model_name(p["model_number"])}')
            if (fw >= 53) != (p['firmware_version'] >= 53):
                raise ValueError(f'ID {sid} 固件的 Indirect Address 布局不兼容，禁止写入。')
            if core.BAUD_CODE_TO_BPS[core.item_value(p, 'Baud Rate')] != self.connection['baudrate']:
                raise ValueError(f'ID {sid} 档案波特率与当前总线不同。本网页保留 ID / 波特率，请使用匹配档案。')

    def plan_items(self, profile):
        return core.profile_restore_items(profile) + [profile['items']['Status Return Level']]

    def read_plan_rows(self, bus, ids):
        rows = []
        for sid in sorted(ids):
            p = self.profiles[sid]
            items = []
            for item in self.plan_items(p):
                current = bus.read_register(sid, item['address'], item['size'], signed=item['signed'])
                items.append(dict(name=item['name'], address=item['address'], before=current, after=item['value']))
            rows.append(dict(current_id=sid, backup_id=sid, final_id=sid,
                model=core.model_name(p['model_number']), baudrate=self.connection['baudrate'],
                firmware=self.devices[sid][1], items=items, changes=sum(x['before'] != x['after'] for x in items),
                write_count=len(items)))
        return rows

    def do_plan(self, payload):
        self.plan = None
        self.require_backup()
        ids = payload.get('ids')
        self.check_targets(ids)
        bus = self.bus()
        try:
            bus.open()
            self.checked_scan(bus)
            rows = self.read_plan_rows(bus, ids)
            self.plan = dict(kind='restore', id=secrets.token_urlsafe(24), rows=rows)
            return f'恢复计划已生成：仅写入选中的 {len(rows)} 台舵机，ID 和波特率保持一致。'
        finally:
            bus.close()

    def do_restore(self, payload):
        self.require_backup()
        if (payload.get('confirm') != 'RESTORE' or not self.plan or self.plan.get('kind') != 'restore'
                or payload.get('plan_id') != self.plan['id']):
            raise ValueError('请核对最新恢复计划并点击“确认恢复”。')
        plan = copy.deepcopy(self.plan)
        ids = [row['current_id'] for row in plan['rows']]
        self.check_targets(ids)
        bus = self.bus()
        touched = []
        # Consume authorization and snapshot even on failure; retry needs a new backup.
        self.backup['valid'] = False
        self.plan = None
        try:
            bus.open()
            self.checked_scan(bus)
            if self.read_plan_rows(bus, ids) != plan['rows']:
                raise ValueError('寄存器自生成计划后发生变化。尚未写入，请重新备份和生成计划。')
            # All selected motors must be torque-off before restoring the first one.
            for sid in ids:
                if bus.ping(sid) != self.profiles[sid]['model_number']:
                    raise ValueError(f'MODEL MISMATCH: ID {sid}')
            for sid in ids:
                touched.append(sid)
                core.prepare_servo_for_restore(bus, sid)
            for sid in ids:
                p = self.profiles[sid]
                fw = core.restore_profile_on_current_bus(bus, sid, p)
                mismatches = core.verify_profile(bus, sid, p, fw)
                if mismatches:
                    for failure in mismatches:
                        self.log(f'[FAIL] ID {sid}: {failure}')
                    raise RuntimeError(f'ID {sid} 最终回读校验失败，停止后续恢复。')
                ok, detail = core.restore_status_return_level(bus, sid, p)
                if not ok:
                    raise RuntimeError(f'ID {sid} Status Return Level 校验失败：{detail}')
                self.log(f'[OK] ID {sid} 配置完整校验通过；Torque OFF。{detail}')
            self.checked_scan(bus)
            return 'RESTORE + VERIFY SUCCESS' + (' · 演示结果' if self.demo else ' · 请断电再上电后测试')
        finally:
            # Best effort on error too; never hide inability to confirm torque-off.
            cleanup_errors = []
            for sid in touched:
                try:
                    bus.write_register_txonly(sid, core.ADDR_TORQUE_ENABLE, 1, 0)
                    time.sleep(core.WRITE_VERIFY_DELAY)
                    bus.ping(sid)
                    # SRL=0 intentionally prevents readback. Ping is all that remains.
                    srl = core.item_value(self.profiles[sid], 'Status Return Level')
                    if srl != 0 and bus.read_register(sid, core.ADDR_TORQUE_ENABLE, 1) != 0:
                        raise RuntimeError('Torque 未关闭')
                except Exception as exc:
                    self.log(f'[FAIL] ID {sid} Torque OFF 无法确认：{exc}；请断电检查。')
                    cleanup_errors.append(sid)
            bus.close()
            # Attempt every selected motor before reporting a cleanup failure.
            if cleanup_errors:
                raise RuntimeError(f'Torque OFF 无法确认：ID {cleanup_errors}，请断电检查。')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    @property
    def app(self):
        return self.server.app

    def send(self, status, content, mime='application/json; charset=utf-8', attachment=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
        if attachment:
            self.send_header('Content-Disposition', f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(content)

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, dict(error='仅允许本机访问。'))
        path = urlparse(self.path).path
        if path == '/api/state':
            return self.send(200, self.app.state())
        if path == '/api/ports':
            ports = [dict(device='DEMO', description='模拟 U2D2 · 不连接硬件')] if self.app.demo else [
                dict(device=p.device, description=p.description) for p in core.list_ports.comports()]
            return self.send(200, ports)
        if path == '/api/logs':
            with self.app.lock:
                return self.send(200, self.app.logs)
        if path.startswith('/files/'):
            name = path[len('/files/'):]
            file = self.app.files.get(name)
            if file and file.exists():
                return self.send(200, file.read_bytes(), 'application/octet-stream', name)
        static = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path in static:
            name, mime = static[path]
            return self.send(200, (ROOT / 'web' / name).read_bytes(), mime)
        self.send(404, dict(error='未找到文件。'))

    def do_POST(self):
        origin = self.headers.get('Origin')
        if not self.valid_host() or (origin and origin != 'http://' + self.headers.get('Host', '')):
            return self.send(403, dict(error='仅允许同源本机操作。'))
        if not secrets.compare_digest(self.headers.get('X-Tool-Token', ''), self.app.token):
            return self.send(403, dict(error='会话已变化，请刷新页面。'))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2_000_000 or self.headers.get_content_type() != 'application/json':
                raise ValueError('请求须为 JSON 且不能超过 2 MB。')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('请求格式无效。')
            path = urlparse(self.path).path
            if not path.startswith('/api/'):
                raise ValueError('未知操作。')
            self.app.start(path[len('/api/'):], payload)
            self.send(202, dict(ok=True))
        except (ValueError, TypeError) as exc:
            self.send(400, dict(error=str(exc)))


class LocalServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR permits two listeners on the same endpoint.
    # Exclusive binding prevents requests from reaching an older tool instance.
    allow_reuse_address = sys.platform != 'win32'

    def server_bind(self):
        if sys.platform == 'win32':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(port=8765, demo=False):
    server = LocalServer(('127.0.0.1', port), Handler)
    server.app = Tool(demo=demo)
    core.print = server.app.log
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='Use memory only, never connect hardware')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--lang', choices=('zh', 'en'), help='Browser interface language (otherwise use browser preference)')
    args = parser.parse_args()
    try:
        server = make_server(args.port, args.demo)
    except OSError as exc:
        parser.exit(1, f'无法启动本地服务：{exc}\n请关闭占用端口的旧服务，或使用 --port 8767 指定其他端口。\n')
    url = f'http://127.0.0.1:{server.server_port}/' + (f'?lang={args.lang}' if args.lang else '')
    print(f'XL330 Web Tool: {url}' + (' [DEMO / no hardware]' if args.demo else ''), flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if server.app.job['kind'] == 'scan':
            server.app.cancel_scan.set()
        # Do not interrupt an active restore worker halfway through a register write.
        print('\nWaiting for active operation to finish...', flush=True)
        while server.app.job['status'] == 'running':
            threading.Event().wait(0.2)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
