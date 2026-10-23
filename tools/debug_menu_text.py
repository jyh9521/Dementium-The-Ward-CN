"""Source-bound native debug menu UTF-8 text pool and pointer patching.

Table name fields reuse their existing DIR64 relocations; state LEAs stay
RIP-relative. Callbacks, source strings, and unrelated shared true/false users
remain unchanged. A caller owns adding the returned pool to a mapped section.
"""
from __future__ import annotations
import hashlib
import struct
import pefile
from runtime_patch import ORIGINAL_SHA256, validate_text


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_catalog(catalog):
    if catalog.get('schema') != 1 or catalog.get('encoding') != 'utf-8' or catalog.get('source_sha256') != ORIGINAL_SHA256:
        raise ValueError('Unsupported debug text catalog/source identity')
    rows = catalog['entries'] + catalog['states']
    ids = set()
    for row in rows:
        if row['id'] in ids or not row['target']:
            raise ValueError('Duplicate or empty debug text')
        ids.add(row['id'])
        raw = validate_text(row['target'])
        # C62A0/C6380/C65B0 copy labels into per-row 64-byte fields.
        # Boolean status is formatted into a 16-byte caller stack field.
        limit = 15 if row in catalog['states'] else 63
        if len(raw) > limit:
            raise ValueError('Debug UTF-8 text exceeds native field capacity')
        source = row['source']
        if source.startswith('Load ') and row['target'].split()[-1] != source[5:]:
            raise ValueError('Debug load-section identifier changed')
        if len(source) == 3 and source[0].isdigit() and source not in row['target']:
            raise ValueError('Debug section identifier changed')
    pointers = [q['rva'] for r in catalog['entries'] for q in r['pointers']]
    expected = [t['rva'] + i * 16 for t in catalog['tables'] for i in range(t['count'])]
    if len(pointers) != len(set(pointers)) or set(pointers) != set(expected):
        raise ValueError('Debug table coverage mismatch')
    return catalog


def required_text(catalog):
    validate_catalog(catalog)
    return [r['target'] for r in catalog['entries'] + catalog['states']]


def build_text_patch(data, catalog, pool_rva):
    validate_catalog(catalog)
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    relocations = {e.rva for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type == 10}
    out = bytearray(data)
    pool = bytearray()
    runs = []
    targets = {}

    def patch(rva, old, new, identity):
        offset = pe.get_offset_from_rva(rva)
        if bytes(out[offset:offset + len(old)]) != old or len(old) != len(new):
            raise ValueError('Debug text byte guard mismatch: ' + identity)
        out[offset:offset + len(old)] = new
        runs.append(dict(id=identity, rva=rva, offset=offset, old=old.hex(), new=new.hex()))

    for table in catalog['tables']:
        if _sha(pe.get_data(table['rva'], table['count'] * 16)) != table['sha256']:
            raise ValueError('Debug command table source identity mismatch')
    for row in catalog['entries'] + catalog['states']:
        original = row['source'].encode('ascii') + b'\0'
        if pe.get_data(row['source_rva'], len(original)) != original:
            raise ValueError('Debug source literal changed')
        target_rva = pool_rva + len(pool)
        targets[row['id']] = target_rva
        pool.extend(validate_text(row['target']) + b'\0')
        for pointer in row.get('pointers', []):
            rva = pointer['rva']
            if rva not in relocations:
                raise ValueError('Debug name pointer lacks existing DIR64 relocation')
            if pe.get_data(rva + 8, 8) != struct.pack('<Q', base + pointer['callback_rva']):
                raise ValueError('Debug callback identity changed')
            patch(rva, struct.pack('<Q', base + row['source_rva']), struct.pack('<Q', base + target_rva), row['id'])
        for reference in row.get('references', []):
            old = bytes.fromhex(reference['old'])
            if reference['disp_size'] != 4:
                raise ValueError('Unsupported state LEA displacement')
            new = bytearray(old)
            struct.pack_into('<i', new, reference['disp_offset'], target_rva - reference['rva'] - len(old))
            patch(reference['rva'], old, new, row['id'])
    pe.close()
    recipe = dict(schema=1, format='debug-text-pool-v1', pool_rva=pool_rva,
                  pool_size=len(pool), pool_sha256=_sha(pool), targets=targets, runs=runs,
                  tables=len(catalog['tables']), table_labels=sum(t['count'] for t in catalog['tables']),
                  unique_labels=len(catalog['entries']), boolean_state_references=sum(len(r['references']) for r in catalog['states']))
    return bytes(out), bytes(pool), recipe


def restore_text(data, recipe):
    out = bytearray(data)
    for run in reversed(recipe['runs']):
        at = run['offset']; old = bytes.fromhex(run['old']); new = bytes.fromhex(run['new'])
        if out[at:at + len(new)] != new:
            raise ValueError('Debug text rollback byte guard mismatch')
        out[at:at + len(old)] = old
    return bytes(out)


def verify_text(data, catalog, recipe, font):
    """Verify actual mapped pool, callbacks, ASLR targets and native font metrics.

    Instruction replay is separate in replay_debug_menu_text(); font must be a
    BinFont instance. GPU output and menu side effects remain manual acceptance.
    """
    from locale_data import line_width
    validate_catalog(catalog)
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    pool = pe.get_data(recipe['pool_rva'], recipe['pool_size'])
    if _sha(pool) != recipe['pool_sha256']:
        raise ValueError('Mapped debug text pool identity mismatch')
    checked=[]
    for row in catalog['entries'] + catalog['states']:
        rva = recipe['targets'][row['id']]
        raw = validate_text(row['target']) + b'\0'
        if pe.get_data(rva, len(raw)) != raw:
            raise ValueError('Mapped debug translation mismatch')
        source = row['source'].encode('ascii') + b'\0'
        if pe.get_data(row['source_rva'], len(source)) != source:
            raise ValueError('Shared original debug literal changed')
        for reference in row.get('references', []):
            instruction = pe.get_data(reference['rva'], len(bytes.fromhex(reference['old'])))
            displacement = struct.unpack_from('<i', instruction, reference['disp_offset'])[0]
            if reference['rva'] + len(instruction) + displacement != rva:
                raise ValueError('Debug boolean instruction target mismatch')
        missing = {ord(ch) for ch in row['target']} - font.glyphs.keys()
        if missing:
            raise ValueError('Debug menu font missing glyphs')
        for pointer in row.get('pointers', []):
            if struct.unpack('<QQ', pe.get_data(pointer['rva'],16)) != (base+rva,base+pointer['callback_rva']):
                raise ValueError('Localized debug table/callback mismatch')
        checked.append(dict(id=row['id'], bytes=len(raw)-1,width=line_width(row['target'],font)))
    pe.close()
    return dict(tables=recipe['tables'], table_labels=recipe['table_labels'],
                unique_labels=recipe['unique_labels'], states=len(catalog['states']),
                boolean_state_references=recipe['boolean_state_references'],
                callback_pointers_unchanged=True, original_shared_literals_unchanged=True,
                utf8_fields_bounded=True, glyph_coverage=True, checks=checked, game_launched=False)


def replay_debug_menu_text(original_exe, data, catalog, recipe, font):
    """Run actual C62A0 label copying and eight original boolean query branches.

    The table callback boundary in page replay returns empty values to avoid
    invoking gameplay; boolean query replay independently executes real callback
    instructions and stops at snprintf (3E940), capturing its selected pointer.
    """
    from pathlib import Path
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP
    from replay_utf8 import UTF8Replay
    from runtime_patch import RVA, FILE_OFFSET, LENGTH, patch_bytes
    from locale_data import line_width
    original_exe=Path(original_exe)
    expected,_=patch_bytes(original_exe.read_bytes())
    if data[FILE_OFFSET:FILE_OFFSET+LENGTH] != expected[FILE_OFFSET:FILE_OFFSET+LENGTH]:
        raise ValueError('Debug label runtime decoder not enabled')
    callback_rvas={p['callback_rva'] for r in catalog['entries'] for p in r['pointers']}
    by_pointer={p['rva']:r for r in catalog['entries'] for p in r['pointers']}
    pages=[];states=[]
    for base in (0x140000000,0x180000000):
        pe=pefile.PE(data=bytes(data));pe.relocate_image(base);image=pe.get_memory_mapped_image();pe.close()
        u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base,(len(image)+4095)&~4095);u.mem_write(base,image)
        u.mem_map(0x30000000,0x300000)
        obj,stack,stop=0x30010000,0x30200008,0x300f0000
        def ret(uc):
            rsp=uc.reg_read(UC_X86_REG_RSP);address=int.from_bytes(uc.mem_read(rsp,8),'little')
            uc.reg_write(UC_X86_REG_RSP,rsp+8);uc.reg_write(UC_X86_REG_RIP,address)
        def callback_boundary(uc,address,size,user):
            if address-base in callback_rvas:
                if uc.reg_read(UC_X86_REG_RCX)!=0:raise ValueError('Page replay attempted a gameplay action')
                uc.mem_write(uc.reg_read(UC_X86_REG_RDX),b'\0');ret(uc)
        handle=u.hook_add(UC_HOOK_CODE,callback_boundary)
        for table in catalog['tables']:
            for start in range(0,table['count'],12):
                u.mem_write(obj,bytes(0xd60));u.mem_write(obj+0xd20,struct.pack('<Q',base+table['rva']))
                u.mem_write(obj+0xd58,bytes([table['count'],start]))
                u.mem_write(stack,struct.pack('<Q',stop));u.reg_write(UC_X86_REG_RSP,stack);u.reg_write(UC_X86_REG_RCX,obj)
                u.emu_start(base+0xc62a0,stop,count=100000)
                if u.reg_read(UC_X86_REG_RIP)!=stop:raise ValueError('Debug page fill did not return')
                for index in range(min(12,table['count']-start)):
                    row=by_pointer[table['rva']+(start+index)*16]
                    actual=bytes(u.mem_read(obj+0x720+index*64,64)).split(b'\0')[0].decode('utf-8')
                    if actual!=row['target']:raise ValueError('Native debug label fill mismatch')
                pages.append(dict(base=hex(base),table=table['id'],start=start,labels=min(12,table['count']-start)))
        u.hook_del(handle)
        selected=[]
        def snprintf_boundary(uc,address,size,user):
            if address==base+0x3e940:
                pointer=uc.reg_read(UC_X86_REG_R8)
                selected.append(bytes(uc.mem_read(pointer,16)).split(b'\0')[0].decode('utf-8'))
                ret(uc)
        u.hook_add(UC_HOOK_CODE,snprintf_boundary)
        for callback,field,kind in [(0xc5d70,0x3fc415,'byte'),(0xc5db0,0x39634c,'flag'),
                (0xc5e00,0x3a83b4,'vsync'),(0xc5e70,0x3a5340,'collision'),
                (0xc5ee0,0x3fc409,'byte'),(0xc5f20,0x3fc414,'byte'),
                (0xc5f60,0x3fc40b,'byte'),(0xc5fa0,0x3fc40a,'byte')]:
            # source-bound values are supplied here, not OS or gameplay objects.
            for value in (0,1):
                if kind=='collision':
                    u.mem_write(base+field,struct.pack('<Q',obj));u.mem_write(obj+0x44,struct.pack('<I',value<<11))
                elif kind=='flag':u.mem_write(base+field,struct.pack('<I',value<<16))
                elif kind=='vsync':u.mem_write(base+field,struct.pack('<I',value*60))
                else:u.mem_write(base+field,bytes([value]))
                u.mem_write(stack,struct.pack('<Q',stop));u.reg_write(UC_X86_REG_RSP,stack)
                u.reg_write(UC_X86_REG_RCX,0);u.reg_write(UC_X86_REG_RDX,obj+0xe00)
                u.emu_start(base+callback,stop,count=1000)
                if u.reg_read(UC_X86_REG_RIP)!=stop or selected[-1]!=catalog['states'][value]['target']:
                    raise ValueError(f'Native boolean query mismatch: {callback:x} value={value} actual={selected[-1]}')
                states.append(dict(base=hex(base),callback_rva=hex(callback),value=value,target=selected[-1]))
    replay=UTF8Replay(original_exe)
    replay.u.mem_write(replay.base+RVA,data[FILE_OFFSET:FILE_OFFSET+LENGTH])
    replay.bind_font(font.data)
    replay.u.mem_write(replay.obj+0x824,struct.pack('<f',font.glyphs[32].advance))
    widths=[]
    for row in catalog['entries']+catalog['states']:
        actual=replay.decode(row['target'].encode('utf-8'))
        if actual!=list(map(ord,row['target'])):raise ValueError('Native debug UTF-8 decode mismatch')
        width=replay.measure(actual)
        if width!=line_width(row['target'],font):raise ValueError('Native debug label width mismatch')
        widths.append(dict(id=row['id'],width=width))
    return dict(pages=pages,labels_copied=sum(r['labels'] for r in pages),boolean_queries=states,
                decoded_labels=len(widths),native_widths=widths,aslr_bases=2,
                boundary_doubles=['menu query callbacks return empty status during page fill','snprintf captures selected string pointer','text compiler and GPU boundaries from UTF8Replay'],
                game_launched=False,visual_acceptance=False)



def load_catalog(path):
    import json
    from pathlib import Path
    return validate_catalog(json.loads(Path(path).read_text(encoding='utf-8')))
