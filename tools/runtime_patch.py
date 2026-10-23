"""Exact-build, reversible UTF-8/BMP entry patch; no target process execution."""
from pathlib import Path
import hashlib
import struct
import pefile
from keystone import Ks, KS_ARCH_X86, KS_MODE_64

ORIGINAL_SHA256 = '26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e'
ORIGINAL_SIZE = 4673536
RVA = 0xea700
LENGTH = 577
FILE_OFFSET = 957184
FUNCTION_SHA256 = '47e570d74b334532fb420a77d4194975a877d8d0d507c3f40db4a3fbf41c0bdc'
BASE = 0x140000000
BUFFER = BASE + 0xd1bc40
MAX_UNITS = 4095
PROLOGUE = bytes.fromhex('48895c240848896c241048897424185741544155415641574883ec30')


def sha(data): return hashlib.sha256(data).hexdigest()


def validate_text(text):
    if '\0' in text or len(text) > MAX_UNITS or any(0xd800 <= ord(c) <= 0xdfff or ord(c)>0xffff for c in text):
        raise ValueError('Text requires non-NUL BMP and at most 4095 code units')
    return text.encode('utf-8')


def replacement(original):
    """Keep original prologue and epilogue, including Windows unwind offsets."""
    if len(original) != LENGTH or sha(original) != FUNCTION_SHA256:
        raise ValueError('Unexpected whole-function bytes')
    prefix = '''mov rbp, qword ptr [rsp+0x80]; mov r13,rcx; mov edi,dword ptr [rsp+0x88];
    mov r14d,r9d; mov r15,r8; mov r12,rdx; lea rsi,[rip]; xor ebx,ebx;'''
    body = '''
next:
    test edi,edi
    jz done
    cmp ebx,4095
    jae done
    movzx eax,byte ptr [rbp]
    test eax,eax
    jz done
    mov r11d,1
    cmp eax,128
    jb emit
    lea ecx,[rax-194]
    cmp ecx,29
    jbe two
    lea ecx,[rax-224]
    cmp ecx,15
    jbe three
bad:
    mov eax,63
    mov r11d,1
    jmp emit
two:
    cmp edi,2
    jb bad
    movzx edx,byte ptr [rbp+1]
    mov ecx,edx
    and ecx,192
    cmp ecx,128
    jne bad
    and eax,31
    shl eax,6
    and edx,63
    or eax,edx
    mov r11d,2
    jmp emit
three:
    cmp edi,3
    jb bad
    movzx edx,byte ptr [rbp+1]
    mov ecx,edx
    and ecx,192
    cmp ecx,128
    jne bad
    and eax,15
    shl eax,6
    and edx,63
    or eax,edx
    shl eax,6
    movzx edx,byte ptr [rbp+2]
    mov ecx,edx
    and ecx,192
    cmp ecx,128
    jne bad
    and edx,63
    or eax,edx
    cmp eax,2048
    jb bad
    lea ecx,[rax-0xd800]
    cmp ecx,0x7ff
    jbe bad
    mov r11d,3
emit:
    mov word ptr [rsi+rbx*2],ax
    inc ebx
    add rbp,r11
    sub edi,r11d
    jmp next
done:
    mov word ptr [rsi+rbx*2],0
    mov edi,ebx
    jmp 0x1400ea8f5
'''
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    code = bytearray(PROLOGUE + bytes(ks.asm(prefix+body, BASE+RVA+len(PROLOGUE))[0]))
    # lea rsi,[rip+disp32] remains ASLR-neutral and needs no new relocation.
    marker = code.index(bytes.fromhex('488d3500000000'))
    struct.pack_into('<i',code,marker+3,BUFFER-(BASE+RVA+marker+7))
    tail = 0x1f5
    if len(code)>tail: raise ValueError('Decoder exceeds original function body')
    return bytes(code)+b'\x90'*(tail-len(code))+original[tail:]


def patch_bytes(data):
    data = bytes(data)
    if len(data)!=ORIGINAL_SIZE or sha(data)!=ORIGINAL_SHA256:
        raise ValueError('Unsupported executable identity')
    pe=pefile.PE(data=data,fast_load=False)
    if pe.FILE_HEADER.Machine!=0x8664 or pe.OPTIONAL_HEADER.ImageBase!=BASE or pe.get_offset_from_rva(RVA)!=FILE_OFFSET:
        raise ValueError('Unexpected PE layout')
    entries=[e.struct for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress==RVA]
    if len(entries)!=1 or entries[0].EndAddress!=RVA+LENGTH:
        raise ValueError('Unexpected function boundary')
    pe.close()
    old=data[FILE_OFFSET:FILE_OFFSET+LENGTH]
    new=replacement(old)
    out=data[:FILE_OFFSET]+new+data[FILE_OFFSET+LENGTH:]
    recipe={'schema':1,'original_sha256':sha(data),'modified_sha256':sha(out),'size':len(data),
        'rva':RVA,'offset':FILE_OFFSET,'before':old.hex(),'after':new.hex(),
        'field':'UTF-8/BMP decoder at RVA 0xEA700; other bytes unchanged'}
    return out,recipe


def rollback_bytes(data,recipe):
    if sha(data)!=recipe['modified_sha256'] or len(data)!=recipe['size']:
        raise ValueError('Rollback modified identity mismatch')
    at=recipe['offset'];new=bytes.fromhex(recipe['after']);old=bytes.fromhex(recipe['before'])
    if data[at:at+len(new)]!=new:raise ValueError('Rollback bytes mismatch')
    result=data[:at]+old+data[at+len(new):]
    if sha(result)!=recipe['original_sha256']:raise ValueError('Rollback original identity mismatch')
    return result
