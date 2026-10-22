import pathlib,struct,sys,unittest,zlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from binfont import Glyph,BinFont,inflate_frame


def frame(raw):
    z=zlib.compress(raw)
    n=(12+len(z)+3)//4*4
    return struct.pack('<3I',0x20000,len(z),n)+z+b'\0'*(n-12-len(z))


def fixture():
    head=struct.pack('<II',1,8)+struct.pack('<256I',1032,*([0]*255))
    page=bytearray(2080);page[65//8]=1<<(65%8)
    page[32+65*8:40+65*8]=Glyph(0,0,2,2,3,-1,1).pack()
    raw=bytes([0,0,0,255])*16
    inner=frame(raw);outer=frame(inner)
    texture=struct.pack('<6H2I',0,1,4,4,4,4,0,16)
    body=head+page+texture+outer[:4]+struct.pack('<I',len(inner))+outer[4:]
    return body+struct.pack('<HH8II',8,0,0,3112,len(body),2,3112,len(body)-3112,len(body)+2,0,2)


class BinFontTests(unittest.TestCase):
    def test_metrics_roundtrip(self):
        g=Glyph(1023,1023,4095,255,255,-128,127)
        self.assertEqual(Glyph.unpack(g.pack()),g)
    def test_metrics_overflow(self):
        for g in [Glyph(1024,0,1,1,1,0,0),Glyph(0,0,1,256,1,0,0),Glyph(0,0,1,1,1,-129,0)]:
            with self.assertRaises(ValueError):g.pack()
    def test_parse_and_noop(self):
        b=fixture();f=BinFont(b)
        self.assertEqual(f.rebuild(),b);self.assertEqual(list(f.glyphs),[65])
        self.assertEqual(len(f.glyph_rgba(65)),16)
        self.assertEqual(f.sections[3],2)
    def test_truncation(self):
        for n in [0,7,1031,3111,3130,len(fixture())-20]:
            with self.assertRaises(ValueError):BinFont(fixture()[:n])
    def test_absent_metrics_rejected(self):
        b=bytearray(fixture());b[1032+32]=1
        with self.assertRaises(ValueError):BinFont(b)
    def test_inflation_bounds(self):
        with self.assertRaises(ValueError):inflate_frame(zlib.compress(b'abc'),2)
        with self.assertRaises(ValueError):inflate_frame(zlib.compress(b'a')+b'junk',1)
        with self.assertRaises(ValueError):inflate_frame(b'',2**30)

    def test_write_add_page_and_expand(self):
        f=BinFont(fixture());glyphs=dict(f.glyphs)
        glyphs[0x65B0]=Glyph(0,4,2,2,3,0,0)
        rgba=f.rgba+bytes([255,255,255,255])*16
        g=BinFont(f.write(glyphs,rgba,4,8))
        self.assertEqual(g.glyphs,glyphs)
        self.assertEqual(g.glyph_rgba(65),f.glyph_rgba(65))
        self.assertEqual(g.base_height,f.base_height)
        self.assertEqual(len(g.pages),2)
        self.assertEqual(g.sections[3],4)
    def test_write_noop(self):
        f=BinFont(fixture())
        self.assertEqual(f.write(f.glyphs,f.rgba,f.width,f.height),fixture())
    def test_bad_write(self):
        f=BinFont(fixture())
        with self.assertRaises(ValueError):f.write({0x10000:Glyph(0,0,1,1,1,0,0)},f.rgba,4,4)
        with self.assertRaises(ValueError):f.write(f.glyphs,b'',4,4)
    def test_bad_relocation(self):
        b=bytearray(fixture());r=BinFont(b).texture_end;b[r]=12
        with self.assertRaises(ValueError):BinFont(b)

if __name__=='__main__':unittest.main()
