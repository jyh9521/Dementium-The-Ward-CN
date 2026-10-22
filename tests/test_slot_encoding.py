from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from slot_encoding import validate_slots,encode,decode


class SlotTests(unittest.TestCase):
    def test_roundtrip(self):
        m={'新':129,'游':141,'戏':143}
        validate_slots(m,SimpleNamespace(glyphs={0:None,32:None}),[b'New Game'])
        self.assertEqual(encode('新游戏',m),bytes([129,141,143]))
        self.assertEqual(decode(encode('新游戏 ABC',m),m),'新游戏 ABC')

    def test_occupied(self):
        with self.assertRaises(ValueError):validate_slots({'新':129},SimpleNamespace(glyphs={129:None}),[])
        with self.assertRaises(ValueError):validate_slots({'新':129},SimpleNamespace(glyphs={}),[b'\x81'])

    def test_invalid_mapping(self):
        for m in [{},{'新':129,'游':129},{'新':65},{'x':129},{'新游':129}]:
            with self.assertRaises(ValueError):validate_slots(m,SimpleNamespace(glyphs={}),[])

    def test_unmapped(self):
        for text in ['新游戏','\0','\n','é']:
            with self.assertRaises(ValueError):encode(text,{'新':129})
