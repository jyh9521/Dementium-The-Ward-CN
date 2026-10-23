import pathlib,sys,unittest
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from binfont import Glyph
from locale_data import wrap_line,line_width,layout_record,advance,transcode_preserved_locales

class LocaleLayoutTests(unittest.TestCase):
    def setUp(self):
        chars='新游戏，。！病房（ ）ABC'+chr(0x3000)
        self.font=SimpleNamespace(glyphs={ord(c):Glyph(0,0,15,12,12,0,0) for c in chars})
        self.font.glyphs[32]=Glyph(0,0,1,1,4,0,0)
    def test_native_spacing_rules(self):
        self.assertEqual(line_width('新 A',self.font),30)
        self.assertEqual(advance(chr(0x3000),self.font),12)
        self.assertEqual(advance(chr(1),self.font),0)
    def test_wrap_keeps_punctuation_and_content(self):
        text='新游戏，病房。'
        lines=wrap_line(text,self.font,39)
        self.assertEqual(''.join(lines),text)
        self.assertTrue(all(line_width(s,self.font)<=39 for s in lines))
        self.assertTrue(all(not s.startswith(('，','。')) for s in lines))
    def test_reject_one_oversize_glyph(self):
        with self.assertRaises(ValueError):wrap_line('新',self.font,12)
    def test_document_layout_preserves_codes(self):
        row=dict(id='x',kind='document',resource='loc/en/examine.500',target='新游戏'+chr(1)+'\r\n病房')
        value,report=layout_record(row,self.font,[])
        self.assertEqual(value,row['target']);self.assertEqual(report['lines'],2)
    def test_image_examine_five_line_limit(self):
        row=dict(id='x',kind='document',resource='loc/en/examine.500',target='\n'.join(['新']*6))
        with self.assertRaisesRegex(ValueError,'height overflow'):
            layout_record(row,self.font,['TEXTURES/EXAMINE/EXAMINE500.PNG'])
    def test_long_document_wrap_and_table_not_wrap(self):
        row=dict(id='x',kind='document',resource='loc/en/item.000',target='新'*40)
        value,report=layout_record(row,self.font,[])
        self.assertEqual(value.replace('\n',''),row['target']);self.assertEqual(report['lines'],2)
        row['kind']='table'
        with self.assertRaisesRegex(ValueError,'Table width'):layout_record(row,self.font,[])
    def test_hud_fixed_bytes(self):
        row=dict(id='x',kind='document',resource='loc/en/open.001',target='新'*86)
        with self.assertRaisesRegex(ValueError,'255'):layout_record(row,self.font,[])
    def test_other_locale_encoding_without_translation(self):
        from content import Content,extract
        from test_content import tar_fixture
        c=Content(tar_fixture({'loc/en/a.tbl':b'New Game\r\n','loc/fr/a.tbl':b'Fran\xe7ais\r\n\x92keep\x01',
                               'loc/de/open.001':b'T\xfcr', 'other':b'untouched'}))
        changes,rows,runtime,report=transcode_preserved_locales(c)
        self.assertNotIn('loc/en/a.tbl',changes)
        after=Content(c.rebuild(changes))
        self.assertEqual(after.read('loc/fr/a.tbl').decode('utf8'),c.read('loc/fr/a.tbl').decode('latin1'))
        self.assertIn('\u0092',after.read('loc/fr/a.tbl').decode('utf8'))
        self.assertEqual(runtime,{r['id']:r['source'] for r in rows})
        self.assertTrue(all(not r['translated'] for r in report))
    def test_other_locale_hud_capacity(self):
        from content import Content
        from test_content import tar_fixture
        c=Content(tar_fixture({'loc/de/open.001':b'\xfc'*128}))
        with self.assertRaisesRegex(ValueError,'capacity'):transcode_preserved_locales(c)

if __name__=='__main__':unittest.main()
