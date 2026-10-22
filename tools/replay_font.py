"""Instruction replay of the shipped font loader and relocation loop.

Only deterministic VFS/allocator/image/sprite boundaries are doubled. This does
not create a process from the PE and does not constitute rendered acceptance.
"""
import copy
import struct
from pathlib import Path
from unicorn.x86_const import (UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
    UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP)
from binfont import BinFont
from replay_text import Replay

SUPPORTED_SHA256 = "26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e"


class FontReplay(Replay):
    def __init__(self, exe, font_data):
        super().__init__(exe)
        if self.profile["executable_sha256"] != SUPPORTED_SHA256:
            raise ValueError("Font loader coordinates require the audited executable profile")
        self.profile=copy.deepcopy(self.profile)
        self.profile['rvas']['font_loader']=0xE9980
        self.u.mem_map(0x31040000,0x1C0000)
        self.raw=bytes(font_data)
        self.parsed=BinFont(self.raw)
        self.position=0
        self.alloc_next=0x31010000
        self.file_obj=0x31003000
        self.file_vtable=0x31003100
        self.file_hooks={0x31003200:'close',0x31003210:'read',0x31003220:'seek'}
        self.u.mem_write(self.file_obj,struct.pack('<Q',self.file_vtable))
        self.u.mem_write(self.file_vtable,struct.pack('<Q',0x31003200))
        self.u.mem_write(self.file_vtable+0x18,struct.pack('<Q',0x31003210))
        self.u.mem_write(self.file_vtable+0x30,struct.pack('<Q',0x31003220))
        self.u.mem_write(self.manager,struct.pack('<2Q',0x200000,self.obj))
        self.u.mem_write(self.base+self.profile['rvas']['memory_manager'],struct.pack('<Q',self.manager))
        self.sprites=[]
        self.image_calls=0
        self.relocation_calls=0
        self.reads=[]

    def alloc(self,size):
        pointer=(self.alloc_next+15)&~15
        self.alloc_next=pointer+max(size,16)
        if size<0 or self.alloc_next>=0x31200000:
            raise ValueError('Font replay allocation outside arena')
        self.u.mem_write(pointer,bytes(max(size,16)))
        return pointer

    def result(self,value=0):
        self.u.reg_write(UC_X86_REG_RAX,value)
        self.ret()

    def boundary(self,u,address,size,user):
        if address in self.file_hooks:
            operation=self.file_hooks[address]
            if operation=='seek':
                offset=u.reg_read(UC_X86_REG_RDX)&0xFFFFFFFF
                if offset&0x80000000:offset-=0x100000000
                origin=u.reg_read(UC_X86_REG_R8)
                if origin not in (0,1,2):raise ValueError('Unknown VFS seek origin')
                self.position=([0,self.position,len(self.raw)][origin])+offset
                if not 0<=self.position<=len(self.raw):raise ValueError('VFS seek out of bounds')
                self.result(self.position)
            elif operation=='read':
                count=u.reg_read(UC_X86_REG_R8)&0xFFFFFFFF
                target=u.reg_read(UC_X86_REG_RDX)
                if self.position+count>len(self.raw):raise ValueError('VFS read out of bounds')
                self.reads.append((self.position,count))
                u.mem_write(target,self.raw[self.position:self.position+count])
                self.position+=count
                self.result(count)
            else:self.result()
            return
        rv=address-self.base
        if rv==0xEA2A0:
            self.relocation_calls+=1  # Observe, but execute every original instruction.
        elif rv==0xF8840:
            pointer=u.reg_read(UC_X86_REG_RCX)
            path=bytes(u.mem_read(pointer,64)).split(b'\0')[0]
            if path!=b'fonts/d2font_12x15.binfont':raise ValueError('Unexpected VFS font path')
            self.result(self.file_obj)
            return
        elif rv in (0x3BF20,0xFF5B0):
            count=u.reg_read(UC_X86_REG_RDX if rv==0x3BF20 else UC_X86_REG_RCX)&0xFFFFFFFF
            self.result(self.alloc(count))
            return
        elif rv in (0x3BFE0,0xFFC30):
            self.result()
            return
        elif rv==0xEA1B0:
            pointer=u.reg_read(UC_X86_REG_RCX)
            expected=self.raw[self.parsed.texture_offset:self.parsed.texture_end]
            if bytes(u.mem_read(pointer,len(expected)))!=expected:
                raise ValueError('Native loader passed wrong image section')
            self.image_calls+=1
            self.result(0x31005000)
            return
        elif rv==0xEA420:
            rsp=u.reg_read(UC_X86_REG_RSP)
            values=[u.reg_read(r)&0xFFFFFFFF for r in (UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9)]
            height=struct.unpack('<I',u.mem_read(rsp+40,4))[0]
            pointer=self.alloc(0x80)
            self.sprites.append((pointer,tuple(values+[height])))
            self.result(pointer)
            return
        if not self.base<=address<self.base+0xF00000:
            raise ValueError('Unexpected font replay boundary '+hex(address))


def verify_loader(exe:Path,font_data:bytes)->dict:
    replay=FontReplay(exe,font_data)
    replay.run('font_loader',rcx=replay.obj)
    f=replay.parsed
    section=struct.unpack('<Q',replay.u.mem_read(replay.obj+0x810,8))[0]
    if not replay.relocation_calls==1 or replay.image_calls!=1:
        raise ValueError('Native font/image loader call count mismatch')
    if len(replay.sprites)!=256*len(f.pages):
        raise ValueError('Native sprite count mismatch')
    glyph_results={}
    for page_index,page in enumerate(f.pages):
        native_pointer=struct.unpack('<I',replay.u.mem_read(section+8+page*4,4))[0]
        if native_pointer!=section-replay.obj+f.pages[page]:
            raise ValueError('Native relocation pointer mismatch')
        for low in range(256):
            pointer,dimensions=replay.sprites[page_index*256+low]
            cp=page*256+low
            if cp not in f.glyphs:
                if dimensions!=(0,0,0,0):raise ValueError('Absent glyph produced rectangle')
                continue
            glyph=f.glyphs[cp]
            bearing=struct.unpack('<2f',replay.u.mem_read(pointer+0x58,8))
            expected=(glyph.x,glyph.y,glyph.width,glyph.height)
            if dimensions!=expected or bearing!=(glyph.bearing_x,glyph.bearing_y):
                raise ValueError('Native glyph dimensions/bearing mismatch')
            glyph_results[str(cp)]={'rectangle':list(dimensions),'bearing':list(bearing)}
    return dict(backend='Unicorn shipped font-loader and relocation instructions',
        native_loader='0x1400e9980',native_relocation='0x1400ea2a0',
        glyph_count=len(glyph_results),page_count=len(f.pages),
        sprite_count=len(replay.sprites),relocation_calls=replay.relocation_calls,
        image_boundary_calls=replay.image_calls,native_pointer_relocation=True,
        glyphs=glyph_results,vfs_reads=[list(r) for r in replay.reads],
        boundaries=['VFS open/seek/read/destruct','allocator/free','image/GPU','sprite construction'],
        game_launched=False,game_visual_acceptance=False)
