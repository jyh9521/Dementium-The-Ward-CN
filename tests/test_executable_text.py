import pathlib,sys,unittest,json,struct,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from executable_text import build_executable,apply_executable_patch,validate_hud_capacity
ROOT=pathlib.Path(__file__).resolve().parents[1]

def fixture():
    data=bytearray(0x400);data[:2]=b'MZ';struct.pack_into('<I',data,60,0x80)
    data[0x80:0x84]=b'PE\0\0';struct.pack_into('<H',data,0x86,1);struct.pack_into('<H',data,0x94,0xf0)
    base=0x80+24+0xf0;data[base:base+8]=b'.rdata\0\0'
    struct.pack_into('<II',data,base+16,0x100,0x300);struct.pack_into('<I',data,base+36,0x40000040)
    data[0x300:0x308]=b'New Game';return bytes(data)

def recipe(data):
    return dict(schema=1,encoding='utf-8',source_size=len(data),source_sha256=hashlib.sha256(data).hexdigest(),
        entries=[dict(id='fixture',offset=0x300,slot_size=16,source='New Game',target='新游戏')])

class ExecutableTextTests(unittest.TestCase):
    def test_roundtrip(self):
        data=fixture();out,patch=build_executable(data,recipe(data))
        self.assertEqual(out[0x300:0x30a],'新游戏'.encode()+b'\0')
        self.assertEqual(apply_executable_patch(data,patch),out)
        self.assertEqual(apply_executable_patch(out,patch,True),data)
    def test_guards(self):
        data=fixture();r=recipe(data)
        for change in [('slot_size',9),('offset',0x200),('source','Bad source')]:
            bad=json.loads(json.dumps(r));bad['entries'][0][change[0]]=change[1]
            with self.assertRaises(ValueError):build_executable(data,bad)
        with self.assertRaises(ValueError):build_executable(data[:-1],r)
        r['entries']*=2
        with self.assertRaises(ValueError):build_executable(data,r)
    def test_hud_capacity(self):
        row=dict(resource='loc/en/open.000',id='x',target='中'*85)
        self.assertEqual(validate_hud_capacity([row])[0]['utf8_bytes'],255)
        row['target']+='中'
        with self.assertRaises(ValueError):validate_hud_capacity([row])
        row['target']='a\0b'
        with self.assertRaises(ValueError):validate_hud_capacity([row])
    def test_translation_hud_capacity(self):
        rows=json.loads((ROOT/'locales/zh-CN/strings-ui-items.json').read_text(encoding='utf-8'))
        result=validate_hud_capacity(rows)
        self.assertEqual(len(result),12)
        self.assertLessEqual(max(x['utf8_bytes'] for x in result),255)
    def test_actual_sequential_chain(self):
        exe=pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\Dementium.exe')
        if not exe.exists():self.skipTest('user-supplied executable absent')
        from runtime_patch import patch_bytes,rollback_bytes
        raw=exe.read_bytes();runtime,rr=patch_bytes(raw)
        spec=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        out,patch=build_executable(runtime,spec)
        self.assertEqual(out,runtime)
        self.assertEqual(rollback_bytes(apply_executable_patch(out,patch,True),rr),raw)
    def test_no_unproven_actual_edits(self):
        r=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        self.assertEqual(r['entries'],[])

if __name__=='__main__':unittest.main()
