"""Read-only game survey and isolated archive probe. Python standard library only."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
from content import Content, extract, import_text, text_kind, verify_index
from zar import Zar, digest, filehash, write_json, make_delta, apply_delta

ROOT = Path(__file__).resolve().parents[1]


def manifest(game):
    rows = []
    for path in sorted(game.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in game input')
        if not path.is_file():
            continue
        with path.open('rb') as f:
            head = f.read(32)
        row = dict(path=path.relative_to(game).as_posix(), size=path.stat().st_size,
                   sha256=filehash(path), magic_hex=head.hex())
        if head.startswith(b'MZ'):
            raw = path.read_bytes()
            off = struct.unpack_from('<I', raw, 60)[0]
            if raw[off:off+4] != b'PE\0\0':
                raise ValueError('Invalid PE signature')
            machine, sections, timestamp = struct.unpack_from('<HHI', raw, off+4)
            optional_size = struct.unpack_from('<H', raw, off+20)[0]
            row['pe'] = dict(machine=hex(machine), architecture={0x8664:'x64',0x14c:'x86'}.get(machine,'unknown'),
                timestamp=timestamp, optional_magic=hex(struct.unpack_from('<H',raw,off+24)[0]),
                sections=[raw[off+24+optional_size+i*40:off+32+optional_size+i*40].rstrip(b'\0').decode('ascii') for i in range(sections)])
        rows.append(row)
    return rows


def ensure_output(game, out):
    game, out = game.resolve(), out.resolve()
    if out == game or game in out.parents or out == ROOT or ROOT not in out.parents or 'build' not in out.relative_to(ROOT).parts:
        raise ValueError('Output must be in project build directory, outside game input')
    out.mkdir(parents=True, exist_ok=True)


def load(game, profile, identity=None):
    raw = (game/profile['archive']).read_bytes()
    if identity:
        expected = next(f for f in identity['files'] if f['path'] == profile['archive'])
        if len(raw) != expected['size'] or digest(raw) != expected['sha256']:
            raise ValueError('Unsupported original archive')
    z = Zar(raw)
    verify_index(z, profile['external_index'])
    return z, Content(z.read(profile['content']))


def survey(game, out, profile):
    ensure_output(game, out)
    files = manifest(game)
    steam = game.parent.parent / f"appmanifest_{profile['appid']}.acf"
    acf = steam.read_text(encoding='utf-8')
    fields = {k:re.search(r'"'+k+r'"\s+"([^"]+)"', acf).group(1) for k in ('appid','buildid','installdir')}
    if fields['appid'] != profile['appid'] or fields['installdir'] != game.name:
        raise ValueError('Steam manifest identity mismatch')
    identity = dict(platform='Steam Windows PC', observed_date='2026-10-23', steam=fields,
        manifest_sha256=filehash(steam), files=files)
    write_json(out/'original-identity.json', identity)
    z, c = load(game, profile)
    outer = [dict(name=n, offset=e.offset, size=e.size, sha256=digest(z.read(n)), magic_hex=z.read(n)[:16].hex()) for n,e in z.entries.items()]
    inner = [dict(name=n, offset=e.offset, data_offset=e.offset_data, size=e.size,
        type='file' if e.isfile() else 'directory', sha256=digest(c.read(n)), magic_hex=c.read(n)[:16].hex()) for n,e in c.entries.items()]
    write_json(out/'archive-manifest.json', outer)
    write_json(out/'content-manifest.json', inner)
    all_records = []
    counts = {}
    for locale in sorted({n.split('/')[1] for n in c.entries if text_kind(n)}):
        records = extract(c, locale, profile['inventory_encoding'])
        write_json(out/f'text-{locale}.json', records)
        all_records.extend(records)
        counts[locale] = dict(resources=len({r['resource'] for r in records}), records=len(records),
            unique=len({r['source'] for r in records}), translated=0,
            ascii_resources=sum(all(b < 128 for b in c.read(n)) for n in {r['resource'] for r in records}))
    candidates = []
    for f in files:
        if not f.get('pe'):
            continue
        raw = (game/f['path']).read_bytes()
        for pattern, enc in [(rb'[ -~]{5,}', 'ascii'), (rb'(?:[ -~]\x00){5,}', 'utf-16le')]:
            for m in re.finditer(pattern, raw):
                candidates.append(dict(file=f['path'],offset=m.start(),encoding=enc,text=m.group().decode(enc),status='unclassified-candidate'))
    write_json(out/'executable-string-candidates.json', candidates)
    pngs = []
    textures = []
    for n in z.entries:
        raw = z.read(n)
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):
            pngs.append(dict(resource=n,width=struct.unpack_from('>I',raw,16)[0],height=struct.unpack_from('>I',raw,20)[0]))
        elif n.endswith('.PNG'):
            textures.append(dict(resource=n,format='non-PNG binary container; fields unverified',
                first_24_bytes=raw[:24].hex(),header_u32=list(struct.unpack_from('<6I',raw))))
    font = c.read(profile['font'])
    summary = dict(zar_header=list(struct.unpack_from('<8I',z.data)), outer_members=len(z.entries),
        tar_members=len(c.entries), tar_files=sum(e.isfile() for e in c.entries.values()),
        outer_extensions=dict(Counter(Path(n).suffix for n in z.entries)),
        vfs_rows=len(verify_index(z,profile['external_index'])), png_count=len(pngs), binary_texture_count=len(textures),
        locale_counts=counts, extracted_text_resources=sum(v['resources'] for v in counts.values()),
        text_recognition_coverage='100% of known loc/* table/document grammar, not all visible text',
        unclassified_localization_files=[n for n,e in c.entries.items() if n.startswith('loc/') and e.isfile() and not text_kind(n)],
        image_text_coverage='unreviewed', executable_candidates=len(candidates),
        font=dict(resource=profile['font'],size=len(font),sha256=digest(font),first_32_bytes=font[:32].hex(),
            chinese_coverage='unverified', format='binary; layout and decoder unverified'),
        runtime_tested=False)
    write_json(out/'coverage.json',summary)
    write_json(out/'images.json',pngs)
    write_json(out/'binary-textures.json',textures)
    print(f"SCAN appid={fields['appid']} build={fields['buildid']} files={len(files)} ZAR={len(z.entries)} TAR={len(c.entries)} EN={counts['en']['records']}/{counts['en']['resources']} PNG={len(pngs)}")


def baseline(game, out, profile, identity):
    ensure_output(game,out)
    z,c=load(game,profile,identity)
    if z.rebuild({n:z.read(n) for n in z.entries}) != z.data:
        raise ValueError('ZAR no-op changed bytes')
    records=extract(c,profile['source_locale'],profile['inventory_encoding'])
    if c.rebuild({n:c.read(n) for n,e in c.entries.items() if e.isfile()}) != c.data or import_text(c,records,profile['source_locale'],profile['inventory_encoding']):
        raise ValueError('TAR/text no-op changed bytes')
    print(f'BASELINE PASS ZAR={len(z.entries)} TAR={len(c.entries)} records={len(records)} noop=byte-identical dual-index=consistent')


def modified(game,out,profile,identity):
    ensure_output(game,out)
    z,c=load(game,profile,identity)
    records=extract(c,profile['source_locale'],profile['inventory_encoding'])
    hits=[r for r in records if r['resource']==profile['probe_resource'] and r['source']==profile['probe_source']]
    if len(hits)!=1:
        raise ValueError('Probe source ambiguous')
    hits[0]['target']=profile['probe_target']
    replacements=import_text(c,records,profile['source_locale'],profile['inventory_encoding'])
    rebuilt=c.rebuild(replacements)
    result=z.rebuild({profile['content']:rebuilt})
    parsed=Zar(result);verify_index(parsed,profile['external_index'])
    after=Content(parsed.read(profile['content']))
    if list(parsed.entries)!=list(z.entries):
        raise ValueError('ZAR order changed')
    changed=[n for n in z.entries if z.read(n)!=parsed.read(n)]
    if set(changed) != {profile['content']}:
        raise ValueError('Unexpected outer changes')
    if [n for n in c.entries if c.read(n)!=after.read(n)] != [profile['probe_resource']]:
        raise ValueError('Unexpected inner changes')
    reread=extract(after,profile['source_locale'],profile['inventory_encoding'])
    for a,b in zip(records,reread,strict=True):
        if b['source'] != (a['target'] or a['source']) or b['tokens']!=a['tokens']:
            raise ValueError('Text roundtrip mismatch')
    # Separately force growth across a TAR 512-byte boundary and test both ZAR/VFS sizes.
    growth=c.rebuild({profile['probe_resource']:c.read(profile['probe_resource'])+b' '*600})
    grown=Zar(z.rebuild({profile['content']:growth}))
    verify_index(grown,profile['external_index'])
    if grown.entries[profile['content']].size <= z.entries[profile['content']].size:
        raise ValueError('Growth probe did not grow')
    patch=make_delta(z.data,result)
    if apply_delta(z.data,patch)!=result or apply_delta(result,patch,reverse=True)!=z.data:
        raise ValueError('Delta roundtrip mismatch')
    (out/'MODIFIED_FILE.zar').write_bytes(result)
    write_json(out/'DIFF_FILE.json',patch)
    write_json(out/'probe-report.json',dict(resource=hits[0]['resource'],id=hits[0]['id'],
        source=hits[0]['source'],target=hits[0]['target'],changed_outer=changed,
        original_sha256=digest(z.data),modified_sha256=digest(result),
        original_size=len(z.data),modified_size=len(result),
        growth_original=len(c.data),growth_modified=len(growth),
        runtime_tested=False,chinese_tested=False))
    print(f"MODIFIED PASS field={hits[0]['id']} changed_outer={len(changed)} changed_inner=1 tokens=preserved delta=roundtrip growth-dual-index=consistent")


def rollback(out,profile):
    patch=json.loads((out/'DIFF_FILE.json').read_text(encoding='utf-8'))
    # Restores an additional isolated output; intentionally retains MODIFIED_FILE.
    restored=apply_delta((out/'MODIFIED_FILE.zar').read_bytes(),patch,reverse=True)
    target=out/'ROLLBACK_COPY.zar'
    target.write_bytes(restored)
    if filehash(target)!=patch['original_sha256']:
        raise ValueError('Restored identity mismatch')
    content=Content(Zar(target.read_bytes()).read(profile['content']))
    row=extract(content,profile['source_locale'],profile['inventory_encoding'])
    if not any(r['resource']==profile['probe_resource'] and r['source']==profile['probe_source'] for r in row):
        raise ValueError('Original field not restored')
    print('ROLLBACK PASS isolated-copy=original-sha256 field=New Game modified-file=retained')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('scan','baseline','modified','rollback','check-input'))
    parser.add_argument('--game',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'build/phase1')
    parser.add_argument('--profile',type=Path,default=ROOT/'assets/game-profile.json')
    parser.add_argument('--identity',type=Path,default=ROOT/'assets/original-identity.json')
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text(encoding='utf-8'))
    if args.command=='rollback':
        ensure_output(ROOT/'original',args.output)
        rollback(args.output,profile)
    elif args.command=='scan':
        if args.game is None: parser.error('--game required')
        survey(args.game,args.output,profile)
    else:
        if args.game is None: parser.error('--game required')
        identity=json.loads(args.identity.read_text(encoding='utf-8'))
        if args.command=='check-input':
            if manifest(args.game)!=identity['files']:
                raise ValueError('Game installation changed')
            print('INPUT PASS all-files=original-sha256 game-not-launched=true')
        else:
            globals()[args.command](args.game,args.output,profile,identity)


if __name__=='__main__':
    main()
