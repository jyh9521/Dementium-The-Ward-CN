"""Offline size ablation: preserve original movies, NOT a playable release.

All non-movie member bytes are taken from a hash-bound existing candidate.
The resulting archive intentionally lacks movie translations; this measures
payload size only and is never copied to dist or installed.
"""
import argparse
import json
import shutil
from pathlib import Path

from source_delta import build, apply
from workspace_io import validate_output_tree
from zar import Zar, digest, filehash, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['baseline', 'modified', 'rollback'])
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    if not out.is_relative_to(ROOT / 'build'):
        raise ValueError('Research output must stay under repository build/')
    if any(x.resolve().is_relative_to(out) for x in (a.source, a.candidate)):
        raise ValueError('Research output contains an input')
    validate_output_tree(out if out.exists() else out.parent)
    out.mkdir(parents=True, exist_ok=True)
    identities = json.loads((ROOT/'assets/original-identity.json').read_text(encoding='utf-8'))
    original = next(f for f in identities['files'] if f['path']=='rom.zar')
    reference = json.loads((ROOT/'build/installer/payload-report.json').read_text(encoding='utf-8'))[0]
    if filehash(a.source) != original['sha256'] or filehash(a.candidate) != reference['target_sha256']:
        raise ValueError('Original or existing release candidate identity mismatch')
    if a.mode == 'baseline':
        z = Zar(a.source.read_bytes())
        assert z.rebuild({}) == z.data
        print('BASELINE PASS original-noop=identical source-sha256='+original['sha256'])
    elif a.mode == 'modified':
        z, c = Zar(a.source.read_bytes()), Zar(a.candidate.read_bytes())
        assert list(z.entries) == list(c.entries)
        changes, movies = {}, []
        for name in z.entries:
            if name == '~INDEX':
                continue
            old, new = z.read(name), c.read(name)
            if old != new:
                if name.startswith('MOVIES/'):
                    movies.append(dict(name=name, original_size=len(old), modified_size=len(new)))
                else:
                    changes[name] = new
        target = out/'MODIFIED_FILE.zar'
        target.write_bytes(z.rebuild(changes))
        check = Zar(target.read_bytes())
        media = [n for n in z.entries if n.startswith('MOVIES/')]
        assert all(check.read(n) == z.read(n) for n in media)
        assert all(check.read(n) == c.read(n) for n in changes)
        stats = build(a.source, target, out/'DIFF_FILE.gz')
        apply(a.source, out/'DIFF_FILE.gz', out/'delta-roundtrip.zar', stats)
        assert filehash(out/'delta-roundtrip.zar') == filehash(target)
        write_json(out/'measurement.json', dict(
            purpose='size-only ablation; movie translations absent; NOT a release',
            candidate_sha256=filehash(a.candidate), original_sha256=original['sha256'],
            preserved_movie_members=len(media), removed_movie_edits=movies,
            retained_nonmovie_changes=list(changes), delta=stats,
            previous_payload_size=reference['payload_size'],
            saved_payload_bytes=reference['payload_size']-stats['payload_size'],
            hypothetical_installer_bytes=(ROOT/'dist/Dementium-The-Ward-zh-CN-Setup.exe').stat().st_size-reference['payload_size']+stats['payload_size'],
            estimate_note='arithmetic only, excludes future overlay code/resources and publish compression changes'))
        print(f'MODIFIED PASS preserved-movie-members={len(media)} removed-movie-edits={len(movies)} nonmovie-changes={len(changes)} delta-bytes={stats["payload_size"]} roundtrip=identical NOT-A-RELEASE')
    else:
        measurement=json.loads((out/'measurement.json').read_text(encoding='utf-8'))
        assert filehash(out/'MODIFIED_FILE.zar')==measurement['delta']['target_sha256']
        # Exercise restoration on a separate copy; leave MODIFIED_FILE changed.
        sample=out/'rollback-sample.zar'
        shutil.copyfile(out/'MODIFIED_FILE.zar', sample)
        assert filehash(sample)==measurement['delta']['target_sha256']
        shutil.copyfile(a.source, sample)
        assert filehash(sample)==original['sha256']
        assert filehash(out/'MODIFIED_FILE.zar')==measurement['delta']['target_sha256']
        print('ROLLBACK PASS separate-copy=original modified-file=retained source=unchanged')
    assert filehash(a.source)==original['sha256']
    assert filehash(a.candidate)==reference['target_sha256']


if __name__ == '__main__':
    main()
