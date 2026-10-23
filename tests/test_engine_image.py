from pathlib import Path
import struct
import sys
import unittest
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from engine_image import EngineImage, decode_frame, encode_frame


def fixture(fmt=0,mips=2,w=4,h=4,aw=None,ah=None,prefix=b'ABCD',opaque=0x12345678):
    aw=aw or w;ah=ah or h;bpp={0:4,1:3}.get(fmt,4)
    count=sum(max(1,aw>>i)*max(1,ah>>i) for i in range(mips))
    pixels=bytes(i%256 for i in range(count*bpp))
    header=struct.pack('<6H2I',fmt,mips,w,h,aw,ah,opaque,count)
    return prefix+header+struct.pack('<I',len(pixels))+encode_frame(encode_frame(pixels)),pixels


class EngineImageTests(unittest.TestCase):
    def test_rgba_all_mips(self):
        raw,pixels=fixture();i=EngineImage(raw,4)
        self.assertEqual(i.pixels,pixels);self.assertEqual(i.level_pixels(1),pixels[64:])
        self.assertEqual(i.rebuild(),raw);self.assertEqual(i.write(pixels),raw)

    def test_rgb_without_prefix(self):
        raw,pixels=fixture(fmt=1,prefix=b'');i=EngineImage(raw)
        self.assertEqual(i.mode,'RGB');self.assertEqual(len(i.level_pixels()),4*4*3)

    def test_visible_crop_uses_allocation_stride(self):
        raw,pixels=fixture(w=3,h=2,aw=4,ah=2,mips=1)
        i=EngineImage(raw,4)
        self.assertEqual(i.level_pixels(),pixels[:12]+pixels[16:28])

    def test_write_preserves_metadata_and_lower_mips(self):
        raw,pixels=fixture();i=EngineImage(raw,4)
        changed=bytes([pixels[0]^1])+pixels[1:]
        result=i.write(changed);other=EngineImage(result,4)
        self.assertEqual(result[:28],raw[:28]);self.assertEqual(other.pixels,changed)
        self.assertEqual(other.level_pixels(1),i.level_pixels(1))

    def test_partial_mips_rejected(self):
        raw,pixels=fixture()
        with self.assertRaisesRegex(ValueError,'All original'):EngineImage(raw,4).write(pixels[:64])

    def test_unknown_format_rejected(self):
        raw,_=fixture(fmt=5)
        with self.assertRaisesRegex(ValueError,'Unknown pixel'):EngineImage(raw,4)

    def test_size_mismatch_rejected(self):
        raw,_=fixture();b=bytearray(raw);struct.pack_into('<I',b,24,1)
        with self.assertRaisesRegex(ValueError,'payload length'):EngineImage(b,4)

    def test_trailing_resource_bytes_rejected(self):
        raw,_=fixture()
        with self.assertRaises(ValueError):EngineImage(raw+b'JUNK',4)

    def test_frame_bound_rejected(self):
        frame=bytearray(encode_frame(b'abc'));struct.pack_into('<I',frame,0,129*1024*1024)
        with self.assertRaises(ValueError):decode_frame(frame)

    def test_extra_compressed_stream_rejected(self):
        packed=zlib.compress(b'abc')+zlib.compress(b'extra')
        n=(12+len(packed)+3)//4*4
        frame=struct.pack('<3I',3,len(packed),n)+packed+b'\0'*(n-12-len(packed))
        with self.assertRaisesRegex(ValueError,'boundary'):decode_frame(frame)

    def test_nonzero_alignment_padding_rejected(self):
        frame=bytearray(encode_frame(b'abc'))
        self.assertGreater(len(frame),12+struct.unpack_from('<I',frame,4)[0])
        frame[-1]=1
        with self.assertRaisesRegex(ValueError,'Nonzero'):decode_frame(frame)

if __name__=='__main__':unittest.main()
