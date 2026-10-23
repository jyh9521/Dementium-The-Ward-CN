import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from debug_menu import build_debug_menu, original_guard, rollback_debug
from replay_debug_menu import verify_debug

# Local build fixture only: these tests never read or modify an installed game.
ORIGINAL = ROOT / 'build/full/rollback-sample/Dementium.exe'


class DebugMenuGuardTests(unittest.TestCase):
    def test_unknown_original_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            original_guard(b'MZ')

    def test_unknown_rollback_format_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            rollback_debug(b'MZ', {'format': 'unknown'})


@unittest.skipUnless(ORIGINAL.exists(), 'user-supplied offline original fixture absent')
class DebugMenuNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.catalog = json.loads((ROOT / 'locales/zh-CN/debug-menu.json').read_text(encoding='utf-8'))
        cls.modified, cls.recipe = build_debug_menu(cls.original, cls.original, cls.catalog)

    def test_exact_rollback_and_second_patch_rejection(self):
        self.assertEqual(rollback_debug(self.modified, self.recipe), self.original)
        with self.assertRaises(ValueError):
            build_debug_menu(self.modified, self.original, self.catalog)
        for data in [self.original, self.modified[:-1], b'X' + self.modified[1:]]:
            with self.assertRaises(ValueError):
                rollback_debug(data, self.recipe)
        altered = copy.deepcopy(self.recipe)
        altered['runs'][0]['after'] = 'ff' * (len(altered['runs'][0]['after']) // 2)
        with self.assertRaises(ValueError):
            rollback_debug(self.modified, altered)

    def test_leaf_bridge_and_inline_gate_preserve_unwind_directory(self):
        import pefile
        from debug_menu import GATE_RVA
        before=pefile.PE(data=self.original);after=pefile.PE(data=self.modified)
        self.assertEqual(before.OPTIONAL_HEADER.DATA_DIRECTORY[3].VirtualAddress,
                         after.OPTIONAL_HEADER.DATA_DIRECTORY[3].VirtualAddress)
        self.assertEqual(before.OPTIONAL_HEADER.DATA_DIRECTORY[3].Size,
                         after.OPTIONAL_HEADER.DATA_DIRECTORY[3].Size)
        self.assertEqual(before.get_data(before.OPTIONAL_HEADER.DATA_DIRECTORY[3].VirtualAddress,
                                        before.OPTIONAL_HEADER.DATA_DIRECTORY[3].Size),
                         after.get_data(after.OPTIONAL_HEADER.DATA_DIRECTORY[3].VirtualAddress,
                                       after.OPTIONAL_HEADER.DATA_DIRECTORY[3].Size))
        self.assertEqual(self.recipe['gate_bridge_rva'],GATE_RVA)
        self.assertEqual(after.get_data(GATE_RVA,5),bytes.fromhex('0fba660412'))
        self.assertEqual(after.sections[-1].Characteristics,0x60000020)
        self.assertFalse(after.sections[-1].Characteristics & 0x80000000)
        before.close();after.close()

    def test_two_base_actual_instruction_replay(self):
        report = verify_debug(self.original, self.modified, self.recipe)
        self.assertEqual(report['status'], 'PASS')
        self.assertFalse(report['game_launched'])
        self.assertFalse(report['steam_directory_modified'])
        self.assertEqual(len(report['results']), 4)
        for result in report['results']:
            self.assertEqual(len(result['opening_cases']), 40)
            self.assertEqual(result['ordinary_key_cases'], 56)
            self.assertEqual(len(result['raw_bridge_cases']), 12)
            self.assertEqual(len(result['native_menu']), 8)
            self.assertEqual([r['opened_debug'] for r in result['f1_lifecycle']],
                [True, False, False, True, False] if result['variant'] == 'modified' else [False] * 5)
            self.assertEqual([r['opened_debug'] for r in result['f1_layout1_lifecycle']],
                [True, False, False, True, False] if result['variant'] == 'modified' else [False] * 5)
            self.assertEqual([r['opened_debug'] for r in result['f1_busy_lifecycle']],
                [False, False, False, True, False] if result['variant'] == 'modified' else [False] * 5)
            self.assertEqual(result['native_menu'][-1]['activation_offsets'], ['0x15a8'])
            self.assertTrue(result['native_menu'][-1]['returned_normally'])
            self.assertEqual(result['startup_keyboard_emulator']['after'], 0)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_replay_rejects_corrupt_modified_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            verify_debug(self.original, self.modified[:-1], self.recipe)


if __name__ == '__main__':
    unittest.main()
