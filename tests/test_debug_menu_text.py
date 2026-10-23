"""Data guards for the native, locale-neutral debug menu text layer."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from debug_menu_text import load_catalog,validate_catalog,required_text,build_text_patch,restore_text
ROOT=Path(__file__).resolve().parents[1]
class DebugTextTests(unittest.TestCase):
    def setUp(self):self.catalog=load_catalog(ROOT/'locales/zh-CN/debug-menu.json')
    def test_complete_tables(self):
        self.assertEqual(len(self.catalog['tables']),21)
        self.assertEqual(sum(t['count'] for t in self.catalog['tables']),325)
        self.assertEqual(len(self.catalog['entries']),306)
        self.assertEqual(len(required_text(self.catalog)),308)
        self.assertEqual(sum(len(s['references']) for s in self.catalog['states']),16)
    def test_overlong_label_rejected(self):
        self.catalog['entries'][0]['target']='字'*22
        with self.assertRaisesRegex(ValueError,'capacity'):validate_catalog(self.catalog)
    def test_overlong_state_rejected(self):
        self.catalog['states'][0]['target']='字'*6
        with self.assertRaisesRegex(ValueError,'capacity'):validate_catalog(self.catalog)
    def test_duplicate_id_rejected(self):
        self.catalog['entries'][1]['id']=self.catalog['entries'][0]['id']
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_catalog(self.catalog)
    def test_table_coverage_rejected(self):
        self.catalog['entries'][0]['pointers'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'):validate_catalog(self.catalog)
    def test_source_build_rejected(self):
        self.catalog['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):validate_catalog(self.catalog)
    def test_load_identifier_protected(self):
        row=next(r for r in self.catalog['entries'] if r['source'].startswith('Load '));row['target']='载入 unknown'
        with self.assertRaisesRegex(ValueError,'identifier'):validate_catalog(self.catalog)
    def test_invalid_unicode_rejected(self):
        for target in ['空\0格','\ud800','\U00010000']:
            catalog=copy.deepcopy(self.catalog);catalog['entries'][0]['target']=target
            with self.assertRaises(ValueError):validate_catalog(catalog)
    def test_real_table_inverse_when_fixture_available(self):
        path=ROOT/'build/full/rollback-sample/Dementium.exe'
        if not path.is_file():self.skipTest('User-supplied original is not bundled')
        original=path.read_bytes();patched,pool,recipe=build_text_patch(original,self.catalog,0xd20000)
        self.assertEqual(restore_text(patched,recipe),original)
        self.assertEqual(len(recipe['runs']),341)
        damaged=bytearray(original);damaged[recipe['runs'][0]['offset']]^=1
        with self.assertRaisesRegex(ValueError,'identity'):build_text_patch(bytes(damaged),self.catalog,0xd20000)
if __name__=='__main__':unittest.main()
