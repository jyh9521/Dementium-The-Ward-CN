"""Execute reproducible phase-one checks and retain literal command evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from zar import filehash,write_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--bash',type=Path,required=True)
    args=p.parse_args()
    out=ROOT/'build/phase1';out.mkdir(parents=True,exist_ok=True)
    commands=[('SCAN',[sys.executable,'-X','utf8','tools/investigate.py','scan','--game',str(args.game)]),
        ('TESTS',[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-v']),
        ('BASELINE',[sys.executable,'-X','utf8','tools/investigate.py','baseline','--game',str(args.game)]),
        ('MODIFIED',[sys.executable,'-X','utf8','tools/investigate.py','modified','--game',str(args.game)]),
        ('ROLLBACK',[str(args.bash),'tools/ROLLBACK.sh']),
        ('INPUT',[sys.executable,'-X','utf8','tools/investigate.py','check-input','--game',str(args.game)])]
    record=[]
    for label,command in commands:
        result=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        row=dict(label=label,argv=command,command=subprocess.list2cmdline(command),input=str(args.game) if label not in ('TESTS','ROLLBACK') else ('synthetic fixtures' if label=='TESTS' else str(out/'MODIFIED_FILE.zar')),
                 output=result.stdout,exit_status=result.returncode)
        record.append(row)
        print(f'{label} exit={result.returncode}\n{result.stdout}',end='',flush=True)
        if result.returncode:
            write_json(out/'commands.json',record)
            raise SystemExit(result.returncode)
    artifacts={'MODIFIED_FILE':str(out/'MODIFIED_FILE.zar'),'DIFF_FILE':str(out/'DIFF_FILE.json'),
        'VERIFICATION':str(out/'VERIFICATION.txt'),'ROLLBACK':str(ROOT/'tools/ROLLBACK.sh')}
    report=json.loads((out/'probe-report.json').read_text(encoding='utf-8'))
    text='Phase 1 verification - 2026-10-23\nGame was not launched; installation input was read-only.\n'
    text+='Changed field: '+report['id']+'\nNew Game -> New Game [offline probe] (ASCII archive probe, not Chinese proof)\n'
    for name,path in artifacts.items():text+=f'{name}: {path}\n'
    for row in record:
        text+=f"\n{row['label']}\nCOMMAND: {row['command']}\nINPUT: {row['input']}\nOUTPUT (literal):\n{row['output']}EXIT: {row['exit_status']}\n"
    text+='\nOriginal SHA-256: '+report['original_sha256']+'\nModified SHA-256: '+report['modified_sha256']
    text+='\nRollback SHA-256: '+filehash(out/'ROLLBACK_COPY.zar')+'\nRestored behavior/status: field=New Game; original archive byte-identical; modified output retained.\nRuntime/Chinese display: NOT_TESTED.\n'
    (out/'VERIFICATION.txt').write_text(text,encoding='utf-8',newline='\n')
    write_json(out/'commands.json',record)
    for name,path in artifacts.items():
        with Path(path).open('rb') as f:
            if not f.read(1):raise ValueError('Empty artifact: '+name)
    print('EVIDENCE PASS four-artifacts=reopened')


if __name__=='__main__':main()
