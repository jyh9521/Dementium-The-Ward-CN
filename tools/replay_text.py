"""Replay isolated target instructions in Unicorn; never launch the game.

PE mapping and deterministic call boundaries follow the upstream native_replay
approach. Coordinates and state are independently bound to this game's hash.
"""
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
    UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_XMM0)
from binfont import BinFont
from zar import filehash

ROOT=Path(__file__).resolve().parents[1]
AUDITED_SHA256='26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e'


class Replay:
    def __init__(self, exe, profile=None):
        self.profile=profile or json.loads((ROOT/'assets/native-analysis.json').read_text(encoding='utf-8'))
        if self.profile['executable_sha256']!=AUDITED_SHA256:
            raise ValueError('Native coordinates require the audited executable profile')
        if filehash(exe)!=self.profile['executable_sha256']:
            raise ValueError('Unsupported executable for instruction replay')
        pe=pefile.PE(str(exe),fast_load=True)
        self.base=pe.OPTIONAL_HEADER.ImageBase
        if self.base!=self.profile['image_base']:
            raise ValueError('Unexpected image base')
        self.u=Uc(UC_ARCH_X86,UC_MODE_64)
        self.u.mem_map(self.base,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        self.u.mem_write(self.base,pe.get_memory_mapped_image())
        pe.close()
        self.u.mem_map(0x20000000,0x20000)
        self.u.mem_map(0x31000000,0x40000)
        self.stack=0x2001fe08
        self.stop=0x20000000
        self.obj=0x31000000
        self.manager=0x31002000
        self.font=0x31004000
        self.buffer=0x31010000
        self.wide=0x31018000
        self.rows=None
        self.compiled=None
        self.u.hook_add(UC_HOOK_CODE,self.boundary)

    def ret(self):
        rsp=self.u.reg_read(UC_X86_REG_RSP)
        address=struct.unpack('<Q',self.u.mem_read(rsp,8))[0]
        self.u.reg_write(UC_X86_REG_RSP,rsp+8)
        self.u.reg_write(UC_X86_REG_RIP,address)

    def boundary(self,u,address,size,user):
        rv=address-self.base
        r=self.profile['rvas']
        if rv in (r['clear_table'],r['log']):
            self.ret()
        elif rv==r['read_table']:
            vector=u.reg_read(UC_X86_REG_RDX)
            raw=self.rows+b'\0'
            u.mem_write(self.buffer,raw)
            u.mem_write(vector,struct.pack('<3Q',self.buffer,self.buffer+len(raw),self.buffer+len(raw)))
            self.ret()
        elif rv==r['compile']:
            rsp=u.reg_read(UC_X86_REG_RSP)
            pointer=struct.unpack('<Q',u.mem_read(rsp+40,8))[0]
            count=struct.unpack('<I',u.mem_read(rsp+48,4))[0]
            self.compiled=list(struct.unpack('<'+'H'*count,u.mem_read(pointer,count*2)))
            self.ret()
        elif not self.base <= address < self.base+0xF00000:
            raise ValueError('Unexpected native replay boundary')

    def run(self,key,rcx=0,rdx=0,r8=0,r9=0,extra=()):
        self.u.reg_write(UC_X86_REG_RSP,self.stack)
        self.u.mem_write(self.stack,struct.pack('<Q',self.stop)+bytes(32))
        for i,value in enumerate(extra):
            self.u.mem_write(self.stack+40+i*8,struct.pack('<Q',value))
        for reg,value in [(UC_X86_REG_RCX,rcx),(UC_X86_REG_RDX,rdx),(UC_X86_REG_R8,r8),(UC_X86_REG_R9,r9)]:
            self.u.reg_write(reg,value)
        self.u.emu_start(self.base+self.profile['rvas'][key],self.stop,count=100000)
        if self.u.reg_read(UC_X86_REG_RIP)!=self.stop:
            raise ValueError('Replay instruction limit')
        return self.u.reg_read(UC_X86_REG_RAX)

    def table(self,raw):
        self.rows=raw
        self.u.mem_write(self.obj,bytes(0x100))
        count=self.run('table',rcx=self.obj,rdx=self.buffer)
        if not 1<=count<=25:raise ValueError('Unexpected table record count')
        result=[]
        for i in range(count):
            ptr=struct.unpack('<Q',self.u.mem_read(self.obj+i*8,8))[0]
            result.append(bytes(self.u.mem_read(ptr,len(raw)+1)).split(b'\0')[0])
        return result

    def widen(self,raw):
        if len(raw)>=4096 or b'\0' in raw:raise ValueError('Short-path replay only')
        self.u.mem_write(self.buffer,raw+b'\0')
        self.compiled=None
        self.run('widen',extra=(self.buffer,0xffffffff))
        if self.compiled is None:raise ValueError('Widen did not reach compiler')
        return self.compiled

    def bind_font(self,data):
        f=BinFont(data)
        section=bytearray(data[:f.texture_offset])
        for page in f.pages:
            at=8+page*4
            value=struct.unpack_from('<I',section,at)[0]+self.font-self.obj
            struct.pack_into('<I',section,at,value)
        self.u.mem_write(self.font,bytes(section))
        self.u.mem_write(self.manager,struct.pack('<2Q',0x40000,self.obj))
        self.u.mem_write(self.base+self.profile['rvas']['memory_manager'],struct.pack('<Q',self.manager))
        self.u.mem_write(self.obj+0x810,struct.pack('<Q',self.font))
        self.u.mem_write(self.obj+0x820,struct.pack('<f',1.0))

    def advance(self,codepoint):
        self.run('advance',rcx=self.obj,rdx=codepoint)
        return struct.unpack('<f',self.u.reg_read(UC_X86_REG_XMM0).to_bytes(16,'little')[:4])[0]

    def measure(self,codepoints):
        self.u.mem_write(self.wide,struct.pack('<'+'H'*(len(codepoints)+1),*codepoints,0))
        return self.run('measure',rcx=self.obj,rdx=self.wide,r8=len(codepoints))


def verify(exe, original_font, modified_font, original_table, modified_table, expected_slots, logical_source, logical_target):
    r=Replay(exe)
    original_rows=r.table(original_table)
    modified_rows=r.table(modified_table)
    if original_rows[0]!=logical_source.encode('latin-1') or modified_rows[0]!=bytes(expected_slots) or original_rows[1:]!=modified_rows[1:]:
        raise ValueError('Native table parsing mismatch')
    original_codes=r.widen(original_rows[0])
    alias_codes=r.widen(modified_rows[0])
    utf8_codes=r.widen(logical_target.encode('utf-8'))
    if original_codes!=list(logical_source.encode('latin-1')) or alias_codes!=list(expected_slots) or utf8_codes!=list(logical_target.encode('utf-8')):
        raise ValueError('Native byte-widening mismatch')
    r.bind_font(original_font)
    before=[r.advance(c) for c in expected_slots]
    r.bind_font(modified_font)
    after=[r.advance(c) for c in expected_slots]
    expected=[BinFont(modified_font).glyphs[c].advance for c in expected_slots]
    if after!=expected or any(x<=0 for x in after):raise ValueError('Native glyph lookup mismatch')
    width=r.measure(expected_slots)
    if width!=sum(expected)+len(expected_slots):raise ValueError('Native measured width mismatch')
    return dict(table_rows=len(original_rows),unchanged_other_rows=True,
        original_codepoints=original_codes,utf8_codepoints=utf8_codes,
        runtime_codepoints=alias_codes,original_advances=before,modified_advances=after,
        measured_width=width,backend='Unicorn isolated instructions; file I/O/compiler boundaries doubled',
        game_launched=False,game_visual_acceptance=False)
