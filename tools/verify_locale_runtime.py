"""Full-locale controlled replay; target processes are never created."""
from pathlib import Path
import re
import struct
import pefile
from binfont import BinFont
from locale_data import line_width
from replay_utf8 import UTF8Replay
from replay_font import verify_loader
from runtime_patch import patch_bytes,sha,validate_text

class LocaleReplay(UTF8Replay):
    def __init__(self,original_exe,patched_data):
        original_exe=Path(original_exe)
        expected,_=patch_bytes(original_exe.read_bytes())
        if bytes(patched_data)!=expected:
            raise ValueError('Patched executable does not match audited runtime output')
        super().__init__(original_exe)
        # Map the supplied output's actual bytes, rather than only a reconstructed snippet.
        pe=pefile.PE(data=bytes(patched_data),fast_load=True)
        self.u.mem_write(self.base,pe.get_memory_mapped_image());pe.close()
        self.u.mem_map(0x32000000,0x800000)
        self.font=0x32000000
        self.instruction_limit=20000000


def visible_line(line):
    """Exclude color/control units from glyph layout; never alter resource data."""
    return ''.join(c for c in line if ord(c)>=32)


def verify_locale_runtime(original_exe,patched_exe,original_font,full_font,records,runtime,
                          *,verify_font_loader=True,measure_text=True,original_encoding=None):
    """Verify every provided record, actual decoder bytes, visible line metrics and loader.

    Args: EXE paths; font bytes; sequence of structured records; ID->serialized
    Unicode runtime string. Returned JSON-safe report distinguishes compiler
    control-unit spacing from visible-glyph widths and all doubled boundaries.
    """
    original_exe=Path(original_exe);patched_data=Path(patched_exe).read_bytes()
    rows=list(records);keys=[r['id'] for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=set(runtime):
        raise ValueError('Record/runtime ID coverage mismatch')
    if not rows:raise ValueError('No locale records to replay')
    font=BinFont(full_font);old_font=BinFont(original_font)
    if any(font.glyphs.get(cp)!=g for cp,g in old_font.glyphs.items()):
        raise ValueError('Original font metrics changed')
    replay=LocaleReplay(original_exe,patched_data);replay.bind_font(full_font)
    # E9980 sets +0x824 from the space glyph advance; bind_font only binds tables.
    replay.u.mem_write(replay.obj+0x824,struct.pack('<f',font.glyphs[32].advance if 32 in font.glyphs else 0))
    baseline=UTF8Replay(original_exe,False)
    old_sample=baseline.decode('新游戏'.encode('utf-8'))
    if old_sample!=list('新游戏'.encode('utf-8')):
        raise ValueError('Original decoder baseline changed')
    checked=[];control_lines=[];line_count=0
    for row in rows:
        key=row['id'];text=runtime[key];raw=validate_text(text)
        actual=replay.decode(raw)
        if actual!=list(map(ord,text)):
            raise ValueError('Native UTF-8 decoder differs from Unicode: '+key)
        # Explicit-length path is used by examine documents and must match too.
        if replay.decode(raw,len(raw))!=actual:
            raise ValueError('Native byte-length decode differs: '+key)
        if original_encoding is not None:
            original_raw=text.encode(original_encoding,errors='strict')
            if baseline.decode(original_raw)!=actual:
                raise ValueError('Original/patched decoded streams differ: '+key)
        widths=[]
        for index,line in enumerate(re.split(r'\r\n|\r|\n',text)):
            if not measure_text:
                line_count+=1
                continue
            visible=visible_line(line)
            if '<' in visible or '>' in visible:
                raise ValueError('Unresolved native angle-markup semantics: '+key)
            native=replay.measure(list(map(ord,visible)))
            expected=line_width(line,font)
            if native!=expected:
                raise ValueError(f'Native visible width mismatch: {key}:{index} {native}!={expected}')
            raw_native=replay.measure(list(map(ord,line)))
            if raw_native!=native:
                control_lines.append(dict(id=key,line=index,raw_native_width=raw_native,
                    visible_native_width=native,control_count=sum(ord(c)<32 for c in line)))
            widths.append(native);line_count+=1
        checked.append(dict(id=key,utf8_bytes=len(raw),unicode_units=len(actual),lines=len(re.split(r'\r\n|\r|\n',text)),
            native_line_widths=widths,decode_explicit_length=True))
    loaders={}
    if verify_font_loader:
        loaders={'original':verify_loader(original_exe,original_font),'modified':verify_loader(original_exe,full_font)}
        if loaders['modified']['page_count']!=len(font.pages):raise ValueError('Font page coverage mismatch')
    return dict(backend='Unicorn exact original/patched PE instructions; no target process',
        original_exe_sha256=sha(original_exe.read_bytes()),patched_exe_sha256=sha(patched_data),
        records=len(checked),lines=line_count,decode_all_records=True,explicit_byte_length_all_records=True,
        visible_native_widths_match=True if measure_text else None,
        original_decoded_streams_preserved=original_encoding is not None,
        measurement_mode='visible glyph measurement' if measure_text else 'not measured; original decoded stream identity only',
        raw_control_spacing_differences=control_lines,
        font_pages=len(font.pages),font_glyphs=len(font.glyphs),original_glyph_metrics_preserved=len(old_font.glyphs),
        font_loaders=loaders,checks=checked,baseline_utf8_bytes=old_sample,
        game_launched=False,game_visual_acceptance=False,
        boundaries=['downstream compiler intercepted for decoding','font image/GPU','sprite construction',
                    'font VFS/allocator/free'])
