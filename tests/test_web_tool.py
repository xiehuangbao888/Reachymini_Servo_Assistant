import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import web_tool as web


class RecordingBus(web.DemoBus):
    def __init__(self, memory):
        super().__init__('DEMO', 1000000, memory)
        self.writes = []
        self.fail_write = None
        self.fail_read = None

    def write_register_txonly(self, sid, address, size, value):
        self.writes.append((sid, address, size, value))
        if (sid, address) == self.fail_write:
            raise RuntimeError('simulated write failure')
        return super().write_register_txonly(sid, address, size, value)

    def read_register(self, sid, address, size, signed=False):
        if (sid, address) == self.fail_read:
            raise RuntimeError('simulated read failure')
        return super().read_register(sid, address, size, signed)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tool = web.Tool(demo=True, output_dir=self.temp.name)
        self.bus = RecordingBus(self.tool.memory)
        self.tool.bus_factory = lambda port, baud: self.bus
        self.printer = patch.object(web.core, 'print', self.tool.log, create=True)
        self.delay = patch.object(web.core, 'WRITE_VERIFY_DELAY', 0)
        self.printer.start()
        self.delay.start()
        self.tool.do_scan(dict(port='DEMO', baudrate=1000000))

    def tearDown(self):
        self.printer.stop()
        self.delay.stop()
        self.temp.cleanup()

    def plan(self, ids=None):
        self.tool.do_backup({})
        self.tool.do_plan(dict(ids=ids or [15]))
        return dict(confirm='RESTORE', plan_id=self.tool.plan['id'])

    def test_full_backup_roundtrip_no_writes(self):
        self.tool.do_backup({})
        backup = json.loads(Path(self.temp.name, self.tool.backup['name']).read_text(encoding='utf-8'))
        self.assertEqual(len(backup['servos']), 6)
        self.assertTrue(all(s['complete'] for s in backup['servos']))
        self.assertEqual(len(web.normalize_backup(backup)), 6)
        self.assertEqual(self.bus.writes, [])

    def test_restore_only_selected_motor_and_never_goals(self):
        payload = self.plan()
        self.assertEqual(self.tool.plan['rows'][0]['changes'], 1)
        self.assertEqual(self.bus.writes, [])  # Plan is read-only.
        result = self.tool.do_restore(payload)
        self.assertIn('RESTORE + VERIFY SUCCESS', result)
        self.assertTrue(all(w[0] == 15 for w in self.bus.writes))
        forbidden = {7, 8, 65, 100, 102, 104, 116} | set(range(224, 252))
        self.assertFalse(any(w[1] in forbidden for w in self.bus.writes))
        self.assertFalse(any(w[1] == 64 and w[3] != 0 for w in self.bus.writes))
        self.assertEqual(self.bus.read_register(15, 84, 2), 300)
        self.assertEqual(self.bus.read_register(15, 64, 1), 0)
        self.assertFalse(self.tool.backup['valid'])
        self.assertTrue(Path(self.temp.name, self.tool.backup['name']).exists())
        self.assertIsNone(self.tool.plan)
        with self.assertRaises(ValueError):
            self.tool.do_restore(payload)

    def test_all_selected_torque_off_before_configuration(self):
        payload = self.plan([14, 15])
        self.tool.do_restore(payload)
        first_config = next(i for i, w in enumerate(self.bus.writes) if w[1] not in (64, 68))
        off_ids = {w[0] for w in self.bus.writes[:first_config] if w[1] == 64 and w[3] == 0}
        self.assertEqual(off_ids, {14, 15})

    def test_backup_required_and_confirm_required(self):
        with self.assertRaises(ValueError):
            self.tool.do_plan(dict(ids=[15]))
        payload = self.plan()
        with self.assertRaises(ValueError):
            self.tool.do_restore(dict(payload, confirm='restore'))
        with self.assertRaises(ValueError):
            self.tool.do_restore(dict(payload, plan_id='stale'))
        self.assertEqual(self.bus.writes, [])

    def test_changed_config_aborts_before_any_write(self):
        payload = self.plan()
        self.tool.memory[15]['items']['Position P Gain']['value'] = 401
        with self.assertRaisesRegex(ValueError, '发生变化'):
            self.tool.do_restore(payload)
        self.assertEqual(self.bus.writes, [])

    def test_inventory_change_invalidates_backup(self):
        payload = self.plan()
        del self.tool.memory[16]
        with self.assertRaisesRegex(ValueError, '已变化'):
            self.tool.do_restore(payload)
        self.assertEqual(self.bus.writes, [])
        self.assertIsNone(self.tool.backup)

    def test_partial_backup_saved_but_blocked(self):
        self.bus.fail_read = (15, 84)
        with self.assertRaisesRegex(ValueError, '备份有读取失败'):
            self.tool.do_backup({})
        self.assertFalse(self.tool.backup['complete'])
        self.assertTrue(Path(self.temp.name, self.tool.backup['name']).exists())
        with self.assertRaises(ValueError):
            self.tool.do_plan(dict(ids=[15]))
        self.assertEqual(self.bus.writes, [])

    def test_model_firmware_baud_and_missing_profile_blocked(self):
        self.tool.do_backup({})
        p = self.tool.profiles[15]
        original = copy.deepcopy(p)
        p['model_number'] = 1190
        with self.assertRaisesRegex(ValueError, 'MODEL MISMATCH'):
            self.tool.do_plan(dict(ids=[15]))
        self.tool.profiles[15] = p = copy.deepcopy(original)
        p['firmware_version'] = 52
        with self.assertRaisesRegex(ValueError, '布局不兼容'):
            self.tool.do_plan(dict(ids=[15]))
        self.tool.profiles[15] = p = copy.deepcopy(original)
        p['items']['Baud Rate']['value'] = 2
        with self.assertRaisesRegex(ValueError, '波特率'):
            self.tool.do_plan(dict(ids=[15]))
        with self.assertRaises(ValueError):
            self.tool.do_plan(dict(ids=[99]))
        with self.assertRaises(ValueError):
            self.tool.do_plan(dict(ids=[15, 15]))
        self.assertEqual(self.bus.writes, [])

    def test_write_failure_stops_and_torque_off_all_touched(self):
        payload = self.plan([14, 15])
        self.bus.fail_write = (14, 84)
        with self.assertRaisesRegex(RuntimeError, 'simulated write failure'):
            self.tool.do_restore(payload)
        for sid in (14, 15):
            self.assertEqual(self.bus.read_register(sid, 64, 1), 0)
        self.assertFalse(any(w[0] == 15 and w[1] not in (64, 68) for w in self.bus.writes))
        self.assertFalse(self.tool.backup['valid'])

    def test_final_mismatch_and_cleanup_failure_never_success(self):
        payload = self.plan()
        with patch.object(web.core, 'verify_profile', return_value=['mismatch']):
            self.tool.run('restore', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertTrue(any('[FAIL]' in x['text'] for x in self.tool.logs))
        payload = self.plan([14, 15])
        self.bus.fail_write = (14, 64)
        self.tool.run('restore', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertIn('Torque OFF', self.tool.job['message'])

    def test_cleanup_continues_to_other_selected_motor(self):
        payload = self.plan([14, 15])
        original = web.core.restore_status_return_level
        def trigger_cleanup_failure(bus, sid, profile):
            result = original(bus, sid, profile)
            if sid == 15:
                self.bus.fail_write = (14, 64)
            return result
        with patch.object(web.core, 'restore_status_return_level', trigger_cleanup_failure):
            self.tool.run('restore', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertEqual(self.bus.writes[-2:], [(14, 64, 1, 0), (15, 64, 1, 0)])

    def test_status_return_zero_uses_ping_and_stays_off(self):
        self.tool.profiles[15]['items']['Status Return Level']['value'] = 0
        payload = self.plan()
        self.assertIn('SUCCESS', self.tool.do_restore(payload))
        self.assertEqual(self.bus.read_register(15, 68, 1), 0)
        self.assertEqual(self.bus.read_register(15, 64, 1), 0)

    def test_demo_file_rejected_in_hardware_mode(self):
        data = json.loads((web.ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text(encoding='utf-8'))
        data['demo'] = True
        self.tool.demo = False
        with self.assertRaisesRegex(ValueError, '演示备份'):
            self.tool.do_profile(dict(name='demo.json', data=data))

    def test_rescan_disconnect_profile_change_expire_plan(self):
        self.plan()
        self.tool.do_scan(dict(port='DEMO', baudrate=1000000))
        self.assertIsNone(self.tool.backup)
        self.assertIsNone(self.tool.plan)
        self.plan()
        data = json.loads((web.ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text(encoding='utf-8'))
        self.tool.do_profile(dict(data=data, name='test.json'))
        self.assertIsNone(self.tool.plan)
        self.tool.do_disconnect({})
        self.assertIsNone(self.tool.backup)
        self.assertEqual(self.tool.devices, {})

    def id_plan(self, old_id=15, new_id=20):
        self.tool.do_backup({})
        self.tool.do_id_plan(dict(old_id=old_id, new_id=new_id))
        return dict(plan_id=self.tool.plan['id'], confirm=f'CHANGE {old_id} TO {new_id}')

    def test_id_change_readonly_plan_and_only_id_torque_written(self):
        payload = self.id_plan()
        self.assertEqual(self.bus.writes, [])
        before = copy.deepcopy(self.tool.memory[15]['items'])
        self.assertIn('SUCCESS', self.tool.do_change_id(payload))
        self.assertEqual(self.bus.writes, [(15, 64, 1, 0), (15, 7, 1, 20)])
        self.assertNotIn(15, self.tool.devices)
        self.assertEqual(self.tool.devices[20], [1200, 53])
        self.assertEqual(self.bus.read_register(20, 7, 1), 20)
        self.assertEqual(self.bus.read_register(20, 64, 1), 0)
        self.assertFalse(self.tool.backup['valid'])
        self.assertIsNone(self.tool.plan)
        for name, item in before.items():
            if name not in ('ID', 'Torque Enable'):
                self.assertEqual(item, self.tool.memory[20]['items'][name])
        self.assertIn(15, self.tool.profiles)
        self.assertNotIn(20, self.tool.profiles)
        with self.assertRaises(ValueError):
            self.tool.do_change_id(payload)
        self.tool.do_backup({})
        saved = json.loads(Path(self.temp.name, self.tool.backup['name']).read_text(encoding='utf-8'))
        self.assertIn(20, web.normalize_backup(saved))

    def test_id_change_backup_confirmation_and_plan_type(self):
        with self.assertRaises(ValueError):
            self.tool.do_id_plan(dict(old_id=15, new_id=20))
        payload = self.id_plan()
        for invalid in (dict(payload, confirm='CHANGE'), dict(payload, plan_id='stale')):
            with self.assertRaises(ValueError):
                self.tool.do_change_id(invalid)
        with self.assertRaises(ValueError):
            self.tool.do_restore(dict(payload, confirm='RESTORE'))
        payload = self.plan()
        with self.assertRaises(ValueError):
            self.tool.do_change_id(dict(payload, confirm='CHANGE 15 TO 20'))
        self.assertEqual(self.bus.writes, [])

    def test_invalid_or_occupied_ids_never_write(self):
        self.tool.do_backup({})
        for new_id in (-1, 253, 254, 255, True, 1.5, '20', None, 15, 16):
            with self.assertRaises(ValueError):
                self.tool.do_id_plan(dict(old_id=15, new_id=new_id))
        for old_id in (True, '15', 99):
            with self.assertRaises(ValueError):
                self.tool.do_id_plan(dict(old_id=old_id, new_id=20))
        self.assertEqual(self.bus.writes, [])

    def test_boundary_ids_and_change_back(self):
        self.tool.do_change_id(self.id_plan(new_id=0))
        self.tool.do_change_id(self.id_plan(old_id=0, new_id=252))
        self.tool.do_change_id(self.id_plan(old_id=252, new_id=15))
        self.assertEqual(self.bus.read_register(15, 7, 1), 15)

    def test_new_device_appearing_after_id_plan_aborts(self):
        payload = self.id_plan()
        self.tool.memory[20] = copy.deepcopy(self.tool.memory[15])
        with self.assertRaisesRegex(ValueError, '已变化'):
            self.tool.do_change_id(payload)
        self.assertEqual(self.bus.writes, [])

    def test_direct_ping_blocks_device_missed_by_scan(self):
        payload = self.id_plan()
        with patch.object(self.bus, 'ensure_id_free', side_effect=ValueError('新 ID 已被占用')):
            with self.assertRaisesRegex(ValueError, '占用'):
                self.tool.do_change_id(payload)
        self.assertEqual(self.bus.writes, [])

    def test_torque_failure_never_changes_id(self):
        payload = self.id_plan()
        self.bus.fail_read = (15, 64)
        self.tool.run('change_id', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertFalse(any(w[1] == 7 for w in self.bus.writes))
        self.assertIsNone(self.tool.connection)
        self.assertFalse(self.tool.backup['valid'])

    def test_id_write_failure_requires_rescan(self):
        payload = self.id_plan()
        self.bus.fail_write = (15, 7)
        self.tool.run('change_id', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertEqual(self.bus.read_register(15, 64, 1), 0)
        self.assertIsNone(self.tool.connection)
        self.assertFalse(self.tool.backup['valid'])
        self.assertTrue(any('不自动回滚' in x['text'] for x in self.tool.logs))

    def test_new_id_verification_failure_does_not_rollback(self):
        payload = self.id_plan()
        self.bus.fail_read = (20, 7)
        self.tool.run('change_id', payload)
        self.assertEqual(self.tool.job['status'], 'error')
        self.assertEqual(self.bus.writes, [(15, 64, 1, 0), (15, 7, 1, 20)])
        self.assertEqual(self.bus.read_register(20, 64, 1), 0)
        self.assertIsNone(self.tool.connection)
        self.assertEqual(self.tool.devices, {})

    def test_reset_default_profile_invalidates_id_plan(self):
        self.id_plan()
        self.tool.profiles[15]['items']['Position P Gain']['value'] = 999
        self.tool.do_default_profile({})
        self.assertIsNone(self.tool.plan)
        self.assertEqual(self.tool.profiles[15]['items']['Position P Gain']['value'], 300)
        self.assertIn('153857', self.tool.profile_name)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((web.ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text(encoding='utf-8'))

    def test_original_nine_profiles_compatible(self):
        self.assertEqual(set(web.normalize_backup(self.data)), set(range(10, 19)))

    def test_default_is_selected_1538_backup(self):
        self.assertEqual(self.data['created_at'], '2026-11-20T15:38:56.439123')
        for servo in self.data['servos']:
            self.assertEqual(servo['firmware_version'], 53)
            self.assertEqual(servo['items']['Position P Gain']['value'], 300 if 11 <= servo['id'] <= 16 else 200)
            self.assertEqual(servo['items']['Position D Gain']['value'], 0)

    def test_real_ping_only_timeout_means_free(self):
        bus = object.__new__(web.WebBus)
        bus.packet, bus.port = Mock(), Mock()
        bus.packet.ping.return_value = (0, web.COMM_RX_TIMEOUT, 0)
        bus.ensure_id_free(20)
        bus.packet.ping.return_value = (1200, web.core.COMM_SUCCESS, 0)
        with self.assertRaisesRegex(ValueError, '占用'):
            bus.ensure_id_free(20)
        bus.packet.ping.return_value = (0, -999, 0)
        with self.assertRaisesRegex(RuntimeError, '无法确认'):
            bus.ensure_id_free(20)

    def test_metadata_cannot_reclassify_runtime_command(self):
        self.data['servos'][0]['items']['Goal Position']['category'] = 'configuration'
        with self.assertRaisesRegex(ValueError, '寄存器定义不匹配'):
            web.normalize_backup(self.data)

    def test_arbitrary_address_and_overflow_rejected(self):
        item = self.data['servos'][0]['items']['Position P Gain']
        item['address'] = 116
        with self.assertRaises(ValueError):
            web.normalize_backup(self.data)
        item['address'] = 84
        item['value'] = 65536
        with self.assertRaises(ValueError):
            web.normalize_backup(self.data)

    def test_missing_incomplete_and_duplicate_rejected(self):
        for change in (
            lambda d: d['servos'].append(copy.deepcopy(d['servos'][0])),
            lambda d: d['servos'][0].update(complete=False),
            lambda d: d['servos'][0]['items'].pop('Operating Mode'),
            lambda d: d['servos'][0]['items']['ID'].update(value=99),
            lambda d: d['servos'][0]['items']['Protocol Type'].update(value=1),
        ):
            data = copy.deepcopy(self.data)
            change(data)
            with self.assertRaises(ValueError):
                web.normalize_backup(data)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = web.ThreadingHTTPServer(('127.0.0.1', 0), web.Handler)
        self.server.app = web.Tool(demo=True, output_dir=self.temp.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_html_state_and_ports(self):
        with urlopen(self.url) as response:
            self.assertIn('reachymini舵机调试助手', response.read().decode())
        with urlopen(self.url + '/api/state') as response:
            self.assertTrue(json.load(response)['demo'])
        with urlopen(self.url + '/api/ports') as response:
            self.assertEqual(json.load(response)[0]['device'], 'DEMO')

    def test_local_server_cannot_share_a_port(self):
        server = web.LocalServer(('127.0.0.1', 0), web.Handler)
        try:
            with self.assertRaises(OSError):
                other = web.LocalServer(server.server_address, web.Handler)
                other.server_close()
        finally:
            server.server_close()

    def test_cross_origin_and_missing_token_blocked(self):
        for headers in (
            {'Content-Type': 'application/json'},
            {'Content-Type': 'application/json', 'X-Tool-Token': self.server.app.token, 'Origin': 'http://evil.example'},
        ):
            request = Request(self.url + '/api/restore', data=b'{}', headers=headers)
            with self.assertRaises(HTTPError) as cm:
                urlopen(request)
            self.assertEqual(cm.exception.code, 403)

    def test_invalid_host_and_file_traversal_blocked(self):
        request = Request(self.url + '/api/state', headers={'Host': 'evil.example'})
        with self.assertRaises(HTTPError) as cm:
            urlopen(request)
        self.assertEqual(cm.exception.code, 403)
        with self.assertRaises(HTTPError) as cm:
            urlopen(self.url + '/files/../web_tool.py')
        self.assertEqual(cm.exception.code, 404)

    def test_serial_operations_are_exclusive(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(payload):
            entered.set()
            release.wait(3)
            return 'done'
        with patch.object(self.server.app, 'do_scan', blocked):
            self.server.app.start('scan', {})
            self.assertTrue(entered.wait(2))
            try:
                with self.assertRaisesRegex(ValueError, '已有操作'):
                    self.server.app.start('backup', {})
            finally:
                release.set()
        # Join the operation before deleting its temporary output directory.
        for thread in threading.enumerate():
            if thread is not threading.current_thread() and thread is not self.thread and thread.name.startswith('Thread-'):
                thread.join(3)


if __name__ == '__main__':
    unittest.main()
