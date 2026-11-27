import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import web_tool as web
from test_web_tool import RecordingBus


class RobotModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tool = web.Tool(demo=True, output_dir=self.temp.name)
        self.bus = RecordingBus(self.tool.memory)
        self.tool.bus_factory = lambda port, baud: self.bus
        self.delay = patch.object(web.core, 'WRITE_VERIFY_DELAY', 0)
        self.delay.start()

    def tearDown(self):
        self.delay.stop()
        self.temp.cleanup()

    def scan(self):
        self.tool.do_scan(dict(port='DEMO', baudrate=1000000))

    def switch(self):
        self.tool.do_robot(dict(robot_type='microduck'))

    def test_switch_clears_connection_backup_profile_and_old_plan(self):
        self.scan()
        self.tool.do_backup({})
        self.tool.do_id_plan(dict(old_id=15, new_id=20))
        plan = dict(plan_id=self.tool.plan['id'], confirm='CHANGE 15 TO 20')
        self.switch()
        self.assertIsNone(self.tool.connection)
        self.assertIsNone(self.tool.backup)
        self.assertIsNone(self.tool.plan)
        self.assertEqual(self.tool.devices, {})
        self.assertEqual(self.tool.profiles, {})
        with self.assertRaises(ValueError):
            self.tool.do_change_id(plan)
        self.assertEqual(self.bus.writes, [])

    def test_microduck_rejects_reachy_profiles_and_builtin_defaults(self):
        data = json.loads((web.ROOT / 'DYNAMIXEL_XL330_BACKUP.json').read_text())
        self.switch()
        for tag in (None, 'reachymini'):
            incoming = copy.deepcopy(data)
            if tag: incoming['robot_type'] = tag
            with self.assertRaisesRegex(ValueError, '机型不匹配'):
                self.tool.do_profile(dict(data=incoming))
        with self.assertRaises(ValueError):
            self.tool.do_default_profile({})
        self.assertEqual(self.tool.profiles, {})
        self.assertEqual(self.bus.writes, [])

    def test_microduck_tagged_backup_restore_and_id_change_in_memory(self):
        self.switch()
        self.scan()
        self.tool.do_backup({})
        data = json.loads(Path(self.temp.name, self.tool.backup['name']).read_text())
        self.assertEqual(data['robot_type'], 'microduck')
        self.tool.do_profile(dict(data=data, name='microduck-test.json'))
        self.tool.profiles[15]['items']['Position P Gain']['value'] = 300
        self.tool.do_plan(dict(ids=[15]))
        self.assertEqual(self.bus.writes, [])
        self.tool.do_restore(dict(plan_id=self.tool.plan['id'], confirm='RESTORE'))
        self.assertEqual(self.bus.read_register(15, 84, 2), 300)
        self.assertFalse(any(address in (100, 102, 104, 116) for _, address, _, _ in self.bus.writes))
        self.tool.do_backup({})
        self.tool.do_id_plan(dict(old_id=15, new_id=20))
        self.tool.do_change_id(dict(plan_id=self.tool.plan['id'], confirm='CHANGE 15 TO 20'))
        self.assertIn(20, self.tool.devices)
        self.assertNotIn(15, self.tool.devices)

    def test_missing_ids_match_selected_robot(self):
        self.switch()
        self.tool.devices = {sid: [1200, 53] for sid in web.EXPECTED_IDS['microduck'] if sid != 24}
        self.tool.connection = dict(port='DEMO', baudrate=1000000)
        self.assertEqual(self.tool.state()['missing_ids'], [24])
        self.assertEqual(len(self.tool.state()['expected_ids']), 15)

    def test_busy_and_stale_clients_cannot_switch_or_start_actions(self):
        self.tool.job['status'] = 'running'
        with self.assertRaisesRegex(ValueError, '已有操作'):
            self.tool.start('robot', dict(robot_type='microduck'))
        self.tool.job['status'] = 'idle'
        self.switch()
        with self.assertRaisesRegex(ValueError, '机型已变化'):
            self.tool.start('restore', dict(_robot_type='reachymini'))
        self.assertEqual(self.bus.writes, [])

    def test_reachy_restored_on_switch_back_rejects_microduck_profile(self):
        self.switch()
        self.scan()
        self.tool.do_backup({})
        data = json.loads(Path(self.temp.name, self.tool.backup['name']).read_text())
        self.tool.do_robot(dict(robot_type='reachymini'))
        self.assertEqual(set(self.tool.profiles), set(range(10, 19)))
        with self.assertRaisesRegex(ValueError, '机型不匹配'):
            self.tool.do_profile(dict(data=data))


if __name__ == '__main__':
    unittest.main()
