import hashlib
import pathlib
import random
import struct
import sys
import unittest

import lz4.block

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from texture import Texture


def fixture(width=4, height=3, header=(122, 32)):
    rgba = bytes(range(width * height * 4))
    return Texture.encode(width, height, rgba, header_words=header), rgba


def replace_inner(data, inner):
    z = lz4.block.compress(inner, store_size=False)
    return data[:16] + struct.pack('<2I', len(inner), len(z)) + z + b'\0' * (4 - len(z) % 4)


class TextureTests(unittest.TestCase):
    def test_decode(self):
        raw, rgba = fixture()
        t = Texture(raw)
        self.assertEqual((t.width, t.height, t.rgba), (4, 3, rgba))
        self.assertEqual(t.describe()['source_sha256'], hashlib.sha256(raw).hexdigest())

    def test_exact_noop(self):
        raw, rgba = fixture()
        t = Texture(raw)
        self.assertEqual(t.rebuild(), raw)
        self.assertEqual(t.rebuild(rgba), raw)

    def test_modified_and_deterministic_rebuild(self):
        raw, rgba = fixture()
        t = Texture(raw)
        replacement = bytes(reversed(rgba))
        out = t.rebuild(replacement)
        self.assertNotEqual(out, raw)
        self.assertEqual(t.rebuild(replacement), out)
        self.assertEqual(Texture(out).rgba, replacement)
        self.assertEqual(t.data, raw)
        self.assertEqual(Texture(out).rebuild(rgba), Texture.encode(4, 3, rgba))

    def test_hash_binding(self):
        raw, rgba = fixture()
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(Texture(raw, expected_sha256=digest).rebuild(expected_sha256=digest), raw)
        with self.assertRaises(ValueError): Texture(raw, expected_sha256='0' * 64)
        with self.assertRaises(ValueError): Texture(raw).rebuild(expected_sha256='0' * 64)

    def test_opaque_header_preserved(self):
        raw, rgba = fixture(header=(0x12345678, 0x87654321))
        t = Texture(raw)
        self.assertEqual(Texture(t.rebuild(bytes(reversed(rgba)))).header_words, t.header_words)
        with self.assertRaises(ValueError): Texture(raw, expected_header=(122, 32))

    def test_truncated(self):
        raw, _ = fixture()
        for n in range(len(raw)):
            with self.assertRaises(ValueError): Texture(raw[:n])

    def test_size_and_dimensions_bounded(self):
        raw, _ = fixture()
        for offset, number in [(8, 0), (12, 0), (8, 16385), (16, 0xffffffff), (20, 0xffffffff)]:
            bad = bytearray(raw)
            struct.pack_into('<I', bad, offset, number)
            with self.assertRaises(ValueError): Texture(bytes(bad))
        with self.assertRaises(ValueError): Texture(raw, max_size=16)
        with self.assertRaises(ValueError): Texture(raw, max_dimension=2)

    def test_bad_outer_tail(self):
        raw, _ = fixture()
        for b in [raw + b'\0', raw[:-1] + b'\1']:
            with self.assertRaises(ValueError): Texture(b)

    def test_bad_inner_frame(self):
        raw, _ = fixture()
        size, csize = struct.unpack_from('<2I', raw, 16)
        inner = lz4.block.decompress(raw[24:24+csize], uncompressed_size=size)
        for bad in [inner + b'\0', inner[:-1] + b'\1', b'\0' * len(inner)]:
            with self.assertRaises(ValueError): Texture(replace_inner(raw, bad))

    def test_wrong_decoded_rgba_size(self):
        raw, _ = fixture()
        size, csize = struct.unpack_from('<2I', raw, 16)
        inner = bytearray(lz4.block.decompress(raw[24:24+csize], uncompressed_size=size))
        struct.pack_into('<I', inner, 0, 47)
        with self.assertRaises(ValueError): Texture(replace_inner(raw, bytes(inner)))

    def test_corrupt_lz4(self):
        raw, _ = fixture()
        bad = bytearray(raw)
        bad[24:30] = b'\xff' * 6
        with self.assertRaises(ValueError): Texture(bytes(bad))

    def test_bad_replacement(self):
        raw, _ = fixture()
        for value in [b'', b'123', 'x' * 48]:
            with self.assertRaises(ValueError): Texture(raw).rebuild(value)
        for width, height, rgba in [(0, 1, b''), (1, 1, b''), (1, 1, '1234')]:
            with self.assertRaises(ValueError): Texture.encode(width, height, rgba)

    def test_full_word_alignment_padding(self):
        # Synthetic inputs exercise each possible mandatory padding length.
        lengths = set()
        for n in range(1, 180):
            rng = random.Random(n)
            rgba = bytes(rng.randrange(4) for i in range(n * 4))
            t = Texture(Texture.encode(n, 1, rgba))
            lengths.add(len(t.inner_tail))
            lengths.add(len(t.outer_tail))
        self.assertEqual(lengths, {1, 2, 3, 4})


if __name__ == '__main__':
    unittest.main()
