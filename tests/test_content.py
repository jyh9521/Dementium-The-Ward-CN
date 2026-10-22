import copy
import io
from pathlib import Path
import struct
import sys
import tarfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content import Content, extract, import_text, verify_index
from zar import Zar
from test_zar import fixture


def tar_fixture(members=None):
    members = members or {'loc/en/GUI.tbl':b'New Game\r\n\r\nResume\n',
        'loc/en/examine.001':b'Title\r\n\x02item\x01\r\n',
        'loc/en/item.001':b'Item\nDetails', 'other':b'keep'}
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as t:
        for n,raw in members.items():
            info=tarfile.TarInfo(n);info.size=len(raw);info.mtime=17
            t.addfile(info,io.BytesIO(raw))
    return stream.getvalue()


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.raw=tar_fixture();self.c=Content(self.raw);self.r=extract(self.c)

    def test_noop(self):
        self.assertEqual(self.c.rebuild({}),self.raw)
        self.assertEqual(self.c.rebuild({n:self.c.read(n) for n in self.c.entries}),self.raw)
        self.assertEqual(import_text(self.c,self.r),{})

    def test_extract_all_types_and_blanks(self):
        self.assertEqual(len(self.r),4)
        self.assertEqual(self.r[1]['line'],2)
        self.assertEqual(self.r[2]['source'],'Title\r\n\x02item\x01\r\n')

    def test_offsets(self):
        for r in self.r:
            self.assertEqual(self.raw[r['tar_offset']:r['tar_offset']+r['source_bytes']],r['source'].encode('ascii'))

    def test_byte_encoding_is_explicit(self):
        c=Content(tar_fixture({'loc/en/credits.tbl':b'IN\xcaS'}))
        with self.assertRaises(UnicodeDecodeError):extract(c)
        self.assertEqual(extract(c,encoding='latin-1')[0]['source'],'INÊS')

    def test_unknown_chinese_encoding_rejected(self):
        self.r[0]['target']='新游戏'
        with self.assertRaises(UnicodeEncodeError):import_text(self.c,self.r)

    def test_growth_order_payloads_and_headers(self):
        after=Content(self.c.rebuild({'loc/en/GUI.tbl':b'A'*1200}))
        self.assertEqual(list(after.entries),list(self.c.entries))
        self.assertEqual(after.read('other'),b'keep')
        self.assertEqual(after.read('loc/en/GUI.tbl'),b'A'*1200)
        for n,e in self.c.entries.items():
            if n!='loc/en/GUI.tbl':
                f=after.entries[n]
                self.assertEqual(self.raw[e.offset:e.offset_data],after.data[f.offset:f.offset_data])

    def test_reimport_preserves_newlines_and_tokens(self):
        self.r[0]['target']='New Game [probe]'
        after=Content(self.c.rebuild(import_text(self.c,self.r)))
        self.assertEqual(after.read('loc/en/GUI.tbl'),b'New Game [probe]\r\n\r\nResume\n')

    def test_table_line_injection(self):
        self.r[0]['target']='New\nGame'
        with self.assertRaises(ValueError):import_text(self.c,self.r)

    def test_document_linebreak_and_controls(self):
        for target in ['Title\r\nitem\r\n','Title\n\x02item\x01\n','Title\r\n\x01item\x02\r\n']:
            r=copy.deepcopy(self.r);r[2]['target']=target
            with self.assertRaises(ValueError):import_text(self.c,r)

    def test_duplicate_missing_stale(self):
        bad=copy.deepcopy(self.r);bad[0]['offset']=123
        for rows in [bad,self.r[:-1],self.r+[self.r[0]]]:
            with self.assertRaises(ValueError):import_text(self.c,rows)

    def test_unsafe_names(self):
        for name in ['../bad','/absolute','c:/bad','a\\bad']:
            with self.assertRaises(ValueError):Content(tar_fixture({name:b'a'}))

    def test_invalid_checksum(self):
        raw=bytearray(self.raw);raw[1]^=1
        with self.assertRaises((ValueError,tarfile.TarError)):Content(bytes(raw))

    def test_truncation_and_bad_trailer(self):
        with self.assertRaises(ValueError):Content(self.raw[:-1])
        raw=bytearray(self.raw);raw[-1]=1
        with self.assertRaises(ValueError):Content(bytes(raw))

    def test_unknown_member(self):
        with self.assertRaises(ValueError):self.c.rebuild({'unknown':b'a'})

    def test_nested_dual_index_growth(self):
        index=struct.pack('<QIIQ',1,len(self.raw),0,0)+b'/content.tar\0'
        z=Zar(fixture({'CONTENT.TAR':self.raw,'~INDEX':index}))
        after=Zar(z.rebuild({'CONTENT.TAR':self.c.rebuild({'other':b'large'*600})}))
        verify_index(after,{})
        self.assertGreater(after.entries['CONTENT.TAR'].size,z.entries['CONTENT.TAR'].size)

    def test_external_and_mismatch_guard(self):
        index=struct.pack('<QIIQ',1,12,0,0)+b'/licenses.txt\0'
        z=Zar(fixture({'OTHER':b'A','~INDEX':index}))
        verify_index(z,{'LICENSES.TXT':12})
        with self.assertRaises(ValueError):verify_index(z,{})
        with self.assertRaises(ValueError):verify_index(z,{'LICENSES.TXT':13})


if __name__=='__main__':unittest.main()
