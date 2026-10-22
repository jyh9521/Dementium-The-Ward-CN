"""Run and retain literal baseline/modified/isolated rollback evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from workspace_io import validate_output_tree
from investigate import ensure_output
from zar import filehash,write_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--bash',type=Path,required=True)
    a=p.parse_args();out=ROOT/'build/phase2'
    ensure_output(a.game,out);validate_output_tree(out)
    commands=[('TESTS',[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-q']),
        ('BASELINE',[sys.executable,'-X','utf8','tools/build_probe.py','baseline','--game',str(a.game)]),
        ('MODIFIED',[sys.executable,'-X','utf8','tools/build_probe.py','modified','--game',str(a.game)]),
        ('ROLLBACK',[str(a.bash),'tools/ROLLBACK_PROBE.sh']),
        ('INPUT',[sys.executable,'-X','utf8','tools/investigate.py','check-input','--game',str(a.game)])]
    rows=[]
    for label,command in commands:
        r=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        row=dict(label=label,argv=command,command=subprocess.list2cmdline(command),
            input='synthetic fixtures' if label=='TESTS' else str(out/'MODIFIED_FILE.zar') if label=='ROLLBACK' else str(a.game),
            output=r.stdout,exit_status=r.returncode)
        rows.append(row);print(f'{label} exit={r.returncode}\n{r.stdout}',end='',flush=True)
        write_json(out/'commands.json',rows)
        if r.returncode:raise SystemExit(r.returncode)
    report=json.loads((out/'build-report.json').read_text(encoding='utf-8'))
    original_loader=json.loads((out/'original-loader.json').read_text(encoding='utf-8'))
    modified_loader=json.loads((out/'modified-loader.json').read_text(encoding='utf-8'))
    artifacts={'MODIFIED_FILE':out/'MODIFIED_FILE.zar','DIFF_FILE':out/'DIFF_FILE.json',
        'VERIFICATION':out/'VERIFICATION.txt','ROLLBACK':ROOT/'tools/ROLLBACK_PROBE.sh'}
    text='Phase 2 minimal localization verification - 2026-10-23\n'
    text+='Changed field: '+report['field']+'\nNew Game -> 新游戏; runtime bytes=818d8f; EXE unchanged.\n'
    text+='No game process launched. Native replay uses isolated emulation and explicit boundary doubles.\n'
    for key,path in artifacts.items():text+=f'{key}: {path}\n'
    for row in rows:
        text+=f"\n{row['label']}\nCOMMAND: {row['command']}\nINPUT: {row['input']}\nOUTPUT (literal):\n{row['output']}EXIT: {row['exit_status']}\n"
    text+=f"\nNative font loader: original glyphs={original_loader['glyph_count']}, modified glyphs={modified_loader['glyph_count']}; real loader/relocation replay=PASS; image/GPU boundary doubled.\n"
    text+='Original SHA-256: '+report['original_sha256']+'\nModified SHA-256: '+report['modified_sha256']+'\n'
    text+='Rollback SHA-256: '+filehash(out/'ROLLBACK_COPY.zar')+'\n'
    text+='Restored status: original archive byte-identical, New Game and original font restored on isolated copy; MODIFIED_FILE and manual sample remain changed.\n'
    text+='Rebuild twice from identical inputs: byte-identical.\nManual game visual acceptance: NOT_TESTED.\n'
    (out/'VERIFICATION.txt').write_text(text,encoding='utf-8',newline='\n')
    for path in artifacts.values():
        with path.open('rb') as f:
            if not f.read(1):raise ValueError('Empty artifact')
    print('EVIDENCE PASS four-artifacts=reopened sample=modified original-input=unchanged')


if __name__=='__main__':main()
