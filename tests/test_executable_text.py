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
        self.assertNotEqual(out,runtime)
        self.assertEqual(rollback_bytes(apply_executable_patch(out,patch,True),rr),raw)
    def test_display_modes_are_localized(self):
        r=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        mapping={e['source']:e['target'] for e in r['entries']}
        self.assertEqual(mapping,{'RETRO':'经典','RETRO CRT':'经典CRT',
                                  'HI-RES':'高清','HI-RES CRT':'高清CRT'})

    def test_native_display_mode_lookup(self):
        # Execute the original selector instructions, not a Python reimplementation.
        source=ROOT/'build/full/rollback-sample/Dementium.exe'
        if not source.exists():self.skipTest('user-supplied original fixture absent')
        import pefile
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_64
        from unicorn.x86_const import UC_X86_REG_RCX,UC_X86_REG_RAX,UC_X86_REG_RSP
        from runtime_patch import patch_bytes
        raw=source.read_bytes();runtime,_=patch_bytes(raw)
        recipe=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        modified,patch=build_executable(runtime,recipe)
        self.assertEqual(apply_executable_patch(modified,patch,True),runtime)
        selector=raw[0x2eca0:0x2ed1d]
        self.assertEqual(hashlib.sha256(selector).hexdigest(),
                         'd584320b91c4a2b2ed226b430428035744921d0db945eec8372b989010f40a42')
        # No instruction, pointer, relocation or non-ASCII label may change.
        changed={i for i,(a,b) in enumerate(zip(runtime,modified)) if a!=b}
        allowed={i for e in recipe['entries'] for i in range(e['offset'],e['offset']+e['slot_size'])}
        self.assertTrue(changed<=allowed)
        expected=['Debug','经典','经典CRT','高清','高清CRT']
        p=pefile.PE(data=modified)
        for base in (0x140000000,0x180000000):
            image=bytearray(p.get_memory_mapped_image())
            # Apply actual PE DIR64 relocation records for the chosen load base.
            for block in p.DIRECTORY_ENTRY_BASERELOC:
                for entry in block.entries:
                    if entry.type==10:
                        value=struct.unpack_from('<Q',image,entry.rva)[0]
                        struct.pack_into('<Q',image,entry.rva,value+base-p.OPTIONAL_HEADER.ImageBase)
            uc=Uc(UC_ARCH_X86,UC_MODE_64)
            uc.mem_map(base,(len(image)+4095)&~4095);uc.mem_write(base,bytes(image))
            stack=0x20000000;uc.mem_map(stack,0x2000)
            for language in range(5):
                for mode in range(5):
                    uc.mem_write(base+0x3fc3c0,struct.pack('<I',language))
                    uc.mem_write(stack+0x1000,struct.pack('<Q',base+0x1000))
                    uc.reg_write(UC_X86_REG_RSP,stack+0x1000)
                    uc.reg_write(UC_X86_REG_RCX,mode)
                    uc.emu_start(base+0x2f8a0,base+0x1000,count=40)
                    pointer=uc.reg_read(UC_X86_REG_RAX)
                    label=bytes(uc.mem_read(pointer,32)).split(b'\0',1)[0]
                    if language==0:self.assertEqual(label.decode('utf-8'),expected[mode])
                    # All languages keep the same original pointers/enum mapping.
                    table={0:0x304af0,1:0x304b40,2:0x304b18,3:0x304b68,4:0x304ac8}[language]
                    self.assertEqual(pointer,struct.unpack_from('<Q',image,table+mode*8)[0])

if __name__=='__main__':unittest.main()
