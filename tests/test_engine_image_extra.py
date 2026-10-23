import pathlib,sys,struct,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from engine_image import encode_frame
from engine_image_extra import ExtraImage,verify_native_conversion

def fixture(fmt,raw,w=2,h=1):
 return struct.pack('<6H3I',fmt,1,w,h,w,h,0,w*h,len(raw))+encode_frame(encode_frame(raw))

class ExtraImageTests(unittest.TestCase):
 def test_gray_alpha(self):
  raw=fixture(5,bytes([10,20,30,40]));im=ExtraImage(raw)
  self.assertEqual(im.rgba,bytes([10,10,10,20,30,30,30,40]))
  self.assertEqual(im.rebuild(),raw)
 def test_gray_is_alpha_and_tail_preserved(self):
  raw=fixture(8,bytes([10,30,77]));im=ExtraImage(raw)
  self.assertEqual(im.rgba,bytes([10]*4+[30]*4));self.assertEqual(im.tail,b'M')
  self.assertEqual(im.rebuild(),raw)
 def test_guards(self):
  with self.assertRaises(ValueError):ExtraImage(fixture(8,b'x'))
  with self.assertRaises(ValueError):ExtraImage(fixture(0,b'12345678'))
  with self.assertRaises(ValueError):ExtraImage(fixture(5,b'1234')[:-1])
  raw=bytearray(fixture(5,b'1234'));struct.pack_into('<I',raw,20,5)
  with self.assertRaises(ValueError):ExtraImage(raw)
 def test_actual_native_loop(self):
  exe=pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\Dementium.exe')
  if not exe.exists():self.skipTest('user supplied executable absent')
  for fmt,raw in [(5,bytes(range(48))),(8,bytes(range(24)))]:
   image=ExtraImage(fixture(fmt,raw,6,4))
   self.assertTrue(verify_native_conversion(exe,image)['match'])

if __name__=='__main__':unittest.main()
