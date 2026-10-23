import gzip
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from source_delta import build, apply, MAGIC


class SourceDeltaTests(unittest.TestCase):
    def test_shifted_reuse_and_determinism(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            a = bytes(range(256)) * 8 + b'A' * 512 + b'Z' * 512
            b = a[:512] + b'new' * 171 + a[512:] + b'end'
            (d/'source').write_bytes(a); (d/'target').write_bytes(b)
            recipe = build(d/'source', d/'target', d/'delta')
            again = build(d/'source', d/'target', d/'second')
            self.assertEqual(recipe, again)
            apply(d/'source', d/'delta', d/'output', recipe)
            self.assertEqual((d/'output').read_bytes(), b)
            self.assertGreater(recipe['copy_bytes'], 0)
            self.assertEqual((d/'source').read_bytes(), a)
            (d/'source').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'Source identity'):
                apply(d/'source', d/'delta', d/'output', recipe)

    def test_malformed_commands_and_output_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d/'source').write_bytes(b'x' * 512); (d/'target').write_bytes(b'y' * 512)
            recipe = build(d/'source', d/'target', d/'delta')
            for body in [MAGIC + b'\x03', MAGIC + b'\x01' + struct.pack('<QQ', 500, 512),
                         MAGIC + b'\x02' + struct.pack('<I', 512) + b'y', MAGIC + b'\0extra',
                         MAGIC + b'\0']:
                (d/'bad').write_bytes(gzip.compress(body, mtime=0))
                with self.assertRaises(ValueError):
                    apply(d/'source', d/'bad', d/'output', recipe)


if __name__ == '__main__':
    unittest.main()
