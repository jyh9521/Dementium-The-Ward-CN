import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from runtime_patch import *
from replay_utf8 import UTF8Replay
EXE=pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\Dementium.exe')

class RuntimePatchTests(unittest.TestCase):
    def test_text_guard(self):
        self.assertEqual(validate_text('新游戏'),b'\xe6\x96\xb0\xe6\xb8\xb8\xe6\x88\x8f')
        for value in ['a'*4096,'\0','\ud800','😀']:
            with self.assertRaises(ValueError):validate_text(value)
    @unittest.skipUnless(EXE.exists(),'user-supplied exact executable absent')
    def test_identity_and_rollback(self):
        original=EXE.read_bytes();modified,recipe=patch_bytes(original)
        self.assertEqual(rollback_bytes(modified,recipe),original)
        self.assertEqual(modified[FILE_OFFSET:FILE_OFFSET+28],PROLOGUE)
        self.assertEqual(modified[FILE_OFFSET+0x1f5:FILE_OFFSET+LENGTH],original[FILE_OFFSET+0x1f5:FILE_OFFSET+LENGTH])
        self.assertEqual(original[:FILE_OFFSET],modified[:FILE_OFFSET])
        self.assertEqual(original[FILE_OFFSET+LENGTH:],modified[FILE_OFFSET+LENGTH:])
        for data in [modified,original[:-1],b'X'+original[1:]]:
            with self.assertRaises(ValueError):patch_bytes(data)
        with self.assertRaises(ValueError):rollback_bytes(original,recipe)
    @unittest.skipUnless(EXE.exists(),'user-supplied exact executable absent')
    def test_actual_decoder_instructions(self):
        r=UTF8Replay(EXE)
        for text in ['', 'New Game', '新游戏','A新é游ß戏Z','\x01\x02\r\n\tABC', '\u0080\u07ff\u0800\ud7ff\ue000\uffff']:
            with self.subTest(text=text):self.assertEqual(r.decode(text.encode()),list(map(ord,text)))
        for raw,expected in [(b'\xff',[63]),(b'\xc0\x80',[63,63]),(b'\xed\xa0\x80',[63,63,63]),
                (b'\xe0\x80\x80',[63,63,63]),(b'\xf0\x9f\x98\x80',[63]*4),(b'\xe6\x96',[63,63])]:
            with self.subTest(raw=raw):self.assertEqual(r.decode(raw),expected)
        for n,want in [(0,[]),(1,[63]),(2,[63,63]),(3,[ord('新')]),(4,[ord('新'),65])]:
            self.assertEqual(r.decode('新AB'.encode(),n),want)
        self.assertEqual(r.decode(b'A\0B'),[65])
        self.assertEqual(r.decode(('新'*4095).encode()),[ord('新')]*4095)
        self.assertEqual(r.decode(('新'*4096).encode()),[ord('新')]*4095)
        self.assertEqual(r.decode(b'A'*4095),[65]*4095)
        # Same PC-relative bytes remain valid after a synthetic ASLR image move.
        import pefile
        original=EXE.read_bytes();patched,_=patch_bytes(original);pe=pefile.PE(data=patched)
        relocated=0x150000000
        r.u.mem_map(relocated,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        r.u.mem_write(relocated,pe.get_memory_mapped_image());pe.close();r.base=relocated
        self.assertEqual(r.decode('新游戏'.encode()),list(map(ord,'新游戏')))
    @unittest.skipUnless(EXE.exists(),'user-supplied exact executable absent')
    def test_bmp_measure_and_draw(self):
        from test_binfont import fixture
        from binfont import BinFont
        font=BinFont(fixture());glyphs=dict(font.glyphs)
        cps=[ord(c) for c in '新游戏，']
        for cp in cps:glyphs[cp]=glyphs[65]
        data=font.write(glyphs,font.rgba,font.width,font.height)
        r=UTF8Replay(EXE);r.bind_font(data)
        self.assertEqual([r.advance(cp) for cp in cps],[3.0]*4)
        self.assertEqual(r.measure(cps),16)
        calls,x=r.draw_glyphs(cps)
        self.assertEqual(calls,[0.0,4.0,8.0,12.0])
        self.assertEqual(x,16.0)
    @unittest.skipUnless(EXE.exists(),'user-supplied exact executable absent')
    def test_baseline_difference(self):
        self.assertEqual(UTF8Replay(EXE,False).decode('新游戏'.encode()),list('新游戏'.encode()))

if __name__=='__main__':unittest.main()
