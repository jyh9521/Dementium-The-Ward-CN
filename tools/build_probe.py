"""Build one guarded text/font experiment entirely under project build/."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
from PIL import Image
from binfont import BinFont
from build_font import build_font
from content import Content,extract,import_text,text_kind,verify_index
from investigate import ensure_output,manifest,load
from replay_text import verify as replay_verify
from replay_font import verify_loader
from slot_encoding import validate_slots,encode,decode
from workspace_io import validate_output_tree
from zar import Zar,digest,filehash,write_json,make_delta,apply_delta

ROOT=Path(__file__).resolve().parents[1]


def inputs(game,locale):
    if not locale or '/' in locale or '\\' in locale or locale in ('.','..'):
        raise ValueError('Invalid locale directory')
    profile=json.loads((ROOT/'assets/game-profile.json').read_text(encoding='utf-8'))
    identity=json.loads((ROOT/'assets/original-identity.json').read_text(encoding='utf-8'))
    spec=json.loads((ROOT/'locales'/locale/'probe.json').read_text(encoding='utf-8'))
    font_profile=json.loads((ROOT/'locales'/locale/'font-profile.json').read_text(encoding='utf-8'))
    if manifest(game)!=identity['files']:raise ValueError('Original installation identity changed')
    z,c=load(game,profile,identity)
    if (spec['encoding']!='single-byte-glyph-slots-v1' or digest(c.read(spec['resource']))!=spec['source_sha256']
            or digest(c.read(profile['font']))!=spec['font_source_sha256']):
        raise ValueError('Unsupported probe source/font')
    return profile,identity,spec,font_profile,z,c


def baseline(game,out,locale):
    ensure_output(game,out)
    validate_output_tree(out)
    profile,identity,spec,fp,z,c=inputs(game,locale)
    f=BinFont(c.read(profile['font']))
    if c.rebuild({})!=c.data or z.rebuild({})!=z.data or f.rebuild()!=c.read(profile['font']):
        raise ValueError('No-op mismatch')
    from replay_text import Replay
    r=Replay(game/profile['executable'])
    if r.table(c.read(spec['resource']))[0]!=spec['source'].encode('ascii'):
        raise ValueError('Native original row mismatch')
    if r.widen(spec['target'].encode('utf-8'))!=list(spec['target'].encode('utf-8')):
        raise ValueError('Unexpected target decoder')
    print(f'BASELINE PASS original-glyphs={len(f.glyphs)} noop=byte-identical native-decoder=byte-widen UTF8-not-decoded=true')


def preview(font,slots,target,out):
    canvas=Image.new('RGBA',(sum(font.glyphs[s].advance+1 for s in slots),15),(0,0,0,255))
    x=0
    for s in slots:
        g=font.glyphs[s]
        image=Image.frombytes('RGBA',(g.width,g.height),font.glyph_rgba(s))
        canvas.alpha_composite(image,(x+g.bearing_x,g.bearing_y))
        x+=g.advance+1
    canvas.resize((canvas.width*8,canvas.height*8),Image.Resampling.NEAREST).save(out/'preview.png')


def modified(game,out,locale):
    ensure_output(game,out)
    validate_output_tree(out)
    profile,identity,spec,fp,z,c=inputs(game,locale)
    original_font=c.read(profile['font']);f=BinFont(original_font)
    resources=[c.read(n) for n in c.entries if text_kind(n)]
    validate_slots(spec['slots'],f,resources)
    runtime=encode(spec['target'],spec['slots'])
    if decode(runtime,spec['slots'])!=spec['target']:raise ValueError('Logical text inverse mismatch')
    records=extract(c,profile['source_locale'],profile['inventory_encoding'])
    hits=[r for r in records if r['id']==spec['id'] and r['source']==spec['source'] and r['resource']==spec['resource']]
    if len(hits)!=1:raise ValueError('Probe source ambiguous')
    hits[0]['target']=runtime.decode(profile['inventory_encoding'])
    changes=import_text(c,records,profile['source_locale'],profile['inventory_encoding'])
    font_data,font_report=build_font(original_font,{ord(k):v for k,v in spec['slots'].items()},fp)
    changes[profile['font']]=font_data
    modified_content=c.rebuild(changes)
    result=z.rebuild({profile['content']:modified_content})
    parsed=Zar(result);verify_index(parsed,profile['external_index'])
    after=Content(parsed.read(profile['content']))
    changed_inner=[n for n in c.entries if c.read(n)!=after.read(n)]
    changed_outer=[n for n in z.entries if z.read(n)!=parsed.read(n)]
    allowed_outer={profile['content']}
    if len(modified_content)!=len(c.data):allowed_outer.add('~INDEX')
    if set(changed_inner)!={spec['resource'],profile['font']} or set(changed_outer)!=allowed_outer:
        raise ValueError('Unexpected changed resource')
    if list(parsed.entries)!=list(z.entries) or list(after.entries)!=list(c.entries):
        raise ValueError('Member order changed')
    rr=extract(after,profile['source_locale'],profile['inventory_encoding'])
    differing=[(a,b) for a,b in zip(records,rr,strict=True) if a['source']!=b['source']]
    if len(differing)!=1 or differing[0][1]['source'].encode('latin-1')!=runtime:
        raise ValueError('Re-extracted records differ')
    if decode(runtime,spec['slots'])!=spec['target']:raise ValueError('Reverse glyph mapping failed')
    native=replay_verify(game/profile['executable'],original_font,font_data,c.read(spec['resource']),
                         after.read(spec['resource']),list(runtime),spec['source'],spec['target'])
    original_loader=verify_loader(game/profile['executable'],original_font)
    modified_loader=verify_loader(game/profile['executable'],font_data)
    delta=make_delta(z.data,result)
    if apply_delta(z.data,delta)!=result or apply_delta(result,delta,reverse=True)!=z.data:
        raise ValueError('Sparse delta roundtrip mismatch')
    # Build twice from the same inputs before writing any ready-to-test sample.
    again_font,again_info=build_font(original_font,{ord(k):v for k,v in spec['slots'].items()},fp)
    if again_font!=font_data or z.rebuild({profile['content']:c.rebuild(changes)})!=result:
        raise ValueError('Nondeterministic build')
    (out/'MODIFIED_FILE.zar').write_bytes(result)
    write_json(out/'DIFF_FILE.json',delta)
    write_json(out/'font-report.json',font_report)
    write_json(out/'native-replay.json',native)
    write_json(out/'original-loader.json',original_loader)
    write_json(out/'modified-loader.json',modified_loader)
    preview(BinFont(font_data),list(runtime),spec['target'],out)
    sample=out/'sample';sample.mkdir(exist_ok=True)
    if any(p.name not in {f['path'] for f in identity['files']} for p in sample.iterdir()):
        raise ValueError('Sample directory contains unexpected files')
    for f in identity['files']:
        target=sample/f['path']
        if target.resolve()==(game/f['path']).resolve():raise ValueError('Sample aliases original input')
        if f['path']==profile['archive']:
            shutil.copyfile(out/'MODIFIED_FILE.zar',target)
            expected=digest(result)
        else:
            shutil.copyfile(game/f['path'],target)
            expected=f['sha256']
        if filehash(target)!=expected:raise ValueError('Sample copy identity mismatch')
    report=dict(locale=locale,field=spec['id'],source=spec['source'],target=spec['target'],
        runtime_encoding=spec['encoding'],runtime_hex=runtime.hex(),changed_inner=changed_inner,
        changed_outer=changed_outer,original_sha256=digest(z.data),modified_sha256=digest(result),
        original_size=len(z.data),modified_size=len(result),source_records=len(records),changed_text_records=1,
        font_added=len(spec['slots']),sample=str(sample.resolve()),
        executable_modified=False,reproducible=True,game_launched=False,visual_acceptance='NOT_TESTED')
    write_json(out/'build-report.json',report)
    print('MODIFIED PASS field='+spec['id']+' logical='+spec['target']+' runtime='+runtime.hex()+
          ' text-records=1 added-glyphs='+str(len(spec['slots']))+' original-glyphs=preserved native-replay=PASS reproducible=true')


def rollback(out):
    ensure_output(ROOT/'original',out)
    validate_output_tree(out)
    patch=json.loads((out/'DIFF_FILE.json').read_text(encoding='utf-8'))
    source=out/'MODIFIED_FILE.zar'
    restored=apply_delta(source.read_bytes(),patch,reverse=True)
    target=out/'ROLLBACK_COPY.zar';target.write_bytes(restored)
    if filehash(target)!=patch['original_sha256']:raise ValueError('Rollback identity mismatch')
    # Exercise file-copy restoration in a second sample, leaving manual sample modified.
    copy=out/'rollback-sample';copy.mkdir(exist_ok=True)
    shutil.copyfile(source,copy/'rom.zar')
    shutil.copyfile(target,copy/'rom.zar')
    if filehash(copy/'rom.zar')!=patch['original_sha256']:raise ValueError('Copy rollback failed')
    if filehash(source)!=patch['modified_sha256']:raise ValueError('Modified artifact not retained')
    print('ROLLBACK PASS isolated-copy=original-sha256 text=New Game font=original modified-and-sample=retained')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('baseline','modified','rollback'))
    p.add_argument('--game',type=Path)
    p.add_argument('--locale',default='zh-CN')
    p.add_argument('--output',type=Path,default=ROOT/'build/phase2')
    a=p.parse_args()
    if a.command=='rollback':rollback(a.output)
    else:
        if a.game is None:p.error('--game required')
        globals()[a.command](a.game,a.output,a.locale)


if __name__=='__main__':main()
