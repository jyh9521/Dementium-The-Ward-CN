"""Actual native menu coordinate regression for all command tables."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from debug_menu import build_debug_menu,rollback_debug
from debug_menu_text import replay_debug_layout,verify_text
from binfont import BinFont
ORIGINAL=ROOT/'build/full/rollback-sample/Dementium.exe'
FONT=ROOT/'build/release-candidate/full.binfont'
@unittest.skipUnless(ORIGINAL.exists() and FONT.exists(),'offline original and font required')
class DebugLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes()
        cls.catalog=json.loads((ROOT/'locales/zh-CN/debug-menu.json').read_text(encoding='utf-8'))
        cls.font=BinFont(FONT.read_bytes())
        cls.modified,cls.recipe=build_debug_menu(cls.original,cls.original,cls.catalog)
    def test_native_all_tables_safe_margin_and_columns(self):
        report=replay_debug_layout(self.modified,self.catalog,self.font)
        self.assertEqual(len(report['rows']),650)
        for row in report['rows']:
            self.assertEqual(row['name_x'],16,row)
            self.assertEqual(row['value_x'],112,row)
            self.assertGreaterEqual(row['gap'],16,row)
            self.assertEqual(row['y'],row['value_y'],row)
    def test_baseline_reproduces_clip_and_long_label_overlap(self):
        report=replay_debug_layout(self.original,self.catalog,self.font)
        self.assertTrue(all(r['name_x']==0 and r['value_x']==64 for r in report['rows']))
        longest=next(r for r in report['rows'] if r['target']=='简易生命修改')
        self.assertLess(longest['gap'],0)
    def test_font_metric_columns_and_corruption_guards(self):
        report=verify_text(self.modified,self.catalog,self.recipe['text'],self.font)
        self.assertEqual(report['layout']['value_x'],112)
        self.assertEqual(max(r['width'] for r in report['checks']),78)
        import pefile
        pe=pefile.PE(data=self.modified)
        at=pe.get_offset_from_rva(0xc743b);pe.close()
        broken=bytearray(self.modified);broken[at]^=1
        with self.assertRaisesRegex(ValueError,'layout instruction'):
            verify_text(bytes(broken),self.catalog,self.recipe['text'],self.font)
    def test_layout_is_inverse_bound(self):
        self.assertEqual(rollback_debug(self.modified,self.recipe),self.original)
if __name__=='__main__':unittest.main()
