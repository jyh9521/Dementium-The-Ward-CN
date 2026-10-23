import pathlib,sys,unittest,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from verify_locale_runtime import verify_locale_runtime,visible_line
from runtime_patch import patch_bytes
from binfont import BinFont,Glyph
EXE=pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\Dementium.exe')

class VerifyLocaleRuntimeTests(unittest.TestCase):
    def test_visible_controls(self):
        self.assertEqual(visible_line('\x03新\x01 游戏'),'新 游戏')
    @unittest.skipUnless(EXE.exists(),'user-supplied executable absent')
    def test_exact_native_decode_measure_and_loader(self):
        from test_binfont import fixture
        f=BinFont(fixture());glyphs=dict(f.glyphs)
        glyphs[32]=Glyph(0,0,0,0,2,0,0)
        original=f.write(glyphs,f.rgba,f.width,f.height)
        for c in '新游戏，':glyphs[ord(c)]=glyphs[65]
        full=f.write(glyphs,f.rgba,f.width,f.height)
        records=[{'id':'a'},{'id':'b'},{'id':'c'}]
        runtime={'a':'新游戏，','b':'A 新\r\n\x03游戏\x01','c':''}
        with tempfile.TemporaryDirectory() as td:
            patched=pathlib.Path(td)/'patched.exe';patched.write_bytes(patch_bytes(EXE.read_bytes())[0])
            report=verify_locale_runtime(EXE,patched,original,full,records,runtime)
            self.assertEqual(report['records'],3)
            self.assertTrue(report['visible_native_widths_match'])
            self.assertEqual(report['font_loaders']['modified']['page_count'],5)
            self.assertEqual(report['checks'][1]['native_line_widths'],[10,8])
            self.assertEqual(report['raw_control_spacing_differences'][0]['raw_native_width'],10)
            self.assertFalse(report['game_launched'])
            preserved=verify_locale_runtime(EXE,patched,original,full,[{'id':'fr'}],{'fr':'<< être civilisé >>\r\n'},
                verify_font_loader=False,measure_text=False,original_encoding='latin-1')
            self.assertTrue(preserved['original_decoded_streams_preserved'])
            self.assertIsNone(preserved['visible_native_widths_match'])
            self.assertEqual(preserved['checks'][0]['lines'],2)
            with self.assertRaises(ValueError):verify_locale_runtime(EXE,patched,original,full,records,{'a':'A'})
            patched.write_bytes(EXE.read_bytes())
            with self.assertRaises(ValueError):verify_locale_runtime(EXE,patched,original,full,records,runtime)

if __name__=='__main__':unittest.main()
