import copy
import pathlib
import struct
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from binfont import BinFont, Glyph
from build_font import build_font
from test_binfont import fixture


def atlas_fixture(height=256):
    base = BinFont(fixture())
    return base.write(base.glyphs, bytes([20, 30, 40, 50]) * (128 * height), 128, height)


class BuildFontTests(unittest.TestCase):
    def setUp(self):
        from PIL import ImageFont
        self.font = ImageFont.load_default(size=12)
        self.profile = {'fonts': {'body': {'pixel_size': 12, 'cell_width': 12,
                                          'cell_height': 15, 'advance': 12}}}
        self.contexts = [patch('build_font.resolve_fonts', return_value={'body': pathlib.Path('fixture.ttf')}),
                         patch('build_font.font_metadata', return_value={'sha256': 'fixture-sha'}),
                         patch('PIL.ImageFont.truetype', return_value=self.font),
                         patch('fontTools.ttLib.TTFont')]
        for context in self.contexts:
            self.addCleanup(context.stop)
            result = context.start()
        self.ttf = result
        self.ttf.return_value.__enter__.return_value.getBestCmap.return_value = {66: 'B', 67: 'C'}
        self.original = atlas_fixture()

    def test_append_preserves_pixels_metrics_and_base_height(self):
        result, report = build_font(self.original, {66: 128, 67: 129}, self.profile)
        before, after = BinFont(self.original), BinFont(result)
        self.assertEqual((after.width, after.height), (128, 512))
        self.assertEqual(after.rgba[:len(before.rgba)], before.rgba)
        self.assertEqual(after.glyphs[65], before.glyphs[65])
        self.assertEqual(after.glyph_rgba(65), before.glyph_rgba(65))
        self.assertEqual(after.base_height, before.base_height)
        self.assertEqual(after.glyphs[128], Glyph(0, 256, 15, 12, 12, 0, 0))
        self.assertEqual(after.glyphs[129].x, 12)
        self.assertTrue(all(g['ink_pixels'] > 0 for g in report['added_glyphs']))
        self.assertEqual(report['font_sha256'], 'fixture-sha')
        self.assertTrue(report['base_height_unchanged'])

    def test_reject_original_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'overwrites'):
            build_font(self.original, {66: 65}, self.profile)

    def test_reject_duplicate_slots(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            build_font(self.original, {66: 128, 67: 128}, self.profile)

    def test_reject_missing_cmap(self):
        with self.assertRaisesRegex(ValueError, 'glyph missing'):
            build_font(self.original, {68: 128}, self.profile)

    def test_reject_empty_raster(self):
        self.ttf.return_value.__enter__.return_value.getBestCmap.return_value = {32: 'space'}
        with self.assertRaisesRegex(ValueError, 'raster is empty'):
            build_font(self.original, {32: 128}, self.profile)

    def test_reject_clipping(self):
        profile = copy.deepcopy(self.profile)
        profile['fonts']['body']['cell_width'] = 1
        with self.assertRaisesRegex(ValueError, 'outside configured cell'):
            build_font(self.original, {66: 128}, profile)

    def test_reject_atlas_overflow(self):
        with self.assertRaisesRegex(ValueError, '1024 metric'):
            build_font(atlas_fixture(1024), {66: 128}, self.profile)

    def test_reject_invalid_mapping(self):
        for mapping in [{}, {0xD800: 128}, {0x110000: 128}, {66: 0x10000}, {66: 0xD800}, {True: 128}]:
            with self.assertRaises(ValueError):
                build_font(self.original, mapping, self.profile)

    def test_reject_invalid_cell(self):
        profile = copy.deepcopy(self.profile)
        profile['fonts']['body']['advance'] = 256
        with self.assertRaisesRegex(ValueError, 'Invalid font cell'):
            build_font(self.original, {66: 128}, profile)


if __name__ == '__main__':
    unittest.main()
