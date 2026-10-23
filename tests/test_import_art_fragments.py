import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from art_delta import apply, capture, sha
from import_art_fragments import import_fragments


class FragmentImportTests(unittest.TestCase):
    def test_quarter_turn_exact_pixels_alpha_and_roundtrip(self):
        original = Image.new('RGBA', (8, 8), (40, 20, 10, 137))
        source = Image.new('RGBA', (4, 2))
        source.putdata([(x*30, y*100, 50, 255) for y in range(2) for x in range(4)])
        before = original.tobytes()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source.save(folder / 'part.png')
            part = dict(file='part.png', sha256=sha((folder/'part.png').read_bytes()),
                        generated_box=[0, 0, 4, 2], native_box=[3, 2, 5, 6],
                        rotation_ccw=90, wording='fixture')
            base = capture(original, original, resource='fixture', prompt='base')
            recipe = dict(resource='fixture', prompt='reviewed art', fragments=[part])
            delta, edited = import_fragments(original, base, recipe, folder)
            self.assertEqual(original.tobytes(), before)
            self.assertEqual(edited.getchannel('A').tobytes(), original.getchannel('A').tobytes())
            expected = source.transpose(Image.Transpose.ROTATE_90).convert('RGB')
            self.assertEqual(edited.crop((3, 2, 5, 6)).convert('RGB').tobytes(), expected.tobytes())
            self.assertEqual(apply(original, delta).tobytes(), edited.tobytes())
            for y in range(8):
                for x in range(8):
                    if not (3 <= x < 5 and 2 <= y < 6):
                        self.assertEqual(edited.getpixel((x, y)), original.getpixel((x, y)))
            for key, value, error in [('sha256', 'wrong', 'identity'),
                                      ('rotation_ccw', 45, 'quarter-turn'),
                                      ('generated_box', [-1, 0, 4, 2], 'outside'),
                                      ('native_box', [3, 2, 9, 6], 'outside'),
                                      ('file', '../part.png', 'basename')]:
                bad = copy.deepcopy(recipe)
                bad['fragments'][0][key] = value
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, error):
                    import_fragments(original, base, bad, folder)


if __name__ == '__main__':
    unittest.main()
