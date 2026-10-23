import hashlib,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from verify_sample import verify

class SampleIdentityTests(unittest.TestCase):
    def test_localized_and_original_modes(self):
        sha=lambda b:hashlib.sha256(b).hexdigest()
        identity={'files':[dict(path='rom.zar',size=3,sha256=sha(b'old')),
                           dict(path='Dementium.exe',size=3,sha256=sha(b'exe'))]}
        report=dict(modified_sha256=sha(b'changed'),executable_sha256=sha(b'patched'))
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);(p/'rom.zar').write_bytes(b'changed');(p/'Dementium.exe').write_bytes(b'patched')
            self.assertEqual(verify(p,report,identity),2)
            with self.assertRaises(ValueError):verify(p,report,identity,True)
            (p/'rom.zar').write_bytes(b'old');(p/'Dementium.exe').write_bytes(b'exe')
            self.assertEqual(verify(p,report,identity,True),2)
            with self.assertRaises(ValueError):verify(p,report,identity)
    def test_one_byte_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);(p/'rom.zar').write_bytes(b'a');(p/'Dementium.exe').write_bytes(b'b')
            report=dict(modified_sha256='0'*64,executable_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'rom.zar'):verify(p,report,{'files':[]})

if __name__=='__main__':unittest.main()
