"""Read-only identity check for a user-operated local sample; no launch."""
import argparse,json
from pathlib import Path
from zar import filehash

ROOT=Path(__file__).resolve().parents[1]

def verify(directory,report,identity,restored=False):
    expected={r['path']:dict(sha256=r['sha256'],size=r['size']) for r in identity['files']}
    if not restored:
        expected['rom.zar']=dict(sha256=report['modified_sha256'],size=None)
        expected['Dementium.exe']=dict(sha256=report['executable_sha256'],size=None)
    for name,row in expected.items():
        path=Path(directory)/name
        if not path.is_file() or filehash(path)!=row['sha256'] or (row['size'] is not None and path.stat().st_size!=row['size']):
            raise ValueError('Sample identity mismatch: '+name)
    return len(expected)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/full')
    p.add_argument('--sample',type=Path)
    p.add_argument('--restored',action='store_true')
    a=p.parse_args();out=a.output.resolve();sample=a.sample or out/'sample'
    report=json.loads((out/'build-report.json').read_text(encoding='utf-8'))
    identity=json.loads((ROOT/'assets/original-identity.json').read_text(encoding='utf-8'))
    count=verify(sample,report,identity,a.restored)
    print(f'SAMPLE PASS files={count} mode={"original" if a.restored else "localized"} hashes=exact game-launched=false')

if __name__=='__main__':main()
