from pathlib import Path
import sys
import tempfile
import os
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_probe import inputs
from investigate import ensure_output
from replay_text import Replay
from workspace_io import validate_output_tree


class ProbeGuardTests(unittest.TestCase):
    def test_hardlink_output_rejected_without_touching_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/'source';source.write_bytes(b'original fixture')
            out=p/'output';out.mkdir();os.link(source,out/'rom.zar')
            with self.assertRaisesRegex(ValueError,'Multiple-link'):validate_output_tree(out)
            self.assertEqual(source.read_bytes(),b'original fixture')

    def test_regular_tree_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'sub').mkdir();(p/'sub'/'fixture').write_text('ordinary')
            validate_output_tree(p)
    def test_wrong_executable_rejected_before_pe_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.exe';p.write_bytes(b'not a supported executable')
            with self.assertRaisesRegex(ValueError,'Unsupported executable'):Replay(p)

    def test_invalid_locale(self):
        for locale in ['../en','/en','en\\x','.','..','']:
            with self.assertRaisesRegex(ValueError,'Invalid locale'):inputs(Path('unused'),locale)

    def test_installation_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            game=Path(d)
            with self.assertRaisesRegex(ValueError,'Output must'):ensure_output(game,game/'build')

    def test_external_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'Output must'):ensure_output(Path('original'),Path(d)/'output')

    def test_unknown_original_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'unknown.txt').write_text('fixture')
            with self.assertRaisesRegex(ValueError,'Original installation identity changed'):inputs(p,'zh-CN')
