import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from font_source import resolve_fonts
from zar import filehash


class FontSourceTests(unittest.TestCase):
    def test_matching_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            font = pathlib.Path(temp) / 'sample.ttf'
            font.write_bytes(b'fixture font input')
            profile = {'fonts': {'body': {'file': 'SAMPLE.TTF', 'sha256': filehash(font)}}}
            with patch('font_source.discover', return_value=[font]):
                self.assertEqual(resolve_fonts(profile), {'body': font})

    def test_missing_font_fails(self):
        with patch('font_source.discover', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'Installed font not found'):
                resolve_fonts({'fonts': {'body': {'file': 'missing.ttf', 'sha256': '0' * 64}}})

    def test_changed_identity_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            font = pathlib.Path(temp) / 'sample.ttf'
            font.write_bytes(b'wrong font')
            with patch('font_source.discover', return_value=[font]):
                with self.assertRaisesRegex(ValueError, 'Installed font identity changed'):
                    resolve_fonts({'fonts': {'body': {'file': font.name, 'sha256': '0' * 64}}})

    def test_profile_is_body_only(self):
        path = pathlib.Path(__file__).resolve().parents[1] / 'locales/zh-CN/font-profile.json'
        profile = json.loads(path.read_text('utf-8'))
        self.assertEqual(set(profile), {'schema', 'fonts'})
        self.assertEqual(set(profile['fonts']), {'body'})
        self.assertEqual(profile['fonts']['body']['pixel_size'], 12)


if __name__ == '__main__':
    unittest.main()
