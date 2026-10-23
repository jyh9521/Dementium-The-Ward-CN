"""Read-only text-source coverage audit; emits local research metadata only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import struct
import zlib
from content import Content, TOKEN
from zar import Zar, digest


def unwrap(raw: bytes, max_layers: int = 4):
    """Decode observed length-prefixed zlib wrappers; retain each layer identity."""
    layers = []
    for _ in range(max_layers):
        if len(raw) < 14:
            break
        usize, csize, aligned = struct.unpack_from('<3I', raw)
        if not (0 < csize <= len(raw) - 12 and aligned == len(raw)):
            break
        try:
            decoded = zlib.decompress(raw[12:12+csize])
        except zlib.error:
            break
        if len(decoded) != usize:
            raise ValueError('Length-prefixed zlib size mismatch')
        layers.append(dict(size=len(raw), usize=usize, csize=csize, aligned=aligned))
        raw = decoded
    return raw, layers


def candidates(raw, minimum=4):
    return [dict(offset=m.start(), text=m.group().decode('ascii'))
            for m in re.finditer(rb'[ -~]{%d,}' % minimum, raw)]


def review(records, original):
    by_id = {r['id']:r for r in original}
    ids = [r['id'] for r in records]
    issues = []
    for r in records:
        source = by_id.get(r['id'])
        if source is None:
            issues.append(dict(id=r['id'], issue='unknown-id')); continue
        for key, value in source.items():
            if key not in {'target','status','notes'} and r.get(key) != value:
                issues.append(dict(id=r['id'],issue='metadata-'+key))
        if not r.get('target'):
            issues.append(dict(id=r['id'],issue='empty-target'))
        if TOKEN.findall(r['source']) != TOKEN.findall(r['target']):
            issues.append(dict(id=r['id'],issue='token-order'))
        if re.findall(r'\r\n|\r|\n',r['source']) != re.findall(r'\r\n|\r|\n',r['target']):
            issues.append(dict(id=r['id'],issue='newline-sequence'))
        if [bool(x) for x in re.split(r'\r\n|\r|\n',r['source'])] != [bool(x) for x in re.split(r'\r\n|\r|\n',r['target'])]:
            issues.append(dict(id=r['id'],issue='blank-line-position'))
    return dict(records=len(records), unique_ids=len(set(ids)), missing_ids=sorted(set(by_id)-set(ids)),
                duplicate_ids=sorted({i for i in ids if ids.count(i)>1}), structural_issues=issues,
                preserved_source=[r['id'] for r in records if r['target']==r['source']])


def audit(game, root):
    profile=json.loads((root/'assets/game-profile.json').read_text(encoding='utf-8'))
    z=Zar((game/profile['archive']).read_bytes())
    c=Content(z.read(profile['content']))
    raw,layers=unwrap(c.read('stringpool'))
    strings=candidates(raw)
    config=[]
    for n,e in c.entries.items():
        if n.startswith('config/') and e.isfile():
            b=c.read(n)
            config.append(dict(resource=n,size=len(b),sha256=digest(b),candidates=candidates(b)))
    movies=[]
    for n in z.entries:
        if n.endswith('.DAT'):
            b=z.read(n)
            version,frames=struct.unpack_from('<II',b)
            movies.append(dict(resource=n,size=len(b),sha256=digest(b),version=version,frames=frames,
                               size_equals_24_plus_24_frames=len(b)==24+24*frames,
                               printable_candidates=candidates(b,12)))
    allr=[]
    for name in ['strings-documents.json','strings-ui-items.json']:
        allr+=json.loads((root/'locales/zh-CN'/name).read_text(encoding='utf-8'))
    original=json.loads((root/'build/phase1/text-en.json').read_text(encoding='utf-8'))
    return dict(review=review(allr,original),
        stringpool=dict(resource='CONTENT.TAR/stringpool',size=len(raw),sha256=digest(raw),layers=layers,candidates=strings),
        config=config,movie_dat=movies,
        movie_ogg=[dict(resource=n,size=z.entries[n].size,magic=z.read(n)[:4].hex()) for n in z.entries if n.endswith('.OGG')],
        unreviewed_media='Speech, burned-in video titles, texture text and EXE runtime strings are not covered by 278 table/document records.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();root=Path(__file__).resolve().parents[1]
    out=a.out.resolve()
    if root/'build' not in out.parents or a.game.resolve() in out.parents:
        raise ValueError('Audit output must remain in project build/')
    report=audit(a.game,root);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TEXT AUDIT records=%d missing=%d structural-issues=%d stringpool-candidates=%d config-files=%d movie-DAT=%d movie-OGG=%d' % (
        report['review']['records'],len(report['review']['missing_ids']),len(report['review']['structural_issues']),
        len(report['stringpool']['candidates']),len(report['config']),len(report['movie_dat']),len(report['movie_ogg'])))

if __name__=='__main__':main()
