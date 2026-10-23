"""Source-locked movie RGB layer upload: copied pixels, original media untouched.

The exact-build adapter selects actual VPX DAT leaf and decoded PTS, never a
requested cinema name or system time. No process is started by this module.
"""
from __future__ import annotations
import hashlib,math,struct
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from debug_menu import original_guard

BASE=0x140000000
HOOK=0xbdbca
UPLOAD=0x105d30
FORMAT='ward-movie-pixel-overlay-v1'
sha=lambda b:hashlib.sha256(b).hexdigest()
align=lambda x,a:(x+a-1)//a*a


def pack_frames(frames):
    """Canonical offset-only table; RGB triples preserve decoder alpha."""
    groups={};seen=set()
    for f in frames:
        name=f['stem']
        if (not isinstance(name,str) or name!=name.upper() or not name.endswith('.DAT') or
            '/' in name or '\\' in name or '..' in name or not name.isascii() or len(name)>95):
            raise ValueError('Invalid actual DAT leaf identity')
        if (f['width'],f['height'])!=(400,240):raise ValueError('Unsupported movie dimensions')
        start,end=f['start'],f['end']
        if not all(isinstance(x,(float,int)) and math.isfinite(x) for x in (start,end)) or not -1<=start<end<=86400:
            raise ValueError('Invalid movie PTS interval')
        key=(name,start,end)
        if key in seen:raise ValueError('Duplicate movie frame')
        seen.add(key);runs=[];last=0
        for offset,rgb in f['runs']:
            if (type(offset) is not int or offset%4 or offset<last or not isinstance(rgb,bytes) or
                not rgb or len(rgb)%3 or offset+len(rgb)//3*4>400*240*4 or
                offset//1600!=(offset+len(rgb)//3*4-1)//1600):raise ValueError('Invalid movie RGB run')
            runs.append((offset,rgb));last=offset+len(rgb)//3*4
        if not runs:continue
        groups.setdefault(name,[]).append((float(start),float(end),runs))
    if not groups:raise ValueError('Empty movie overlay')
    names=sorted(groups);payload=bytearray(16+112*len(names));payload[:16]=struct.pack('<4sIII',b'MOV1',len(names),400,240)
    intern={};stats=[]
    for i,name in enumerate(names):
        rows=sorted(groups[name]);previous=-2.
        for start,end,_ in rows:
            if start<previous:raise ValueError('Overlapping movie intervals')
            previous=end
        at=16+112*i;payload[at:at+len(name)]=name.encode('ascii')
        frame_at=len(payload);payload+=bytes(len(rows)*24)
        struct.pack_into('<IIII',payload,at+96,len(name),len(rows),frame_at,0)
        for j,(start,end,runs) in enumerate(rows):
            packed=b''.join(struct.pack('<II',offset,len(rgb)//3)+rgb for offset,rgb in runs)
            if packed not in intern:
                intern[packed]=len(payload);payload+=packed
            struct.pack_into('<ddII',payload,frame_at+j*24,start,end,intern[packed],len(runs))
        stats.append(dict(stem=name,frames=len(rows)))
    return bytes(payload),stats


def _code(rva,table_at,buffer_rva,bgr):
    # Push seven nonvolatile registers (56 bytes); 64-byte allocation keeps the
    # Win64 call alignment and reserves shadow space plus original arguments.
    src=f'''
    push rbx
    push rbp
    push rsi
    push rdi
    push r12
    push r13
    push r14
    sub rsp,0x40
    mov [rsp+0x20],rcx
    mov [rsp+0x28],rdx
    mov [rsp+0x30],r8
    lea rbp,[rip]
    mov rax,[rbp+{0xc15a90-rva}]
    test rax,rax
    jz upload
    lea r10,[rbp+{0x314f68-rva}]
    cmp [rax],r10
    jne upload
    mov rax,[rax+0x8150]
    test rax,rax
    jz upload
    lea r10,[rbp+{0x3150e8-rva}]
    cmp [rax],r10
    jne upload
    cmp byte ptr [rax+0x8190],0
    jne upload
    cmp dword ptr [rax+0x8a24],400
    jne upload
    cmp dword ptr [rax+0x8a28],240
    jne upload
    cmp r8d,1600
    jne upload
    cmp dword ptr [rbp+{0xc15b00-rva}],1600
    jne upload
    test rdx,rdx
    jz upload
    movsd xmm0,[rbp+{0xc15af0-rva}]
    subsd xmm0,[rax+0x40]
    ucomisd xmm0,xmm0
    jp upload
    mov r12,[rax+0x81e0]
    test r12,r12
    jz upload
    cmp r12,255
    ja upload
    lea r13,[rax+0x81d0]
    cmp qword ptr [rax+0x81e8],15
    jbe inline_name
    mov r13,[r13]
    test r13,r13
    jz upload
inline_name:
    xor ecx,ecx
    xor edx,edx
leaf:
    cmp rcx,r12
    jae leaf_done
    mov al,[r13+rcx]
    test al,al
    jz upload
    inc ecx
    cmp al,47
    je slash
    cmp al,92
    jne leaf
slash:
    mov edx,ecx
    jmp leaf
leaf_done:
    add r13,rdx
    sub r12,rdx
    lea r14,[rbp+{table_at}]
    mov ebx,[r14+4]
    lea rsi,[r14+16]
movie:
    test ebx,ebx
    jz upload
    cmp r12d,[rsi+96]
    jne next_movie
    xor edi,edi
compare_name:
    cmp edi,r12d
    jae found
    mov al,[r13+rdi]
    cmp al,97
    jb upper
    cmp al,122
    ja upper
    sub al,32
upper:
    cmp al,[rsi+rdi]
    jne next_movie
    inc edi
    jmp compare_name
next_movie:
    add rsi,112
    dec ebx
    jmp movie
found:
    mov ebx,[rsi+100]
    mov esi,[rsi+104]
    add rsi,r14
find_frame:
    test ebx,ebx
    jz upload
    ucomisd xmm0,[rsi]
    jb upload
    ucomisd xmm0,[rsi+8]
    jb frame
    add rsi,24
    dec ebx
    jmp find_frame
frame:
    lea rdi,[rbp+{buffer_rva-rva}]
    mov r12,rdi
    mov r13d,[rsi+16]
    add r13,r14
    mov ebx,[rsi+20]
    mov rsi,[rsp+0x28]
    mov ecx,48000
    rep movsq
run:
    test ebx,ebx
    jz copied
    mov edi,[r13]
    add rdi,r12
    mov ecx,[r13+4]
    add r13,8
pixel:
    mov al,[r13+{2 if bgr else 0}]
    mov [rdi],al
    mov al,[r13+1]
    mov [rdi+1],al
    mov al,[r13+{0 if bgr else 2}]
    mov [rdi+2],al
    add rdi,4
    add r13,3
    dec ecx
    jnz pixel
    dec ebx
    jmp run
copied:
    mov [rsp+0x28],r12
upload:
    mov rcx,[rsp+0x20]
    mov rdx,[rsp+0x28]
    mov r8,[rsp+0x30]
    call {BASE+UPLOAD}
    add rsp,0x40
    pop r14
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbp
    pop rbx
    ret
'''
    code=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(src,BASE+rva)[0])
    # RBP captures the next instruction, not function entry. Normalize exactly
    # once so all operands above use an ASLR-neutral function-relative origin.
    needle=bytes.fromhex('488d2d00000000');at=code.index(needle)
    struct.pack_into('<i',code,at+3,-(at+7))
    return bytes(code)


def build_movie_overlay(data,original,frames,*,expected_input_sha256,bgr=True):
    original_guard(original)
    if sha(data)!=expected_input_sha256:raise ValueError('Movie input chain identity mismatch')
    pe=pefile.PE(data=data);stock=pefile.PE(data=original)
    if pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size or pe.FILE_HEADER.PointerToSymbolTable:
        raise ValueError('Unexpected signed/symbol PE')
    if any(s.Name.rstrip(b'\0') in (b'.locmov',b'.movbuf') for s in pe.sections):raise ValueError('Movie layer already present')
    expected=stock.get_data(HOOK,5)
    if expected!=bytes.fromhex('e861810400') or pe.get_data(HOOK,5)!=expected:raise ValueError('Movie upload hook identity mismatch')
    # Pin the complete caller and upload function to original bytes. Other
    # localization layers live elsewhere and keep both instruction ranges intact.
    for at,n in ((0xbda50,0x220),(UPLOAD,0x100)):
        if pe.get_data(at,n)!=stock.get_data(at,n):raise ValueError('Movie neighborhood identity mismatch')
    table,stats=pack_frames(frames);file_align=pe.OPTIONAL_HEADER.FileAlignment;section_align=pe.OPTIONAL_HEADER.SectionAlignment
    old_headers=pe.OPTIONAL_HEADER.SizeOfHeaders
    new_headers=align(pe.sections[-1].get_file_offset()+40+80,file_align)
    shift=new_headers-old_headers
    if shift<0 or old_headers!=min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):raise ValueError('Unexpected PE header layout')
    out=bytearray(data[:old_headers]+bytes(shift)+data[old_headers:]);debug_changes=[]
    for s in pe.sections:
        if s.SizeOfRawData:struct.pack_into('<I',out,s.get_field_absolute_offset('PointerToRawData'),s.PointerToRawData+shift)
        if s.PointerToRelocations or s.PointerToLinenumbers:raise ValueError('Unsupported section auxiliary pointers')
    if hasattr(pe,'DIRECTORY_ENTRY_DEBUG'):
        for entry in pe.DIRECTORY_ENTRY_DEBUG:
            obj=entry.struct;off=obj.get_field_absolute_offset('PointerToRawData');value=obj.PointerToRawData
            if value:
                struct.pack_into('<I',out,off+shift,value+shift);debug_changes.append(dict(offset=off,before=value,after=value+shift))
    rva=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),section_align)
    table_at=0x1000
    # Build code once for size, then append table, unwind and copied pdata.
    code=_code(rva,table_at,0,bgr)
    if len(code)>table_at:raise ValueError('Movie hook code exceeds slot')
    payload=bytearray(code+bytes(table_at-len(code))+table)
    xdata=align(len(payload),4)
    # UWOP_ALLOC_SMALL(64), seven PUSH_NONVOL.
    # Actual pushes: RBX1 RBP2 RSI3 RDI4 R12=6 R13=8 R14=10, SUB ends14.
    unwind=bytes([1,14,8,0,14,0x72,10,0xe0,8,0xd0,6,0xc0,4,0x70,3,0x60,2,0x50,1,0x30])
    directory=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];pdata=pe.get_data(directory.VirtualAddress,directory.Size)
    if len(pdata)%12:raise ValueError('Malformed exception directory')
    pdata_at=xdata+len(unwind)
    payload+=bytes(xdata-len(payload))+unwind+pdata+struct.pack('<III',rva,rva+len(code),rva+xdata)
    buffer_rva=align(rva+len(payload),section_align)
    realcode=_code(rva,table_at,buffer_rva,bgr)
    if len(realcode)!=len(code):raise ValueError('Unstable code layout')
    payload[:len(code)]=realcode
    raw=align(len(out),file_align);rawsize=align(len(payload),file_align)
    out+=bytes(raw-len(out))+payload+bytes(rawsize-len(payload))
    header=pe.sections[-1].get_file_offset()+40
    struct.pack_into('<8sIIIIIIHHI',out,header,b'.locmov',len(payload),rva,rawsize,raw,0,0,0,0,0x60000020)
    struct.pack_into('<8sIIIIIIHHI',out,header+40,b'.movbuf',384000,buffer_rva,0,0,0,0,0,0,0xc0000080)
    struct.pack_into('<H',out,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(pe.sections)+2)
    for field,value in [('SizeOfHeaders',new_headers),('SizeOfImage',align(buffer_rva+384000,section_align)),('SizeOfCode',pe.OPTIONAL_HEADER.SizeOfCode+rawsize),('SizeOfUninitializedData',pe.OPTIONAL_HEADER.SizeOfUninitializedData+384000),('CheckSum',0)]:
        struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset(field),value)
    struct.pack_into('<II',out,directory.get_file_offset(),rva+pdata_at,len(pdata)+12)
    hookoff=pe.get_offset_from_rva(HOOK)+shift
    out[hookoff:hookoff+5]=b'\xe8'+struct.pack('<i',rva-HOOK-5)
    result=bytes(out)
    recipe=dict(schema=1,format=FORMAT,original_sha256=sha(data),modified_sha256=sha(result),original_size=len(data),modified_size=len(result),
                original_header=data[:old_headers].hex(),header_shift=shift,old_headers=old_headers,debug_changes=debug_changes,hook_offset=pe.get_offset_from_rva(HOOK),hook_before=expected.hex(),hook_after=result[hookoff:hookoff+5].hex(),
                section_rva=rva,code_size=len(code),table_rva=rva+table_at,buffer_rva=buffer_rva,unwind_rva=rva+xdata,exception_table_rva=rva+pdata_at,unwind=unwind.hex(),bgr=bgr,movies=stats,
                field='actual VPX DAT identity + decoded PTS sparse RGB upload / original media unchanged / decoder pixels read-only')
    pe.close();stock.close()
    if rollback_movie_overlay(result,recipe)!=data:raise ValueError('Movie inverse mismatch')
    return result,recipe


def rollback_movie_overlay(data,recipe):
    if recipe.get('format')!=FORMAT or len(data)!=recipe['modified_size'] or sha(data)!=recipe['modified_sha256']:raise ValueError('Movie rollback identity mismatch')
    old=recipe['old_headers'];shift=recipe['header_shift'];out=bytearray(bytes.fromhex(recipe['original_header'])+data[old+shift:recipe['original_size']+shift])
    at=recipe['hook_offset']
    if out[at:at+5]!=bytes.fromhex(recipe['hook_after']):raise ValueError('Movie rollback hook mismatch')
    out[at:at+5]=bytes.fromhex(recipe['hook_before'])
    for item in recipe['debug_changes']:
        if struct.unpack_from('<I',out,item['offset'])[0]!=item['after']:raise ValueError('Movie rollback debug mismatch')
        struct.pack_into('<I',out,item['offset'],item['before'])
    if sha(out)!=recipe['original_sha256']:raise ValueError('Movie inverse SHA mismatch')
    return bytes(out)


class MovieOverlayReplay:
    """Execute installed native hook; only original synchronous upload is doubled."""
    def __init__(self,data,recipe,base=BASE):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_RIP,UC_X86_REG_RSP,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8
        if sha(data)!=recipe['modified_sha256']:raise ValueError('Movie replay identity mismatch')
        rollback_movie_overlay(data,recipe)
        self.base=base;self.recipe=recipe;self.u=Uc(UC_ARCH_X86,UC_MODE_64)
        pe=pefile.PE(data=data);pe.relocate_image(base)
        self.u.mem_map(base,align(pe.OPTIONAL_HEADER.SizeOfImage,4096));self.u.mem_write(base,pe.get_memory_mapped_image());pe.close()
        self.heap=0x30000000;self.stack=0x28000000
        self.u.mem_map(self.heap,0x200000);self.u.mem_map(self.stack,0x20000)
        self.calls=[];self.unwind_checked=False
        def boundary(u,address,size,user):
            if address==base+recipe['section_rva']+14:
                sp=u.reg_read(UC_X86_REG_RSP)
                if sp!=self.entry_sp-8-56-64:raise ValueError('Movie unwind stack allocation mismatch')
                saved=struct.unpack('<7Q',u.mem_read(sp+64,56))
                if saved!=self.saved_values:raise ValueError('Movie unwind saved register mismatch')
                self.unwind_checked=True
            if address==base+UPLOAD:
                sp=u.reg_read(UC_X86_REG_RSP)
                if sp%16!=8:raise ValueError('Movie upload ABI alignment mismatch')
                pointer=u.reg_read(UC_X86_REG_RDX)
                self.calls.append(dict(pointer=pointer,texture=u.reg_read(UC_X86_REG_RCX),stride=u.reg_read(UC_X86_REG_R8),pixels=bytes(u.mem_read(pointer,384000))))
                u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        self.u.hook_add(UC_HOOK_CODE,boundary,begin=base+recipe['section_rva']+14,end=base+recipe['section_rva']+14)
        self.u.hook_add(UC_HOOK_CODE,boundary,begin=base+UPLOAD,end=base+UPLOAD)

    def run(self,pixels,stem='TEST.DAT',timestamp=0.,offset=0.,width=400,height=240,stride=1600,mode=0,media=True,vtable=True,requested='OTHER',longname=True,ownership=0,vpx_vtable=True,child=True,source_stride=None,original=False):
        from unicorn.x86_const import (UC_X86_REG_RSP,UC_X86_REG_RIP,UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8)
        if len(pixels)!=384000:raise ValueError('Replay pixel geometry mismatch')
        u=self.u;b=self.base;h=self.heap;mux=h;vpx=h+0x10000;source=h+0x40000;name=h+0x30000;cinema=h+0x20000
        u.mem_write(h,bytes(0x100000));u.mem_write(source,pixels)
        u.mem_write(b+0xc15a90,struct.pack('<Q',mux if media else 0));u.mem_write(mux,struct.pack('<Q',b+0x314f68 if vtable else 0));u.mem_write(mux+0x8150,struct.pack('<Q',vpx if child else 0))
        u.mem_write(vpx,struct.pack('<Q',b+0x3150e8 if vpx_vtable else 0));u.mem_write(vpx+0x8190,bytes([mode,ownership,0xa5,0x5a]))
        u.mem_write(vpx+0x8a24,struct.pack('<II',width,height));u.mem_write(vpx+0x40,struct.pack('<d',offset))
        encoded=stem.encode('ascii');u.mem_write(name,encoded+b'\0')
        if len(encoded)<=15 and not longname:u.mem_write(vpx+0x81d0,encoded+b'\0')
        else:u.mem_write(vpx+0x81d0,struct.pack('<Q',name))
        u.mem_write(vpx+0x81e0,struct.pack('<QQ',len(encoded),max(16,len(encoded)) if longname or len(encoded)>15 else 15))
        u.mem_write(b+0xc15af0,struct.pack('<d',timestamp+offset));u.mem_write(b+0xc15b00,struct.pack('<I',stride if source_stride is None else source_stride))
        u.mem_write(cinema+0xb4,requested.encode('ascii')+b'\0')
        regs=(UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15)
        values={r:0x123400+i for i,r in enumerate(regs)};values[UC_X86_REG_RBX]=cinema
        for r,value in values.items():u.reg_write(r,value)
        self.saved_values=tuple(values[r] for r in (UC_X86_REG_R14,UC_X86_REG_R13,UC_X86_REG_R12,UC_X86_REG_RDI,UC_X86_REG_RSI,UC_X86_REG_RBP,UC_X86_REG_RBX))
        self.entry_sp=self.stack+0x10000;u.reg_write(UC_X86_REG_RSP,self.entry_sp);u.reg_write(UC_X86_REG_RCX,h+0x25000);u.reg_write(UC_X86_REG_RDX,source);u.reg_write(UC_X86_REG_R8,stride)
        self.calls=[];self.unwind_checked=False
        installed=bytes(u.mem_read(b+HOOK,5))
        if original:u.mem_write(b+HOOK,bytes.fromhex(self.recipe['hook_before']))
        try:u.emu_start(b+HOOK,b+HOOK+5,count=5000000)
        finally:
            if original:u.mem_write(b+HOOK,installed)
        if u.reg_read(UC_X86_REG_RIP)!=b+HOOK+5 or u.reg_read(UC_X86_REG_RSP)!=self.entry_sp:raise ValueError('Movie continuation/stack mismatch')
        if (not original and not self.unwind_checked) or any(u.reg_read(r)!=v for r,v in values.items()):raise ValueError('Movie register/unwind preservation mismatch')
        if bytes(u.mem_read(source,384000))!=pixels:raise ValueError('Movie decoder source mutation')
        if len(self.calls)!=1:raise ValueError('Movie upload not called exactly once')
        return self.calls[0]


def verify_movie_overlay(original_path,patched_data,recipe,frames,*,output=None):
    """Native replay every compiled frame at two ASLR bases plus fail-closed cases.

    The source is synthetic BGRA with varying alpha; generation separately
    compares all source decoded RGB frames. Actual upload/GPU remains a boundary.
    """
    import json
    from pathlib import Path
    original_guard(Path(original_path).read_bytes())
    source=(bytes(range(256))*1500)  # 384000 exact, every pixel/alpha differs.
    results=[]
    for base in (BASE,0x180000000):
        replay=MovieOverlayReplay(patched_data,recipe,base);checks=0;digest=hashlib.sha256()
        for frame in frames:
            if not frame['runs']:continue
            expected=bytearray(source)
            for offset,rgb in frame['runs']:
                n=len(rgb)//3;stop=offset+n*4
                expected[offset:stop:4]=rgb[2::3] if recipe['bgr'] else rgb[0::3]
                expected[offset+1:stop:4]=rgb[1::3]
                expected[offset+2:stop:4]=rgb[0::3] if recipe['bgr'] else rgb[2::3]
            time=(frame['start']+frame['end'])/2
            got=replay.run(source,frame['stem'].lower(),time,requested='OTHER_MOVIE')
            if got['pixels']!=expected or got['pointer']!=base+recipe['buffer_rva'] or got['stride']!=1600:
                raise ValueError('Movie native frame/RGB/alpha mismatch: '+frame['stem'])
            digest.update(got['pixels']);checks+=1
        first=next(f for f in frames if f['runs']);time=(first['start']+first['end'])/2
        baseline=replay.run(source,first['stem'],time,original=True)
        if baseline['pixels']!=source or baseline['pointer']!=replay.heap+0x40000:raise ValueError('Original movie upload baseline mismatch')
        bad=[dict(stem='UNKNOWN.DAT',timestamp=time),dict(stem=first['stem'],timestamp=float('nan')),
             dict(stem=first['stem'],timestamp=-100),dict(stem=first['stem'],timestamp=100000),
             dict(stem=first['stem'],timestamp=time,media=False),dict(stem=first['stem'],timestamp=time,vtable=False),
             dict(stem=first['stem'],timestamp=time,width=401),dict(stem=first['stem'],timestamp=time,height=241),
             dict(stem=first['stem'],timestamp=time,stride=1604),dict(stem=first['stem'],timestamp=time,mode=1),
             dict(stem=first['stem'],timestamp=time,vpx_vtable=False),dict(stem=first['stem'],timestamp=time,child=False),
             dict(stem=first['stem'],timestamp=time,source_stride=1604),
             dict(stem='A'*256,timestamp=time),dict(stem='BAD\x00'+first['stem'],timestamp=time)]
        for case in bad:
            got=replay.run(source,**case)
            if got['pixels']!=source or got['pointer']!=replay.heap+0x40000:raise ValueError('Movie fail-closed replay painted unknown source')
        # Active-media name beats a newly requested cinema name; open DAT path
        # leaves are supported; loop-time offsets are removed before selection.
        for case in [dict(stem='rom:/movies/'+first['stem'].lower(),offset=0.),dict(stem=first['stem'],offset=4096.)]:
            got=replay.run(source,timestamp=time,requested='UNRELATED',**case)
            if got['pointer']!=base+recipe['buffer_rva']:raise ValueError('Movie identity/loop-time mismatch')
        results.append(dict(base=hex(base),native_frames=checks,fail_closed_cases=len(bad),lifecycle_cases=2,
                            output_sha256=digest.hexdigest(),original_baseline='unchanged decoder source passed directly',source_unchanged=True,alpha_preserved=True,unwind=True,nonvolatile=True,stack=True))
    if results[0]['output_sha256']!=results[1]['output_sha256']:raise ValueError('Movie ASLR pixels differ')
    report=dict(status='PASS',backend='Unicorn installed BDBCA call + native copied-pixel hook; original 105D30 upload doubled',results=results,
                all_compiled_frames_replayed=True,game_launched=False,steam_directory_modified=False,
                boundary='synthetic BGRA sources; upload driver/GPU and actual in-game playback remain manual acceptance')
    if output is not None:
        target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if json.loads(target.read_text(encoding='utf-8'))!=report:raise ValueError('Movie replay report reopening mismatch')
    return report
