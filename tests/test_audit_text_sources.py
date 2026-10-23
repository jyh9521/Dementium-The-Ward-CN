import copy
from pathlib import Path
import struct
import sys
import unittest
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_text_sources import candidates, review, unwrap


def wrapped(data):
    packed=zlib.compress(data)
    size=12+len(packed)
    aligned=(size+3)//4*4
    return struct.pack('<3I',len(data),len(packed),aligned)+packed+b'\0'*(aligned-size)


class TextAuditTests(unittest.TestCase):
    def test_double_wrapper(self):
        data=b'alphabet_letter_a\0YesNoButton\0'
        result,layers=unwrap(wrapped(wrapped(data)))
        self.assertEqual(result,data)
        self.assertEqual(len(layers),2)

    def test_non_container_stays_unchanged(self):
        data=b'StartSection0 = 7fw_000'
        self.assertEqual(unwrap(data),(data,[]))

    def test_wrong_decoded_size_rejected(self):
        data=bytearray(wrapped(b'abc'))
        struct.pack_into('<I',data,0,4)
        with self.assertRaisesRegex(ValueError,'size mismatch'):unwrap(data)

    def test_candidate_offsets(self):
        self.assertEqual(candidates(b'\0\0Alpha\0Beta'),[dict(offset=2,text='Alpha'),dict(offset=8,text='Beta')])

    def test_review_detects_tokens_and_newlines(self):
        original=[dict(id='x',source='\x02Gold\x01\r\n\r\n',target='',status='untranslated')]
        r=copy.deepcopy(original);r[0]['target']='金\n'
        issues={x['issue'] for x in review(r,original)['structural_issues']}
        self.assertEqual(issues,{'token-order','newline-sequence','blank-line-position'})

    def test_review_valid_translation(self):
        original=[dict(id='x',source='\x02Gold\x01\r\n\r\n',target='',status='untranslated')]
        r=copy.deepcopy(original);r[0]['target']='\x02金\x01\r\n\r\n'
        self.assertEqual(review(r,original)['structural_issues'],[])

if __name__=='__main__':unittest.main()
