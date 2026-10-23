"""Recheck reviewed art and exact preservation using a user-supplied original archive."""
from pathlib import Path
import argparse
import hashlib
import json
from build_art import build_art
from content import Content
from zar import Zar
from workspace_io import validate_output_tree


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=root/'build/image-readability/art-review-verification.json')
    args=parser.parse_args()
    output=args.output.absolute()
    if root/'build' not in output.parents or output.suffix!='.json':
        raise ValueError('Review output must be JSON under repository build directory')
    validate_output_tree(root/'build')
    source=args.archive.resolve()
    data=source.read_bytes()
    identity=json.loads((root/'assets/original-identity.json').read_text(encoding='utf8'))
    # Every individual art source is hash-bound in build_art; also bind the whole archive.
    profile=json.loads((root/'assets/game-profile.json').read_text(encoding='utf8'))
    expected=next(e['sha256'] for e in identity['files'] if e['path']==profile['archive'])
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Original archive identity mismatch')
    z=Zar(data);c=Content(z.read(profile['content']));config=root/'locales/zh-CN/art-patches.json'
    inner,outer,report=build_art(z,c,config)
    inner2,outer2,_=build_art(z,c,config)
    if (inner,outer)!=(inner2,outer2):raise ValueError('Art repeat build differs')
    rebuilt=Content(c.rebuild(inner))
    for entry in report['preserved_sources']:
        if rebuilt.read(entry['resource'])!=c.read(entry['resource']):
            raise ValueError('Withdrawn art did not preserve source: '+entry['resource'])
        entry['rebuilt_resource_sha256']=hashlib.sha256(rebuilt.read(entry['resource'])).hexdigest()
        entry['verified_byte_identical_after_tar_rebuild']=True
    report.update(input_archive=str(source),input_sha256=expected,repeat_build_identical=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    # Reopen the claimed report and check the persisted evidence.
    if json.loads(output.read_text(encoding='utf8'))!=report:raise ValueError('Report persistence mismatch')
    print(f"IMAGE READABILITY PASS retained={len(inner)+len(outer)} withdrawn={len(report['preserved_sources'])} repeated=identical preserved-after-tar=byte-identical no-game-launch")


if __name__=='__main__':main()
