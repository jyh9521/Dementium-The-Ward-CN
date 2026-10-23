"""Controlled instruction replay of exact original/patched file bytes; no EXE process."""
import struct
from replay_text import Replay
from runtime_patch import patch_bytes, FILE_OFFSET, LENGTH, RVA
from unicorn.x86_const import *

class UTF8Replay(Replay):
    def __init__(self,exe,patched=True):
        super().__init__(exe)
        if patched:
            image,_=patch_bytes(exe.read_bytes())
            self.u.mem_write(self.base+RVA,image[FILE_OFFSET:FILE_OFFSET+LENGTH])
        self.call=None

    def boundary(self,u,address,size,user):
        if address-self.base == 0x11fcf0:
            self.draw_calls.append(struct.unpack('<f',u.reg_read(UC_X86_REG_XMM2).to_bytes(16,'little')[:4])[0])
            self.ret();return
        if address-self.base == 0x11fec0:
            self.ret();return
        if address-self.base==self.profile['rvas']['compile']:
            rsp=u.reg_read(UC_X86_REG_RSP)
            pointer,count=struct.unpack('<QI',u.mem_read(rsp+40,12))
            self.call={'args':[u.reg_read(x) for x in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9)],
                'count':count,'stack_mod16':rsp%16,'terminated':bytes(u.mem_read(pointer+count*2,2))==b'\0\0'}
        super().boundary(u,address,size,user)

    def decode(self,raw,length=0xffffffff):
        self.u.mem_write(self.buffer,raw+b'\0')
        self.compiled=None;self.call=None
        sentinels={r:0x12340000+i for i,r in enumerate((UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,
            UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15))}
        for r,v in sentinels.items():self.u.reg_write(r,v)
        self.u.reg_write(UC_X86_REG_RSP,self.stack)
        self.u.mem_write(self.stack,struct.pack('<Q',self.stop)+bytes(32)+struct.pack('<QQ',self.buffer,length))
        args=[0x112233,0x223344,0x334455,0x445566]
        for reg,value in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):self.u.reg_write(reg,value)
        self.u.emu_start(self.base+RVA,self.stop,count=1000000)
        if self.u.reg_read(UC_X86_REG_RIP)!=self.stop:raise ValueError('Instruction limit')
        if any(self.u.reg_read(r)!=v for r,v in sentinels.items()):raise ValueError('Nonvolatile register corruption')
        if self.u.reg_read(UC_X86_REG_RSP)!=self.stack+8:raise ValueError('Stack unbalanced')
        if not self.call or self.call['args']!=args or self.call['stack_mod16']!=8 or not self.call['terminated']:
            raise ValueError('Compiler ABI mismatch')
        return self.compiled

    def draw_glyphs(self,codepoints):
        """Replay original draw dispatch with synthetic sprite/render boundaries."""
        obj=0x31008000;script=0x31020000;page=0x31025000
        slots=0x31026000;sprite=0x31028000;renderer=0x3102a000
        u=self.u
        u.mem_write(obj,bytes(0x100))
        u.mem_write(obj+0x28,struct.pack('<Q',self.obj))
        u.mem_write(obj+0x48,struct.pack('<Q',script))
        commands=[(cp<<8)|7 for cp in codepoints]+[2]
        u.mem_write(script,struct.pack('<II'+'I'*len(commands),0,len(commands),*commands))
        for cp in codepoints:
            # Distinct bitmap pages may share this synthetic sprite table.
            u.mem_write(self.obj+8+(cp>>8)*8,struct.pack('<Q',page))
            u.mem_write(page+8,struct.pack('<Q',slots))
            u.mem_write(slots+(cp&255)*8,struct.pack('<Q',sprite))
        u.mem_write(sprite,bytes(0x80))
        u.mem_write(self.base+0x3fc399,b'\x01')
        u.mem_write(self.base+0x3fc3a0,struct.pack('<Q',renderer))
        u.mem_write(renderer,bytes(0x100))
        u.reg_write(UC_X86_REG_XMM1,0);u.reg_write(UC_X86_REG_XMM2,0)
        self.draw_calls=[]
        self.profile['rvas']['draw']=0xeadc0
        self.run('draw',rcx=obj)
        return self.draw_calls,struct.unpack('<f',u.mem_read(obj+0x40,4))[0]
