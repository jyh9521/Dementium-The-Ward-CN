"""Offline Y-axis legend composition: original caller coordinates and exact icon pixels."""
import argparse
import json
from pathlib import Path
import struct
from PIL import Image, ImageDraw
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP,UC_X86_REG_RBP,UC_X86_REG_RIP,UC_X86_REG_XMM1,UC_X86_REG_XMM2,UC_X86_REG_XMM3,UC_X86_REG_XMM7
from binfont import BinFont
from build_image_text import build_images
from font_source import resolve_fonts
from replay_text import AUDITED_SHA256
from texture import Texture
from workspace_io import validate_output_tree
from zar import Zar, filehash

ROOT=Path(__file__).resolve().parents[1]


def caller_coordinates(executable):
    if filehash(executable)!=AUDITED_SHA256:
        raise ValueError('Unknown original executable')
    results=[]
    for base in (0x140000000,0x150000000):
        pe=pefile.PE(str(executable),fast_load=True)
        u=Uc(UC_ARCH_X86,UC_MODE_64)
        u.mem_map(base,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        u.mem_write(base,pe.get_memory_mapped_image());pe.close()
        u.mem_map(0x20000000,0x20000);u.mem_map(0x31000000,0x10000)
        calls=[]
        def scalar(register):
            return struct.unpack('<f',u.reg_read(register).to_bytes(16,'little')[:4])[0]
        def boundary(machine,address,size,user):
            rva=address-base
            if rva not in (0xeadc0,0x107dc0):return
            if rva==0xeadc0:
                calls.append(dict(kind='state',x=scalar(UC_X86_REG_XMM1),y=scalar(UC_X86_REG_XMM2)))
            else:
                calls.append(dict(kind='texture',x=scalar(UC_X86_REG_XMM2),y=scalar(UC_X86_REG_XMM3)))
            sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0])
            u.reg_write(UC_X86_REG_RSP,sp+8)
        u.hook_add(UC_HOOK_CODE,boundary)
        for start,end in [(0xc2bae,0xc2bc9),(0xc2c7f,0xc2ca2)]:
            u.reg_write(UC_X86_REG_RSP,0x2001fe00)
            u.reg_write(UC_X86_REG_RBP,0x31008000)
            u.reg_write(UC_X86_REG_XMM7,0)
            u.emu_start(base+start,base+end,count=50)
            if u.reg_read(UC_X86_REG_RIP)!=base+end:raise ValueError('Caller replay stopped early')
        if calls!=[dict(kind='texture',x=-68.,y=0.),dict(kind='state',x=125.,y=220.)]:
            raise ValueError(('Original option coordinates differ',calls))
        results.append(dict(base=hex(base),calls=calls,boundary='texture GPU and text draw doubled; RIP-relative caller slices execute unchanged'))
    return results


def draw_state(image,font,text,origin):
    x,y=origin
    for char in text:
        g=font.glyphs[ord(char)]
        glyph=Image.frombytes('RGBA',(g.width,g.height),font.glyph_rgba(ord(char)))
        image.alpha_composite(glyph,(int(x+g.bearing_x),int(y+g.bearing_y)))
        x+=g.advance


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True,type=Path)
    parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--locale',default='zh-CN')
    parser.add_argument('--previous-build',type=Path)
    args=parser.parse_args();out=args.build.resolve()
    if not out.is_relative_to(ROOT/'build'):raise ValueError('Output must stay under build/')
    validate_output_tree(out)
    if not args.locale or '/' in args.locale or '\\' in args.locale or args.locale in ('.','..'):
        raise ValueError('Invalid locale name')
    directory=ROOT/'locales'/args.locale
    config=json.loads((directory/'image-text.json').read_text(encoding='utf-8'))
    config['images']=[r for r in config['images'] if r['resource'].endswith('_YAXIS.PNG')]
    fontpath=resolve_fonts({'fonts':{'body':config['font']}})['body']
    original_path=args.game/'rom.zar';source_sha=filehash(original_path)
    source=Zar(original_path.read_bytes())
    replacements,report=build_images(source,config,fontpath)
    original_exe=args.game/'Dementium.exe'
    native=caller_coordinates(original_exe)
    fontfile=out/'full.binfont'
    if not fontfile.exists():fontfile=ROOT/'build/ui-feedback-release/full.binfont'
    font=BinFont(fontfile.read_bytes())
    rows=json.loads((directory/'strings-ui-items.json').read_text(encoding='utf-8'))
    states=[next(r['target'] for r in rows if r['id']==f'loc/en/UIOptionsNew.tbl:{index:04d}') for index in (2,1)]
    # State ink comes from actual generated binfont cells, not a separate TTF rendering.
    state_bounds=[]
    for state in states:
        mask=Image.new('RGBA',(100,32));draw_state(mask,font,state,(0,0))
        bounds=mask.getchannel('A').getbbox()
        state_bounds.append([bounds[1]+220,bounds[3]+220])
    checks=[];sheet=Image.new('RGB',(900,4*150),(30,30,30));draw=ImageDraw.Draw(sheet)
    previous_config=out/'baseline-image-text.json'
    before=None
    if previous_config.exists():
        old=json.loads(previous_config.read_text(encoding='utf-8'))
        old['images']=[r for r in old['images'] if r['resource'].endswith('_YAXIS.PNG')]
        before,_=build_images(source,old,fontpath)
    for index,recipe in enumerate(config['images']):
        name=recipe['resource'];raw=source.read(name);original=Texture(raw)
        image=Image.frombytes('RGBA',(original.width,original.height),original.rgba)
        changed=Texture(replacements[name]);result=Image.frombytes('RGBA',(changed.width,changed.height),changed.rgba)
        record=next(r for r in report['images'] if r['resource']==name)
        label=record['labels'][0]['ink_box'];move=recipe['relocations'][0]
        src=move['source_box'];dst=move['destination_box']
        if result.crop(dst).tobytes()!=image.crop(src).tobytes():raise ValueError('Icon pixel mismatch')
        if any(bounds!=[label[1],label[3]] for bounds in state_bounds):raise ValueError('Label/state ink not aligned')
        if dst[1]+dst[3]!=label[1]+label[3]:raise ValueError('Icon not vertically centered')
        if label[0]-dst[2]<6 or 193-label[2]<4:raise ValueError('Legend horizontal spacing too small')
        checks.append(dict(resource=name,label_ink=label,icon_box=dst,state_ink_y=state_bounds,
                           icon_label_gap=label[0]-dst[2],label_state_gap=193-label[2],icon_pixels_exact=True))
        for column,state in enumerate(states):
            composite=Image.new('RGBA',(428,240),(30,30,30,255));composite.alpha_composite(result,(-68,0))
            draw_state(composite,font,state,(125,220))
            preview=composite.crop((65,215,155,240)).resize((450,125),Image.Resampling.NEAREST)
            sheet.paste(preview.convert('RGB'),(column*450,index*150+25))
        draw.text((4,index*150+3),name.split('/')[-1],fill='white')
        if before:
            old=Texture(before[name]);old_image=Image.frombytes('RGBA',(old.width,old.height),old.rgba)
            pair=Image.new('RGBA',(428,480),(30,30,30,255))
            pair.alpha_composite(old_image,(-68,0));draw_state(pair,font,states[0],(125,220))
            panel=Image.new('RGBA',(428,240),(30,30,30,255));panel.alpha_composite(result,(-68,0));draw_state(panel,font,states[0],(125,220));pair.alpha_composite(panel,(0,240))
            # Crop each actual-coordinate legend row; this is a composition, not a game screenshot.
            comparison=Image.new('RGBA',(450,250),(30,30,30,255))
            for i in (0,1):comparison.paste(pair.crop((65,215+240*i,155,240+240*i)).resize((450,125),Image.Resampling.NEAREST),(0,125*i))
            comparison.convert('RGB').save(out/(name.split('/')[-1]+'.before-after.png'))
    sheet.save(out/'yaxis-preview.png')
    scope={}
    modified_path=out/'MODIFIED_FILE.zar'
    if modified_path.exists():
        modified=Zar(modified_path.read_bytes())
        for name,data in replacements.items():
            if modified.read(name)!=data:raise ValueError('Final archive differs from rendered recipe: '+name)
        scope['modified_sha256']=filehash(modified_path)
        if args.previous_build:
            previous=Zar((args.previous_build/'MODIFIED_FILE.zar').read_bytes())
            if list(previous.entries)!=list(modified.entries):raise ValueError('Archive member order changed')
            changed=[name for name in modified.entries if modified.read(name)!=previous.read(name)]
            if not set(replacements).issubset(changed) or set(changed)-set(replacements)-{'~INDEX'}:
                raise ValueError(('Unexpected changed member scope',changed))
            if filehash(out/'MODIFIED_EXECUTABLE.exe')!=filehash(args.previous_build/'MODIFIED_EXECUTABLE.exe'):
                raise ValueError('Unrelated executable changed')
            scope.update(changed_members=changed,executable_unchanged=True,
                         previous_archive_sha256=filehash(args.previous_build/'MODIFIED_FILE.zar'))
    if filehash(original_path)!=source_sha:raise ValueError('Original input changed')
    result=dict(scope=scope,native=native,checks=checks,font_sha256=filehash(fontfile),source_sha256=source_sha,
                game_launched=False,source_unchanged=True,preview='offline composition, no GPU/game execution')
    (out/'yaxis-layout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'YAXIS PASS devices={len(checks)} states=2 bases=2 icon-label-gap=6 label-state-gap=4 ink-y=223..234 icon-pixels=exact input=unchanged game-launched=false')

if __name__=='__main__':main()
