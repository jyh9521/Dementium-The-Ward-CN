"""Reproducible full locale build from exact original files; never launch a game."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
from binfont import BinFont
from build_font import build_font
from content import Content,extract,verify_index
from investigate import ensure_output,manifest,load
from locale_data import read_records,validate_records,build_resources,transcode_preserved_locales
from runtime_patch import patch_bytes,rollback_bytes
from executable_text import build_executable,apply_executable_patch,validate_hud_capacity
from workspace_io import validate_output_tree
from zar import Zar,digest,filehash,write_json,make_delta,apply_delta

ROOT=Path(__file__).resolve().parents[1]


def configuration(locale):
    if not locale or '/' in locale or '\\' in locale or locale in ('.','..'):
        raise ValueError('Invalid locale name')
    directory=ROOT/'locales'/locale
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    return (read(ROOT/'assets/game-profile.json'),read(ROOT/'assets/original-identity.json'),
            directory,read(directory/'font-full-profile.json'))


def inputs(game,locale):
    profile,identity,directory,fp=configuration(locale)
    if manifest(game)!=identity['files']:raise ValueError('Original installation identity changed')
    z,c=load(game,profile,identity)
    rows=read_records([directory/'strings-ui-items.json',directory/'strings-documents.json'])
    validate_records(c,rows,profile['source_locale'],profile['inventory_encoding'])
    return profile,identity,directory,fp,z,c,rows


def baseline(game,out,locale):
    ensure_output(game,out);validate_output_tree(out)
    p,i,d,fp,z,c,rows=inputs(game,locale)
    f=BinFont(c.read(p['font']))
    if z.rebuild({})!=z.data or c.rebuild({})!=c.data or f.rebuild()!=f.data:
        raise ValueError('Original no-op is not byte-identical')
    verify_index(z,p['external_index'])
    from replay_utf8 import UTF8Replay
    r=UTF8Replay(game/p['executable'],patched=False)
    probe='新游戏'.encode('utf-8')
    if r.decode(probe)!=list(probe):raise ValueError('Unexpected original decoder')
    write_json(out/'baseline.json',dict(original_files=i['files'],records=len(rows),
        archive_members=len(z.entries),content_members=len(c.entries),noop_byte_identical=True,
        original_decoder='single-byte widening',game_launched=False))
    print(f'BASELINE PASS records={len(rows)} archive-members={len(z.entries)} content-members={len(c.entries)} noop=byte-identical input=unchanged decoder=byte-widen')


def assemble(game,locale,include_images=True,media_output=None):
    p,i,d,fp,z,c,rows=inputs(game,locale)
    original_font=c.read(p['font']);old=BinFont(original_font)
    extra=[]
    for filename,key,cues in [('movie-subtitles.json','movies','segments'),('movie-onscreen-text.json','movies','cues'),('audio-subtitles.json','clips','cues')]:
        path=d/filename
        if path.exists():
            for item in json.loads(path.read_text(encoding='utf-8'))[key]:
                extra.extend(cue['target'] for cue in item.get(cues,[]))
    debug_catalog=None
    if (d/'debug-menu.json').exists():
        from debug_menu_text import load_catalog, required_text
        debug_catalog=load_catalog(d/'debug-menu.json')
        extra.extend(required_text(debug_catalog))
    chars={ord(ch) for text in [r['target'] for r in rows]+extra for ch in text if ord(ch)>=32}
    mapping={cp:cp for cp in sorted(chars-old.glyphs.keys())}
    font,font_report=build_font(original_font,mapping,fp)
    changes,runtime,layout=build_resources(c,rows,BinFont(font),z.entries,p['source_locale'])
    preserved,preserved_records,preserved_runtime,preserved_report=transcode_preserved_locales(c,p['source_locale'])
    if changes.keys()&preserved.keys():raise ValueError('Overlapping locale edits')
    changes.update(preserved)
    changes[p['font']]=font
    hud=validate_hud_capacity([dict(row,target=runtime[row['id']]) for row in rows])
    outer={};image_report={};movie_frames=[]
    if include_images:
        from build_image_text import build_images
        from font_source import resolve_fonts
        config=json.loads((d/'image-text.json').read_text(encoding='utf-8'))
        source=resolve_fonts({'fonts':{'body':config['font']}})['body']
        outer,image_report=build_images(z,config,source)
        if (d/'art-patches.json').exists():
            from build_art import build_art
            art_inner,art_outer,art_report=build_art(z,c,d/'art-patches.json')
            if changes.keys()&art_inner.keys() or outer.keys()&art_outer.keys():raise ValueError('Overlapping resource edits')
            changes.update(art_inner);outer.update(art_outer);image_report['art']=art_report
        if media_output is not None:
            from movie_layers import compile_layers
            movie_frames,movie_report=compile_layers(z,d/'movie-subtitles.json',source,media_output)
            image_report['movies']=movie_report
    new_content=c.rebuild(changes)
    outer[p['content']]=new_content
    archive=z.rebuild(outer)
    exe,runtime_recipe=patch_bytes((game/p['executable']).read_bytes())
    exe,literal_recipe=build_executable(exe,json.loads((d/'executable-text.json').read_text(encoding='utf-8')))
    utf8_executable=exe
    overlay_recipe=None
    if include_images:
        from audio_subtitles import build_native_overlay
        catalog=json.loads((d/'audio-subtitles.json').read_text(encoding='utf-8'))
        members={row['resource']:z.read(row['resource']) for row in catalog['clips'] if row['cues']}
        exe,overlay_recipe=build_native_overlay(exe,runtime_recipe,catalog,members,BinFont(font))
    debug_recipe=None
    if debug_catalog is not None:
        from debug_menu import build_debug_menu
        exe,debug_recipe=build_debug_menu(exe,(game/p['executable']).read_bytes(),debug_catalog)
    movie_recipe=None
    if movie_frames:
        from movie_overlay import build_movie_overlay
        exe,movie_recipe=build_movie_overlay(exe,(game/p['executable']).read_bytes(),movie_frames,
                                            expected_input_sha256=digest(exe))
    return dict(profile=p,identity=i,rows=rows,original_zar=z,original_content=c,
        archive=archive,executable=exe,utf8_executable=utf8_executable,font=font,font_report=font_report,
        runtime=runtime,layout=layout,hud=hud,images=image_report,
        preserved_records=preserved_records,preserved_runtime=preserved_runtime,preserved_report=preserved_report,
        inner_changes=changes,outer_changes=outer,runtime_recipe=runtime_recipe,literal_recipe=literal_recipe,
        overlay_recipe=overlay_recipe,debug_recipe=debug_recipe,movie_recipe=movie_recipe,movie_frames=movie_frames)


def verify_resources(result):
    p=result['profile'];z=result['original_zar'];c=result['original_content']
    after_z=Zar(result['archive']);verify_index(after_z,p['external_index'])
    after=Content(after_z.read(p['content']))
    if list(z.entries)!=list(after_z.entries) or list(c.entries)!=list(after.entries):raise ValueError('Member order changed')
    for name in c.entries:
        if after.read(name)!=result['inner_changes'].get(name,c.read(name)):raise ValueError('Unexpected inner change: '+name)
    for name in z.entries:
        if name!='~INDEX' and after_z.read(name)!=result['outer_changes'].get(name,z.read(name)):
            raise ValueError('Unexpected outer change: '+name)
    movies=[name for name in z.entries if name.startswith('MOVIES/')]
    if any(after_z.read(name)!=z.read(name) for name in movies):
        raise ValueError('Original movie media changed')
    # Source identifiers/line counts survive the UTF-8 serialization; offsets may grow.
    reread=extract(after,p['source_locale'],'utf-8')
    if {r['id']:r['source'] for r in reread}!=result['runtime']:raise ValueError('UTF-8 re-extraction mismatch')
    for locale in {r['locale'] for r in result['preserved_report']}:
        reread=extract(after,locale,'utf-8')
        expected={r['id']:r['source'] for r in result['preserved_records'] if r['resource'].split('/')[1]==locale}
        if {r['id']:r['source'] for r in reread}!=expected:raise ValueError('Other locale logical text changed')
    return dict(changed_inner=[n for n in c.entries if c.read(n)!=after.read(n)],
                changed_outer=[n for n in z.entries if z.read(n)!=after_z.read(n)],
                member_order_preserved=True,dual_index_consistent=True,
                utf8_reextraction_records=len(result['rows']),
                preserved_locale_records=len(result['preserved_records']),
                original_movie_members_preserved=len(movies))


def modified(game,out,locale,include_images=True):
    ensure_output(game,out);validate_output_tree(out)
    media_output=out/'movie-assets' if include_images else None
    result=assemble(game,locale,include_images,media_output)
    checks=verify_resources(result)
    p=result['profile'];identity=result['identity'];original=result['original_zar'].data
    delta=make_delta(original,result['archive'])
    if apply_delta(original,delta)!=result['archive'] or apply_delta(result['archive'],delta,True)!=original:
        raise ValueError('Archive delta inverse failed')
    exe_restore=result['executable']
    if result['movie_recipe']:
        from movie_overlay import rollback_movie_overlay
        exe_restore=rollback_movie_overlay(exe_restore,result['movie_recipe'])
    if result['debug_recipe']:
        from debug_menu import rollback_debug
        exe_restore=rollback_debug(exe_restore,result['debug_recipe'])
    if result['overlay_recipe']:
        from audio_subtitles import rollback_overlay
        exe_restore=rollback_overlay(exe_restore,result['overlay_recipe'])
    exe_restore=rollback_bytes(apply_executable_patch(exe_restore,result['literal_recipe'],True),result['runtime_recipe'])
    if exe_restore!=(game/p['executable']).read_bytes():raise ValueError('Executable inverse failed')
    # Repeat independently from exact same sources before producing a manual sample.
    again=assemble(game,locale,include_images,media_output)
    if again['archive']!=result['archive'] or again['executable']!=result['executable']:
        raise ValueError(f'Nondeterministic build archive={digest(result["archive"])}!={digest(again["archive"])} exe={digest(result["executable"])}!={digest(again["executable"])}')
    (out/'MODIFIED_FILE.zar').write_bytes(result['archive'])
    (out/'MODIFIED_EXECUTABLE.exe').write_bytes(result['executable'])
    (out/'UTF8_RUNTIME.exe').write_bytes(result['utf8_executable'])
    (out/'full.binfont').write_bytes(result['font'])
    write_json(out/'DIFF_FILE.json',dict(schema=1,archive=delta,
        runtime=result['runtime_recipe'],literals=result['literal_recipe'],audio_overlay=result['overlay_recipe'],debug_menu=result['debug_recipe'],movie_overlay=result['movie_recipe']))
    for key in ('font_report','layout','hud','images','runtime'):
        write_json(out/(key.replace('_','-')+'.json'),result[key])
    from verify_locale_runtime import verify_locale_runtime
    native=verify_locale_runtime(game/p['executable'],out/'UTF8_RUNTIME.exe',
                          result['original_content'].read(p['font']),result['font'],result['rows'],result['runtime'])
    write_json(out/'native-replay.json',native)
    if result['preserved_records']:
        preserved_native=verify_locale_runtime(game/p['executable'],out/'UTF8_RUNTIME.exe',
            result['original_content'].read(p['font']),result['font'],result['preserved_records'],result['preserved_runtime'],
            verify_font_loader=False,measure_text=False,original_encoding='latin-1')
        write_json(out/'preserved-locales-replay.json',preserved_native)
        write_json(out/'preserved-locales.json',result['preserved_report'])
    if result['overlay_recipe']:
        from audio_subtitles import NativeOverlayReplay,verify_native_dispatch,verify_overlay_font,build_resource
        catalog=json.loads((ROOT/'locales'/locale/'audio-subtitles.json').read_text(encoding='utf-8'))
        overlay=result['overlay_recipe']
        overlay_exe=result['executable']
        if result['movie_recipe']:
            from movie_overlay import rollback_movie_overlay
            overlay_exe=rollback_movie_overlay(overlay_exe,result['movie_recipe'])
        if result['debug_recipe']:
            from debug_menu import rollback_debug
            overlay_exe=rollback_debug(overlay_exe,result['debug_recipe'])
        replay=NativeOverlayReplay(game/p['executable'],overlay_exe,overlay)
        replay_rows=[]
        for row in overlay['rows']:
            event=dict(cue_id=row['cue_id'],sample_rate=row['sample_rate'],position=(row['start']+row['end'])/2)
            calls=replay.render([event])
            if [call['text'] for call in calls]!=[row['text']]:raise ValueError('SFX cue runtime mismatch')
            replay_rows.append(dict(id=row['id'],calls=calls))
        write_json(out/'audio-replay.json',dict(cues=replay_rows,
            dispatch=verify_native_dispatch(game/p['executable'],catalog),
            font=verify_overlay_font(game/p['executable'],result['font'],overlay['rows']),
            game_launched=False))
        (out/'subtitles.sub1').write_bytes(build_resource(catalog))
    if result['debug_recipe']:
        from replay_debug_menu import verify_debug
        from debug_menu_text import load_catalog, verify_text, replay_debug_menu_text
        debug_exe=result['executable']
        if result['movie_recipe']:
            from movie_overlay import rollback_movie_overlay
            debug_exe=rollback_movie_overlay(debug_exe,result['movie_recipe'])
        write_json(out/'debug-replay.json',verify_debug((game/p['executable']).read_bytes(),debug_exe,result['debug_recipe']))
        catalog=load_catalog(ROOT/'locales'/locale/'debug-menu.json')
        write_json(out/'debug-text.json',verify_text(debug_exe,catalog,result['debug_recipe']['text'],BinFont(result['font'])))
        write_json(out/'debug-text-replay.json',replay_debug_menu_text(game/p['executable'],debug_exe,catalog,result['debug_recipe']['text'],BinFont(result['font'])))
    if result['movie_recipe']:
        from movie_overlay import verify_movie_overlay
        write_json(out/'movie-replay.json',verify_movie_overlay(game/p['executable'],result['executable'],result['movie_recipe'],result['movie_frames']))
    sample=out/'sample';sample.mkdir(exist_ok=True)
    if any(f.name not in {row['path'] for row in identity['files']} for f in sample.iterdir()):
        raise ValueError('Unexpected sample file')
    for row in identity['files']:
        name=row['path']
        source=out/'MODIFIED_FILE.zar' if name==p['archive'] else out/'MODIFIED_EXECUTABLE.exe' if name==p['executable'] else game/name
        shutil.copyfile(source,sample/name)
        if filehash(source)!=filehash(sample/name):raise ValueError('Sample identity mismatch')
    if manifest(game)!=identity['files']:raise ValueError('Original installation changed')
    report=dict(schema=1,locale=locale,field='loc/en/*; other-locale encoding; BMP font; decoder RVA 0xEA700; audio HUD RVA 0xBFF10; reviewed images; original IVF/DAT/OGG preserved; decoded-frame movie captions/annotations/titles RVA 0xBDBCA'+('; independent F1 raw48/action18; native enabled L3+Y; localized debug menu' if result['debug_recipe'] else ''),
        source_text_records=len(result['rows']),translated=sum(r['status']=='translated' for r in result['rows']),
        preserved=sum(r['status']!='translated' for r in result['rows']),added_glyphs=len(result['font_report']['added_glyphs']),
        ui_procedural=result['images'].get('image_count',0),ui_art=result['images'].get('art',{}).get('outer_count',0),
        ui_total=result['images'].get('image_count',0)+result['images'].get('art',{}).get('outer_count',0),**checks,
        original_sha256=digest(original),modified_sha256=digest(result['archive']),
        executable_sha256=digest(result['executable']),sample=str(sample.resolve()),
        reproducible=True,game_launched=False,game_visual_acceptance='NOT_TESTED',
        movie_dialogue_cues=result['images'].get('movies',{}).get('dialogue_cue_count',0),
        movie_onscreen_glosses=result['images'].get('movies',{}).get('onscreen_cue_count',0),
        movie_title_segments=result['images'].get('movies',{}).get('title_movie_count',0),
        inner_texture_localization=result['images'].get('art',{}).get('inner_count',0),
        audio_subtitle_cues=len(result['overlay_recipe']['rows']) if result['overlay_recipe'] else 0)
    write_json(out/'build-report.json',report)
    print(f'MODIFIED PASS records={len(result["rows"])} UTF8=roundtrip glyphs={len(BinFont(result["font"]).glyphs)} dual-index=consistent reproducible=true native-replay=PASS game-launched=false')


def rollback(out):
    ensure_output(ROOT/'original',out);validate_output_tree(out)
    recipes=json.loads((out/'DIFF_FILE.json').read_text(encoding='utf-8'))
    restored=apply_delta((out/'MODIFIED_FILE.zar').read_bytes(),recipes['archive'],True)
    exe=(out/'MODIFIED_EXECUTABLE.exe').read_bytes()
    if recipes.get('movie_overlay'):
        from movie_overlay import rollback_movie_overlay
        exe=rollback_movie_overlay(exe,recipes['movie_overlay'])
    if recipes.get('debug_menu'):
        from debug_menu import rollback_debug
        exe=rollback_debug(exe,recipes['debug_menu'])
    if recipes.get('audio_overlay'):
        from audio_subtitles import rollback_overlay
        exe=rollback_overlay(exe,recipes['audio_overlay'])
    exe=apply_executable_patch(exe,recipes['literals'],True)
    exe=rollback_bytes(exe,recipes['runtime'])
    sample=out/'rollback-sample';sample.mkdir(exist_ok=True)
    (sample/'rom.zar').write_bytes(restored);(sample/'Dementium.exe').write_bytes(exe)
    p,i,d,fp=configuration('zh-CN')
    z=Zar(restored);c=Content(z.read(p['content']));rows=extract(c,'en','latin-1')
    if next(r['source'] for r in rows if r['id']=='loc/en/UISSFrontend.tbl:0000')!='New Game':
        raise ValueError('Restored original menu mismatch')
    if digest(exe)!=recipes['runtime']['original_sha256']:raise ValueError('Restored executable mismatch')
    if filehash(out/'MODIFIED_FILE.zar')!=recipes['archive']['modified_sha256']:
        raise ValueError('Modified output not retained')
    print('ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('baseline','modified','rollback'))
    parser.add_argument('--game',type=Path)
    parser.add_argument('--locale',default='zh-CN')
    parser.add_argument('--output',type=Path,default=ROOT/'build/full')
    parser.add_argument('--text-only',action='store_true',help='Intermediate text pipeline; not full localization')
    args=parser.parse_args()
    if args.command=='rollback':rollback(args.output)
    elif args.game is None:parser.error('--game is required')
    elif args.command=='baseline':baseline(args.game,args.output,args.locale)
    else:modified(args.game,args.output,args.locale,not args.text_only)


if __name__=='__main__':main()
