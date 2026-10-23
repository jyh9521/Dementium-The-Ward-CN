"""Locale-neutral speech cue resource and deterministic scheduler.

This module can generate a source-locked native HUD overlay in a copied PE.
The Steam installation remains read-only. Pure scheduler tests alone are not
native integration; controlled instruction replay and remaining GPU boundaries
are reported separately in docs/AUDIO_SUBTITLES.md.
"""
from __future__ import annotations
import hashlib,json,math,struct


def validate_catalog(catalog):
    if catalog.get('schema')!=1 or not isinstance(catalog.get('clips'),list):raise ValueError('Unsupported subtitle catalog')
    resources=set();ids=set()
    for clip in catalog['clips']:
        name=clip['resource']
        if not name or name.upper()!=name or name.startswith('/') or '..' in name or '\\' in name or name in resources:
            raise ValueError('Invalid/duplicate subtitle resource identity')
        resources.add(name)
        if len(clip['sha256'])!=64 or any(c not in '0123456789abcdef' for c in clip['sha256']):raise ValueError('Invalid audio SHA256')
        duration=clip['duration']
        if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:raise ValueError('Invalid clip duration')
        previous=0.
        for cue in clip['cues']:
            start,end=cue['start'],cue['end']
            if cue['id'] in ids or not 0<=start<end<=duration+0.001 or start<previous:raise ValueError('Invalid subtitle cue range/identity')
            ids.add(cue['id']);previous=end
            text=cue['target']
            if not text or '\0' in text or len(text)>4095 or any(ord(c)>0xffff or 0xd800<=ord(c)<=0xdfff for c in text):
                raise ValueError('Subtitle target must use bounded non-NUL BMP')
            if cue['status']!='translated-asr-consensus':raise ValueError('Unreviewed cue cannot become a runtime subtitle')
    return catalog


def build_resource(catalog):
    """Reproducible external UTF-8 resource; no game or locale-specific code."""
    validate_catalog(catalog)
    # Runtime resource contains only accepted speech, not uncued audit identities.
    clips=[dict(resource=c['resource'],sha256=c['sha256'],duration=c['duration'],
                cues=[{k:q[k] for k in ('id','start','end','target')} for q in c['cues']])
           for c in catalog['clips'] if c['cues']]
    payload=json.dumps(dict(schema=1,clips=clips),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return struct.pack('<4sI32s',b'SUB1',len(payload),hashlib.sha256(payload).digest())+payload


def read_resource(data):
    if len(data)<40:raise ValueError('Truncated subtitle resource')
    magic,size,digest=struct.unpack_from('<4sI32s',data);payload=data[40:]
    if magic!=b'SUB1' or size!=len(payload) or hashlib.sha256(payload).digest()!=digest:raise ValueError('Subtitle resource guard mismatch')
    result=json.loads(payload.decode('utf-8',errors='strict'))
    if result.get('schema')!=1:raise ValueError('Unsupported runtime subtitle resource')
    return result


def required_characters(catalog):
    validate_catalog(catalog)
    return sorted({ord(c) for clip in catalog['clips'] for q in clip['cues'] for c in q['target'] if ord(c)>=32})


class SubtitleState:
    """Reference event semantics. now is explicit monotonic seconds, not frame count."""
    def __init__(self,catalog):
        validate_catalog(catalog)
        self.clips={c['resource']:c for c in catalog['clips'] if c['cues']}
        self.active={};self.last_time=None;self.generation=0
    def _time(self,now):
        if not math.isfinite(now):raise ValueError('Invalid subtitle clock')
        if self.last_time is not None and now<self.last_time:raise ValueError('Subtitle clock moved backwards')
        self.last_time=now
    def play(self,channel,resource,source_sha256,now):
        self._time(now);self.active.pop(channel,None)
        clip=self.clips.get(resource)
        if clip is None:return False
        if source_sha256!=clip['sha256']:raise ValueError('Subtitle audio identity mismatch')
        self.active[channel]=(clip,now,self.generation);return True
    def stop(self,channel):self.active.pop(channel,None)
    def clear_scene(self):
        self.active.clear();self.generation+=1
    def visible(self,now):
        self._time(now);result=[];expired=[]
        for channel,(clip,start,generation) in self.active.items():
            elapsed=now-start
            if elapsed>=clip['duration'] or generation!=self.generation:expired.append(channel);continue
            for cue in clip['cues']:
                if cue['start']<=elapsed<cue['end']:
                    result.append(dict(channel=channel,resource=clip['resource'],id=cue['id'],target=cue['target'],elapsed=elapsed))
        for channel in expired:self.active.pop(channel,None)
        return sorted(result,key=lambda r:(r['resource'],r['id'],str(r['channel'])))

# Independently audited for this executable's FA990 switch. These are not locale data.
AUDITED_CUE_IDS={
 'SFX/EMERGENCY/EMERGENCY_01_MONOMIX_8HZ_8BIT.FLAC':0x100001f,
 'SFX/SINGING/SINGING_8HZ_8BIT.FLAC':0x1000028,
 **{'SFX/ENEMYBT/TALK%02dLO.FLAC'%i:0x100006f+i for i in range(1,6)}}
HUD_HOOK_RVA=0xbff10
HUD_RETURN_RVA=0xbff1e


def flac_streaminfo(data):
    if data[:4]!=b'fLaC' or len(data)<42 or data[4]&127 or int.from_bytes(data[5:8],'big')!=34:
        raise ValueError('Expected FLAC STREAMINFO')
    packed=int.from_bytes(data[18:26],'big')
    rate=packed>>44;channels=((packed>>41)&7)+1;samples=packed&((1<<36)-1)
    if not rate or not samples:raise ValueError('Invalid FLAC sample clock')
    return dict(sample_rate=rate,channels=channels,samples=samples,duration=samples/rate)


def native_cue_table(catalog,audio_members,font):
    """Bind speech to exact original FLAC and byte-bounded native sample clock."""
    from locale_data import wrap_line,line_width
    validate_catalog(catalog);rows=[]
    for clip in catalog['clips']:
        if not clip['cues']:continue
        name=clip['resource']
        if name not in AUDITED_CUE_IDS or name not in audio_members:
            raise ValueError('Speech resource lacks independently audited native cue mapping: '+name)
        raw=audio_members[name]
        if hashlib.sha256(raw).hexdigest()!=clip['sha256']:raise ValueError('Speech source identity mismatch')
        info=flac_streaminfo(raw)
        # Mixer folds its sample coordinate after 100000; longer clips need another clock binding.
        if info['channels']!=1 or info['samples']>=100000:raise ValueError('Unsupported native subtitle clock layout')
        if abs(info['duration']-clip['duration'])>0.001:raise ValueError('Subtitle duration/source differs')
        for q in clip['cues']:
            lines=[]
            for line in q['target'].split('\n'):lines.extend(wrap_line(line,font,400))
            if len(lines)>2:raise ValueError('Subtitle needs more than two native lines')
            text='\n'.join(lines)
            rows.append(dict(id=q['id'],resource=name,cue_id=AUDITED_CUE_IDS[name],
                sample_rate=info['sample_rate'],start=q['start'],end=q['end'],text=text,
                width=max(line_width(x,font) for x in lines),lines=len(lines)))
    return rows


def _native_code(section_rva,rows):
    from keystone import Ks,KS_ARCH_X86,KS_MODE_64
    base=0x140000000;table=0x1000
    g=lambda r:hex(r-section_rva) if r>=section_rva else '-'+hex(section_rva-r)
    code=f'''
    push rbx
    push rsi
    push rdi
    push rbp
    push r12
    push r13
    push r14
    push r15
    sub rsp,0xe8
    mov qword ptr [rsp+0xa0],rdx
    mov qword ptr [rsp+0xa8],r8
    mov qword ptr [rsp+0xb0],r9
    mov qword ptr [rsp+0xb8],r10
    mov qword ptr [rsp+0xc0],r11
    lea rbp,[rip]
    mov qword ptr [rsp+0xd0],0
    mov rax,qword ptr [rbp+{g(0x3fc468)}]
    test rax,rax
    jz finish
    cmp qword ptr [rax+8],rbx
    jne finish
    cmp byte ptr [rax+0x64],0
    jne finish
    cmp byte ptr [rax+0x68],0
    jne finish
    cmp byte ptr [rbp+{g(0x3fc417)}],0
    jne finish
    mov r12,qword ptr [rbp+{g(0xc14e20)}]
    test r12,r12
    jz finish
    mov rbx,qword ptr [r12]
    xor esi,esi
    xor edi,edi
node:
    cmp rbx,r12
    je finish
    test rbx,rbx
    jz finish
    inc esi
    cmp esi,1024
    ja finish
    mov r13,qword ptr [rbx+16]
    test r13,r13
    jz nextnode
    mov r15,qword ptr [r13+0xc0]
    test r15,r15
    jz nextnode
    cmp byte ptr [r15+0x30],0
    jne nextnode
    cmp byte ptr [r15+0x31],0
    je nextnode
    cmp byte ptr [r15+1],0
    jne nextnode
    xor ecx,ecx
pcm_slot:
    lea rax,[rbp+{g(0xc1a090)}]
    cmp qword ptr [rax+rcx*8],r15
    je pcm_present
    inc ecx
    cmp ecx,64
    jb pcm_slot
    jmp nextnode
pcm_present:
    movsd xmm0,qword ptr [r15+0x90]
    xorps xmm1,xmm1
    comisd xmm0,xmm1
    jp nextnode
    jbe gain
    cvtsi2sd xmm1,qword ptr [rbp+{g(0x6bb6f0)}]
    mov eax,48000
    cvtsi2sd xmm2,eax
    divsd xmm1,xmm2
    comisd xmm0,xmm1
    ja nextnode
gain:
    movss xmm0,dword ptr [r15+0x34]
    mulss xmm0,dword ptr [r15+0x40]
    mulss xmm0,dword ptr [r15+0x4c]
    mulss xmm0,dword ptr [rbp+{g(0x3a56d8)}]
    xorps xmm1,xmm1
    comiss xmm0,xmm1
    jp nextnode
    jbe nextnode
    mov eax,dword ptr [r15+0x80]
    and eax,0x7fffffff
    movd xmm1,eax
    mov eax,dword ptr [r15+0x84]
    and eax,0x7fffffff
    movd xmm2,eax
    addss xmm1,xmm2
    mov eax,dword ptr [r15+0x88]
    and eax,0x7fffffff
    movd xmm2,eax
    addss xmm1,xmm2
    mov eax,dword ptr [r15+0x8c]
    and eax,0x7fffffff
    movd xmm2,eax
    addss xmm1,xmm2
    mulss xmm0,xmm1
    xorps xmm1,xmm1
    comiss xmm0,xmm1
    jp nextnode
    jbe nextnode
    lea r14,[rbp+0x1000]
source_identity:
    mov eax,dword ptr [r13]
    cmp eax,dword ptr [r14]
    je source_found
    add r14,32
    lea rax,[rbp+{table+32*len(rows)}]
    cmp r14,rax
    jb source_identity
    jmp nextnode
source_found:
    mov rax,qword ptr [r15+8]
    test rax,rax
    jz nextnode
    mov eax,dword ptr [rax+0x28]
    cmp eax,dword ptr [r14+4]
    jne nextnode
    mov rax,r14
    sub rax,rbp
    sub eax,0x1000
    shr eax,5
    bt qword ptr [rsp+0xd0],rax
    jc nextnode
    mov dword ptr [rsp+0xd8],eax
    lea r14,[rbp+0x1000]
cue:
    mov eax,dword ptr [r13]
    cmp eax,dword ptr [r14]
    jne nextcue
    mov rax,qword ptr [r15+8]
    test rax,rax
    jz nextcue
    mov eax,dword ptr [rax+0x28]
    cmp eax,dword ptr [r14+4]
    jne nextcue
    cvtsi2sd xmm1,eax
    movsd xmm0,qword ptr [r15+0x60]
    divsd xmm0,xmm1
    comisd xmm0,qword ptr [r14+8]
    jb nextcue
    comisd xmm0,qword ptr [r14+16]
    jae nextcue
    mov eax,dword ptr [rsp+0xd8]
    bts qword ptr [rsp+0xd0],rax
    mov r8,qword ptr [rbp+{g(0x3fc468)}]
    test r8,r8
    jz nextcue
    mov r8,qword ptr [r8+0x20]
    test r8,r8
    jz nextcue
    xorps xmm0,xmm0
    movups xmmword ptr [rsp+0x40],xmm0
    movups xmmword ptr [rsp+0x50],xmm0
    movups xmmword ptr [rsp+0x60],xmm0
    movups xmmword ptr [rsp+0x70],xmm0
    movups xmmword ptr [rsp+0x80],xmm0
    movups xmmword ptr [rsp+0x90],xmm0
    mov dword ptr [rsp+0x7c],2
    mov eax,dword ptr [r14+24]
    add rax,rbp
    mov qword ptr [rsp+0x20],rax
    mov eax,dword ptr [r14+28]
    mov dword ptr [rsp+0x28],eax
    mov r9d,400
    lea rdx,[rbp+{g(0x3a83c0)}]
    lea rcx,[rsp+0x40]
    call 0x1400ea700
    lea rcx,[rsp+0x40]
    mov eax,0x43560000
    movd xmm1,eax
    imul eax,edi,26
    add eax,160
    cvtsi2ss xmm2,eax
    call 0x1400eadc0
    inc edi
    cmp edi,3
    jae finish
nextcue:
    add r14,32
    lea rax,[rbp+{table+32*len(rows)}]
    cmp r14,rax
    jb cue
nextnode:
    mov rbx,qword ptr [rbx]
    jmp node
finish:
    mov rdx,qword ptr [rsp+0xa0]
    mov r8,qword ptr [rsp+0xa8]
    mov r9,qword ptr [rsp+0xb0]
    mov r10,qword ptr [rsp+0xb8]
    mov r11,qword ptr [rsp+0xc0]
    mov rax,qword ptr [rip]
    lea rcx,[rip]
    add rsp,0xe8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rdi
    pop rsi
    pop rbx
    ret
'''
    if not rows or len(rows)>64:raise ValueError('Native subtitle table needs 1..64 rows')
    result=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(code,base+section_rva)[0])
    marker=result.index(bytes.fromhex('488d2d00000000'))
    struct.pack_into('<i',result,marker+3,-(marker+7))
    at=result.index(bytes.fromhex('488b0500000000'))
    struct.pack_into('<i',result,at+3,(0x3a5670-section_rva)-(at+7))
    at=result.index(bytes.fromhex('488d0d00000000'))
    struct.pack_into('<i',result,at+3,(0x3a5670-section_rva)-(at+7))
    if len(result)>table:raise ValueError('Native subtitle code exceeds reserved range')
    code_size=len(result)
    result.extend(bytes(table-len(result)))
    strings=bytearray();entries=bytearray()
    for row in rows:
        text=row['text'].encode('utf-8');offset=table+32*len(rows)+len(strings)
        entries.extend(struct.pack('<IIddII',row['cue_id'],row['sample_rate'],row['start'],row['end'],offset,len(text)))
        strings.extend(text+b'\0')
    return bytes(result+entries+strings),code_size


def build_native_overlay(runtime_exe,runtime_recipe,catalog,audio_members,font,literal_recipe=None):
    import pefile
    from runtime_patch import rollback_bytes,ORIGINAL_SHA256,patch_bytes
    data=bytes(runtime_exe)
    from executable_text import apply_executable_patch
    runtime_only=apply_executable_patch(data,literal_recipe,True) if literal_recipe is not None else data
    original=rollback_bytes(runtime_only,runtime_recipe)
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_SHA256 or patch_bytes(original)[0]!=runtime_only:
        raise ValueError('Native overlay requires exact audited runtime patch')
    pe=pefile.PE(data=data,fast_load=False);rows=native_cue_table(catalog,audio_members,font)
    if hashlib.sha256(pe.get_data(0xbfe00,0x200)).hexdigest()!='e20bb5539ce956169192cde63e489227e50d8bef7a74a95f683186f84b7617e4':
        raise ValueError('HUD native hook neighborhood identity mismatch')
    count=pe.FILE_HEADER.NumberOfSections;section_at=pe.sections[-1].get_file_offset()+40
    if section_at+40>min(s.PointerToRawData for s in pe.sections):raise ValueError('No PE section-header room')
    if any(data[section_at:section_at+40]):raise ValueError('Section header padding not empty')
    if any(s.Name.rstrip(b'\0')==b'.locsub' for s in pe.sections):raise ValueError('Subtitle section already exists')
    align=lambda x,a:(x+a-1)//a*a
    rva=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),pe.OPTIONAL_HEADER.SectionAlignment)
    raw_at=align(len(data),pe.OPTIONAL_HEADER.FileAlignment);payload,code_size=_native_code(rva,rows)
    xdata_at=align(len(payload),4)
    # Valid Win64 unwind for the new callable function: eight PUSH_NONVOL + ALLOC_LARGE(232).
    unwind=bytes([1,19,10,0,19,1])+struct.pack('<H',29)+bytes([12,0xf0,10,0xe0,8,0xd0,6,0xc0,4,0x50,3,0x70,2,0x60,1,0x30])
    directory=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
    original_pdata=pe.get_data(directory.VirtualAddress,directory.Size)
    if len(original_pdata)%12:raise ValueError('Malformed original exception table')
    pdata_at=xdata_at+len(unwind)
    payload+=bytes(xdata_at-len(payload))+unwind+original_pdata+struct.pack('<III',rva,rva+code_size,rva+xdata_at)
    raw_size=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment)
    out=bytearray(data+bytes(raw_at-len(data))+payload+bytes(raw_size-len(payload)))
    struct.pack_into('<8sIIIIIIHHI',out,section_at,b'.locsub\0',len(payload),rva,raw_size,raw_at,0,0,0,0,0x60000020)
    struct.pack_into('<H',out,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),count+1)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(rva+len(payload),pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+raw_size)
    struct.pack_into('<II',out,directory.get_file_offset(),rva+pdata_at,len(original_pdata)+12)
    at=pe.get_offset_from_rva(HUD_HOOK_RVA);old=data[at:at+14]
    expected=bytes.fromhex('488b0559572e00488d0d52572e00')
    if old!=expected:raise ValueError('HUD tail expected bytes mismatch '+old.hex())
    relative=(rva-(HUD_HOOK_RVA+5));out[at:at+14]=b'\xe8'+struct.pack('<i',relative)+b'\xe9'+struct.pack('<i',HUD_RETURN_RVA-(HUD_HOOK_RVA+10))+b'\x90'*4
    changes=[];start=None
    for i,(a,b) in enumerate(zip(data,out)):
        if a!=b and start is None:start=i
        if a==b and start is not None:changes.append(dict(offset=start,before=data[start:i].hex(),after=bytes(out[start:i]).hex()));start=None
    if start is not None:changes.append(dict(offset=start,before=data[start:].hex(),after=bytes(out[start:len(data)]).hex()))
    result=bytes(out);manifest=dict(schema=1,format='ward-audio-subtitle-overlay-v1',original_sha256=hashlib.sha256(data).hexdigest(),
        modified_sha256=hashlib.sha256(result).hexdigest(),original_size=len(data),modified_size=len(result),runs=changes,
        append=result[len(data):].hex(),section_rva=rva,section_raw_offset=raw_at,section_size=len(payload),
        hook_rva=HUD_HOOK_RVA,hook_return_rva=HUD_RETURN_RVA,code_size=code_size,unwind_rva=rva+xdata_at,exception_table_rva=rva+pdata_at,rows=rows)
    pe.close();return result,manifest


def rollback_overlay(data,manifest):
    if len(data)!=manifest['modified_size'] or hashlib.sha256(data).hexdigest()!=manifest['modified_sha256']:
        raise ValueError('Native overlay rollback identity mismatch')
    out=bytearray(data[:manifest['original_size']])
    for run in manifest['runs']:
        at=run['offset'];new=bytes.fromhex(run['after']);old=bytes.fromhex(run['before'])
        if bytes(out[at:at+len(new)])!=new:raise ValueError('Native overlay byte mismatch')
        out[at:at+len(old)]=old
    result=bytes(out)
    if hashlib.sha256(result).hexdigest()!=manifest['original_sha256']:raise ValueError('Native overlay rollback hash mismatch')
    return result

class NativeOverlayReplay:
    """Execute the installed HUD detour, scanner and patched decoder in Unicorn.

    By default compiler and draw submission are explicit call boundaries. With
    font_data, the actual wide compiler and native font measurement execute;
    only draw submission remains doubled. No game process or GPU is created.
    """
    def __init__(self,original_exe,patched_data,manifest,image_base=None,font_data=None):
        from replay_utf8 import UTF8Replay
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_RSP
        import pefile
        self.manifest=manifest;self.calls=[];self.pending=None
        if hashlib.sha256(patched_data).hexdigest()!=manifest['modified_sha256']:
            raise ValueError('Replay overlay identity mismatch')
        rollback_overlay(patched_data,manifest)
        from unicorn.x86_const import UC_X86_REG_RSP
        class ActualCompilerReplay(UTF8Replay):
            def boundary(self,u,address,size,user):
                if address in (0x3300e000,0x3300e010):
                    from unicorn.x86_const import UC_X86_REG_RAX
                    u.reg_write(UC_X86_REG_RAX,int(address==0x3300e010));self.ret();return
                if font_data is not None and address-self.base==0xea950:
                    sp=u.reg_read(UC_X86_REG_RSP);pointer,count=struct.unpack('<QI',u.mem_read(sp+40,12))
                    self.compiled=list(struct.unpack('<'+'H'*count,u.mem_read(pointer,count*2)))
                    self.compiler_calls+=1
                    return  # Execute every actual EA950 instruction; no compile boundary double.
                if address-self.base in (0xff5b0,0xffc30,0x3bf20,0x3bfe0):
                    self.heap_calls+=1
                    raise ValueError('Unexpected text heap operation in native overlay replay')
                super().boundary(u,address,size,user)
        self.r=ActualCompilerReplay(original_exe)
        self.r.compiler_calls=0;self.r.heap_calls=0;self.actual_compile=font_data is not None
        self.u=self.r.u;self.base=self.r.base
        original_pe=pefile.PE(str(original_exe),fast_load=True);pe=pefile.PE(data=patched_data,fast_load=True)
        old=(original_pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095
        new=(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095
        if image_base is not None and image_base!=self.base:
            self.base=image_base;self.r.base=image_base
            pe.relocate_image(image_base)
            self.u.mem_map(self.base,new)
        elif new>old:self.u.mem_map(self.base+old,new-old)
        self.u.mem_write(self.base,pe.get_memory_mapped_image());original_pe.close();pe.close()
        if font_data is not None:
            from binfont import BinFont
            self.u.mem_map(0x32000000,0x800000);self.r.font=0x32000000;self.r.bind_font(font_data)
            font=BinFont(font_data)
            self.u.mem_write(self.r.obj+0x824,struct.pack('<f',font.glyphs[32].advance if 32 in font.glyphs else 0))
        self.u.mem_map(0x33000000,0x20000)
        self.u.hook_add(UC_HOOK_CODE,self.boundary)
    def boundary(self,u,address,size,user):
        from unicorn.x86_const import UC_X86_REG_RCX,UC_X86_REG_RSP,UC_X86_REG_XMM1,UC_X86_REG_XMM2
        rv=address-self.base
        if rv==self.manifest['section_rva']+19:
            # Unwind ALLOC_LARGE(232), then 8 PUSH_NONVOL, then return address.
            sp=u.reg_read(UC_X86_REG_RSP)
            self.unwind_verified=(sp+304==self.entry_stack and
                struct.unpack('<Q',u.mem_read(sp+296,8))[0]==self.base+HUD_HOOK_RVA+5 and
                struct.unpack('<8Q',u.mem_read(sp+232,64))==tuple(self.expected_unwind))
            if not self.unwind_verified:raise ValueError('Native unwind frame does not match runtime stack')
        if rv==0xea950:
            # The base Replay hook already captured the original compiler ABI.
            self.pending=''.join(map(chr,self.r.compiled))
        elif rv==0xeadc0:
            x=struct.unpack('<f',u.reg_read(UC_X86_REG_XMM1).to_bytes(16,'little')[:4])[0]
            y=struct.unpack('<f',u.reg_read(UC_X86_REG_XMM2).to_bytes(16,'little')[:4])[0]
            call=dict(text=self.pending,x=x,y=y,stack_mod16=u.reg_read(UC_X86_REG_RSP)%16)
            if self.actual_compile:
                obj=u.reg_read(UC_X86_REG_RCX);script=struct.unpack('<Q',u.mem_read(obj+0x48,8))[0]
                call['script_pointer']=script-self.base
                call['script_commands']=struct.unpack('<I',u.mem_read(script+4,4))[0]
            self.calls.append(call)
            self.r.ret()
    def mixer_coefficients(self,event,*,muted=False,master_gain=1.0):
        """Original mixer master and PCM matrix instructions; not a gain formula double."""
        from unicorn.x86_const import (UC_X86_REG_R15,UC_X86_REG_RBX,UC_X86_REG_XMM7,
            UC_X86_REG_XMM8,UC_X86_REG_XMM9,UC_X86_REG_XMM10)
        u=self.u;channel=0x33001000
        u.mem_write(channel,bytes(0xc0))
        for offset,key in [(0x34,'volume'),(0x40,'gain'),(0x4c,'envelope'),
                           (0x80,'left'),(0x84,'cross_left'),(0x88,'cross_right'),(0x8c,'right')]:
            u.mem_write(channel+offset,struct.pack('<f',event.get(key,0. if key.startswith('cross') else 1.)))
        u.mem_write(self.base+0x3fc417,bytes([int(muted)]))
        u.mem_write(self.base+0x3a56d8,struct.pack('<f',master_gain))
        u.reg_write(UC_X86_REG_R15,0)
        u.emu_start(self.base+0x10970b,self.base+0x109731,count=30)
        u.reg_write(UC_X86_REG_RBX,channel)
        u.emu_start(self.base+0x109c66,self.base+0x109ca4,count=30)
        return [struct.unpack('<f',u.reg_read(reg).to_bytes(16,'little')[:4])[0]*event.get('envelope',1.)
                for reg in (UC_X86_REG_XMM8,UC_X86_REG_XMM9,UC_X86_REG_XMM10,UC_X86_REG_XMM7)]

    def render(self,events,*,modal=False,muted=False,master_gain=1.0):
        """events: cue_id/sample_rate/position(seconds)/paused/stopped/playing."""
        from unicorn.x86_const import (UC_X86_REG_RSP,UC_X86_REG_RIP,UC_X86_REG_RAX,UC_X86_REG_RCX,
            UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,
            UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15,UC_X86_REG_RDX,UC_X86_REG_R8,
            UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11)
        if len(events)>64:raise ValueError('Replay fixture exceeds native PCM table')
        self.calls=[];self.pending=None;u=self.u;sentinel=0x33000000;root=0x33000100
        u.mem_write(0x33000000,bytes(0x20000));nodes=[]
        u.mem_write(self.base+0xc1a090,bytes(64*8))
        u.mem_write(self.base+0x6bb6f0,struct.pack('<Q',48000))
        for i,event in enumerate(events):
            node=0x33001000+i*0x400;record=node+0x40;channel=node+0x140;buffer=node+0x240;nodes.append(node)
            u.mem_write(node+16,struct.pack('<Q',record));u.mem_write(record,struct.pack('<I',event['cue_id']))
            u.mem_write(record+0xc0,struct.pack('<Q',channel));u.mem_write(channel+8,struct.pack('<Q',buffer))
            u.mem_write(channel+1,bytes([int(event.get('paused',False))]))
            if event.get('mixer_active',True):u.mem_write(self.base+0xc1a090+i*8,struct.pack('<Q',channel))
            u.mem_write(channel+0x90,struct.pack('<d',event.get('scheduled',0.)))
            u.mem_write(channel+0x30,bytes([int(event.get('stopped',False)),int(event.get('playing',True))]))
            rate=event.get('sample_rate',11025);u.mem_write(buffer+0x28,struct.pack('<I',rate))
            u.mem_write(channel+0x60,struct.pack('<d',event['position']*rate))
            for offset,key in [(0x34,'volume'),(0x40,'gain'),(0x4c,'envelope'),(0x80,'left'),(0x8c,'right')]:
                u.mem_write(channel+offset,struct.pack('<f',event.get(key,1.0)))
        chain=[sentinel]+nodes
        for i,node in enumerate(chain):u.mem_write(node,struct.pack('<2Q',chain[(i+1)%len(chain)],chain[(i-1)%len(chain)]))
        u.mem_write(self.base+0xc14e20,struct.pack('<Q',sentinel))
        u.mem_write(self.base+0x3fc468,struct.pack('<Q',root));u.mem_write(root+0x20,struct.pack('<Q',self.r.obj))
        screen=root+0x15a8
        u.mem_write(root+8,struct.pack('<Q',screen))
        if modal:
            target=root+0x2b78;vtable=0x3300d000
            u.mem_write(screen,struct.pack('<Q',vtable));u.mem_write(target,struct.pack('<Q',vtable))
            for offset in (8,0x10,0x50,0x58):
                u.mem_write(vtable+offset,struct.pack('<Q',0x3300e010 if offset==0x58 else 0x3300e000))
            self.r.profile['rvas']['switch_overlay']=0xbbba0
            self.r.run('switch_overlay',rcx=root,rdx=target)
            if struct.unpack('<Q',u.mem_read(root+8,8))[0]!=target or u.mem_read(root+0x68,1)!=b'\x01':
                raise ValueError('Original modal UI transition did not select the overlay screen')
            if modal=='closed':
                self.r.run('switch_overlay',rcx=root,rdx=screen)
                if struct.unpack('<Q',u.mem_read(root+8,8))[0]!=screen or u.mem_read(root+0x68,1)!=b'\x00':
                    raise ValueError('Original modal return did not clear underlay state')
        u.mem_write(self.base+0x3fc417,bytes([int(muted)]))
        u.mem_write(self.base+0x3a56d8,struct.pack('<f',master_gain))
        regs=(UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,
            UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15,UC_X86_REG_RDX,UC_X86_REG_R8,
            UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11)
        sentinels={reg:0x123400+i for i,reg in enumerate(regs)}
        sentinels[UC_X86_REG_RBX]=screen
        for reg,value in sentinels.items():u.reg_write(reg,value)
        self.expected_unwind=[sentinels[x] for x in (UC_X86_REG_R15,UC_X86_REG_R14,UC_X86_REG_R13,UC_X86_REG_R12,UC_X86_REG_RBP,UC_X86_REG_RDI,UC_X86_REG_RSI,UC_X86_REG_RBX)]
        stack=0x2001fe00;self.entry_stack=stack;self.unwind_verified=False;u.reg_write(UC_X86_REG_RSP,stack)
        u.emu_start(self.base+HUD_HOOK_RVA,self.base+HUD_RETURN_RVA,count=2000000)
        if u.reg_read(UC_X86_REG_RIP)!=self.base+HUD_RETURN_RVA or u.reg_read(UC_X86_REG_RSP)!=stack:
            raise ValueError('Native overlay HUD continuation/stack mismatch')
        if any(u.reg_read(reg)!=value for reg,value in sentinels.items()):raise ValueError('Native overlay register corruption')
        if not self.unwind_verified:raise ValueError('Native unwind prologue not reached')
        if any(call['stack_mod16']!=8 for call in self.calls):raise ValueError('Native overlay draw ABI alignment')
        return self.calls

def verify_native_dispatch(exe,catalog):
    """Execute this original game's FA990 switch for every translated sound ID."""
    from replay_text import Replay
    from unicorn.x86_const import UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8
    class DispatchReplay(Replay):
        def __init__(self,path):
            super().__init__(path);self.profile['rvas']['dispatch']=0xfa990;self.capture=None
        def boundary(self,u,address,size,user):
            if address-self.base==0xfda70:
                pointer=u.reg_read(UC_X86_REG_RDX)
                resource=bytes(u.mem_read(pointer,256)).split(b'\0')[0].decode('ascii')
                self.capture=dict(resource='SFX/'+resource.upper(),loop=bool(u.reg_read(UC_X86_REG_R8)&255),
                    object=u.reg_read(UC_X86_REG_RCX))
                self.ret();return
            super().boundary(u,address,size,user)
    replay=DispatchReplay(exe);rows=[]
    for clip in catalog['clips']:
        if not clip['cues']:continue
        name=clip['resource']
        if name not in AUDITED_CUE_IDS:raise ValueError('Unaudited sound ID')
        cue=AUDITED_CUE_IDS[name];replay.capture=None;replay.u.mem_write(replay.obj,bytes(0x100))
        replay.run('dispatch',rcx=replay.obj,rdx=cue)
        if not replay.capture or replay.capture['resource']!=name or replay.capture['object']!=replay.obj:
            raise ValueError('Original sound cue switch disagrees with subtitle mapping')
        if struct.unpack('<I',replay.u.mem_read(replay.obj,4))[0]!=cue:raise ValueError('Original sound record ID not written')
        rows.append(dict(resource=name,cue_id=cue,loop=replay.capture['loop']))
    return dict(backend='Unicorn original FA990 dispatch instructions; FDA70 filename construction boundary',
        verified=rows,game_launched=False)

def verify_overlay_font(exe,font_data,rows):
    """Original loader, measure and sprite-dispatch instructions on the full font."""
    from replay_font import FontReplay
    from binfont import BinFont
    from locale_data import line_width,advance
    from unicorn.x86_const import UC_X86_REG_XMM1,UC_X86_REG_XMM2
    class GlyphReplay(FontReplay):
        def boundary(self,u,address,size,user):
            rv=address-self.base
            if rv==0x11fcf0:
                x=struct.unpack('<f',u.reg_read(UC_X86_REG_XMM2).to_bytes(16,'little')[:4])[0]
                # y is XMM3; sprite and renderer are explicit GPU boundary doubles.
                self.draw_x.append(x);self.result();return
            if rv==0x11fec0:
                self.result();return
            super().boundary(u,address,size,user)
    r=GlyphReplay(exe,font_data);r.run('font_loader',rcx=r.obj)
    from unicorn import UC_HOOK_MEM_INVALID
    from unicorn.x86_const import UC_X86_REG_RIP
    def invalid(u,access,address,size,value,user):
        raise ValueError('Font draw replay unmapped '+hex(address)+' at '+hex(u.reg_read(UC_X86_REG_RIP)))
    r.u.hook_add(UC_HOOK_MEM_INVALID,invalid)
    # EA420 is a boundary double; reproduce its pointer-vector side effect so
    # the original draw dispatcher can consume the already verified sprite order.
    for page_index,page in enumerate(r.parsed.pages):
        page_obj=struct.unpack('<Q',r.u.mem_read(r.obj+8+page*8,8))[0]
        pointers=[r.sprites[page_index*256+low][0] for low in range(256)]
        vector=r.alloc(2048);r.u.mem_write(vector,struct.pack('<256Q',*pointers))
        r.u.mem_write(page_obj+8,struct.pack('<Q',vector))
        for low,pointer in enumerate(pointers):
            dimensions=r.sprites[page_index*256+low][1]
            r.u.mem_write(pointer+8,struct.pack('<2f',float(dimensions[2]),float(dimensions[3])))
    r.wide=r.alloc(8192);obj=r.alloc(0x60);script=r.alloc(0x1000);renderer=r.alloc(0x100)
    font=BinFont(font_data);r.profile['rvas']['draw']=0xeadc0;checked=[]
    for row in rows:
        for line_index,line in enumerate(row['text'].split('\n')):
            cps=list(map(ord,line));expected=line_width(line,font)
            measured=r.measure(cps)
            if measured!=expected:raise ValueError('Native subtitle width mismatch')
            commands=[cp<<8|7 for cp in cps]+[2]
            r.u.mem_write(script,struct.pack('<II'+'I'*len(commands),0,len(commands),*commands))
            r.u.mem_write(obj,bytes(0x60));r.u.mem_write(obj+0x28,struct.pack('<Q',r.obj));r.u.mem_write(obj+0x48,struct.pack('<Q',script))
            r.u.mem_write(renderer,bytes(0x100));r.u.mem_write(r.base+0x3fc399,b'\x01');r.u.mem_write(r.base+0x3fc3a0,struct.pack('<Q',renderer))
            r.u.reg_write(UC_X86_REG_XMM1,0);r.u.reg_write(UC_X86_REG_XMM2,0);r.draw_x=[]
            try:r.run('draw',rcx=obj)
            except Exception as exc:
                from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_R15,UC_X86_REG_R12
                raise ValueError('Draw regs='+str({k:hex(r.u.reg_read(v)) for k,v in dict(rip=UC_X86_REG_RIP,rax=UC_X86_REG_RAX,rcx=UC_X86_REG_RCX,r15=UC_X86_REG_R15,r12=UC_X86_REG_R12).items()})) from exc
            expected_positions=[];x=0
            for c in line:
                expected_positions.append(float(x+font.glyphs[ord(c)].bearing_x));x+=advance(c,font)
            final=struct.unpack('<f',r.u.mem_read(obj+0x40,4))[0]
            if r.draw_x!=expected_positions or final!=expected:raise ValueError('Native subtitle sprite positions differ')
            checked.append(dict(id=row['id'],line=line_index,width=measured,sprites=len(r.draw_x),native_final_x=final))
    return dict(backend='Unicorn original E9980 loader/E9E10 measure/EADC0 dispatch',
        font_pages=len(font.pages),glyphs=len(font.glyphs),lines=checked,
        gpu_boundary='sprite creation and submission doubled; no rendered acceptance',game_launched=False)
