"""Exact-build F1 input restoration; keeps native secret-sequence gamepad gate.

Leaf bridges are RIP-relative, preserve native stack/unwind and add no imports.
Only the existing raw48 bit is generated; the request latch is deliberately not
set, so a key pressed on another screen cannot queue an activation request.
"""
import hashlib
import struct
import pefile
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from runtime_patch import ORIGINAL_SHA256, ORIGINAL_SIZE

FORMAT = 'ward-debug-menu-v1'
BASE = 0x140000000
KEY_RVA = 0xf8e50
GATE_RVA = 0xc0d80
RAW_RVA = 0x3fc3f8

def sha(data): return hashlib.sha256(data).hexdigest()

def original_guard(data):
    if len(data) != ORIGINAL_SIZE or sha(data) != ORIGINAL_SHA256:
        raise ValueError('Unsupported original executable identity')

def _asm(source, rva):
    return bytes(Ks(KS_ARCH_X86, KS_MODE_64).asm(source, BASE+rva)[0])

def build_debug_menu(data, original, catalog):
    from debug_menu_text import build_text_patch
    original_guard(original)
    pe=pefile.PE(data=data)
    source=pefile.PE(data=original)
    # Compose only after existing exact-build layers; preserve every original
    # .text byte except the previously audited UTF8 and audio HUD ranges.
    text=source.sections[0]
    a=text.PointerToRawData; b=a+text.SizeOfRawData
    allowed=[(0xea700,577),(0xbff10,14)]
    expected=bytearray(original[a:b]);actual=data[a:b]
    for rva,n in allowed:
        at=source.get_offset_from_rva(rva)-a
        expected[at:at+n]=actual[at:at+n]
    if bytes(expected)!=actual: raise ValueError('Unexpected pre-debug code changes')
    if pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size: raise ValueError('Unexpected signature')
    align=lambda v,n:(v+n-1)//n*n
    last=pe.sections[-1]
    if last.PointerToRawData+last.SizeOfRawData!=len(data):raise ValueError('Unexpected PE overlay')
    header=last.get_file_offset()+40
    if header+40>pe.OPTIONAL_HEADER.SizeOfHeaders or any(data[header:header+40]):
        raise ValueError('No empty PE section-header slot')
    if any(s.Name.rstrip(b'\0')==b'.locdbg' for s in pe.sections):raise ValueError('Debug layer already present')
    rva=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),pe.OPTIONAL_HEADER.SectionAlignment)
    raw=align(len(data),pe.OPTIONAL_HEADER.FileAlignment)
    key_old=bytes.fromhex('8b0526d42900')
    gate_old=bytes.fromhex('84c0742f88058cb63300eb27')
    out=bytearray(data)
    def replace(at,old,new):
        offset=pe.get_offset_from_rva(at)
        if len(old)!=len(new) or data[offset:offset+len(old)]!=old:raise ValueError('Debug hook byte guard mismatch')
        out[offset:offset+len(old)]=new
    # F1 has no prior binding in either stock layout. Non-F1 keys execute the
    # original first instruction and rejoin the unchanged keyboard callback.
    key_code=_asm(f'''
        cmp ecx,0x1c
        jne ordinary
        test dl,dl
        jz release
        bts qword ptr [rip],48
        ret
    release:
        btr qword ptr [rip],48
        ret
    ordinary:
        mov eax,dword ptr [rip]
        jmp {BASE+KEY_RVA+6}
    ''',rva)
    key_code=bytearray(key_code)
    for pattern,target in [(bytes.fromhex('480fba2d0000000030'),RAW_RVA),
                           (bytes.fromhex('480fba350000000030'),RAW_RVA),
                           (bytes.fromhex('8b0500000000'),0x39627c)]:
        at=key_code.index(pattern)
        disp=4 if len(pattern)==9 else 2
        struct.pack_into('<i',key_code,at+disp,target-(rva+at+len(pattern)))
    # The otherwise dead disabled/request=0 branch has exactly 12 bytes.
    # BT + short JNC + near JMP fits in place, inside the original C0D40 unwind range;
    # do not trampoline a non-leaf stack frame into an unregistered section.
    gate_code=_asm(f'bt dword ptr [rsi+4],18; jnc {BASE+0xc0db3}; jmp {BASE+0xc1017}',GATE_RVA)
    if len(gate_code)!=12:raise ValueError('Unexpected inline gate encoding')
    replace(KEY_RVA,key_old,b'\xe9'+struct.pack('<i',rva-KEY_RVA-5)+b'\x90')
    replace(GATE_RVA,gate_old,gate_code)
    pool_at=align(len(key_code),16)
    patched,pool,text_recipe=build_text_patch(bytes(out),catalog,rva+pool_at)
    payload=bytes(key_code)+b'\xcc'*(pool_at-len(key_code))+pool
    size=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment)
    out=bytearray(patched+bytes(raw-len(patched))+payload+bytes(size-len(payload)))
    struct.pack_into('<8sIIIIIIHHI',out,header,b'.locdbg',len(payload),rva,size,raw,0,0,0,0,0x60000020)
    struct.pack_into('<H',out,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(pe.sections)+1)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(rva+len(payload),pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+size)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),0)
    result=bytes(out);runs=[];start=None
    for i in range(len(data)):
        if data[i]!=result[i] and start is None:start=i
        elif data[i]==result[i] and start is not None:
            runs.append(dict(offset=start,before=data[start:i].hex(),after=result[start:i].hex()));start=None
    if start is not None:runs.append(dict(offset=start,before=data[start:].hex(),after=result[start:len(data)].hex()))
    recipe=dict(schema=1,format=FORMAT,original_sha256=sha(data),modified_sha256=sha(result),
        original_size=len(data),modified_size=len(result),runs=runs,append=result[len(data):].hex(),
        section_rva=rva,key_bridge_rva=rva,gate_bridge_rva=GATE_RVA,pool_rva=rva+pool_at,
        field='F1 raw48 rising-edge / C0D80 independent action18 / native L3+Y enabled gate preserved / localized native menu',text=text_recipe)
    pe.close();source.close()
    if rollback_debug(result,recipe)!=data:raise ValueError('Debug inverse mismatch')
    return result,recipe

def rollback_debug(data,recipe):
    if recipe.get('format')!=FORMAT or len(data)!=recipe['modified_size'] or sha(data)!=recipe['modified_sha256']:
        raise ValueError('Debug rollback identity mismatch')
    if data[recipe['original_size']:]!=bytes.fromhex(recipe['append']):raise ValueError('Debug append mismatch')
    out=bytearray(data[:recipe['original_size']])
    for run in recipe['runs']:
        at=run['offset'];old=bytes.fromhex(run['before']);new=bytes.fromhex(run['after'])
        if bytes(out[at:at+len(new)])!=new:raise ValueError('Debug rollback byte guard mismatch')
        out[at:at+len(old)]=old
    if sha(out)!=recipe['original_sha256']:raise ValueError('Debug inverse SHA mismatch')
    return bytes(out)
