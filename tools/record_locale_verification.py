"""Execute and retain literal baseline/modified/isolated rollback receipts."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from investigate import ensure_output,manifest
from workspace_io import validate_output_tree
from zar import filehash,write_json

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'build/full')
    p.add_argument('--locale',default='zh-CN')
    a=p.parse_args();game=a.game.resolve();out=a.output.resolve()
    ensure_output(game,out);validate_output_tree(out)
    before=manifest(game);steps=[]
    for phase in ('baseline','modified','rollback'):
        command=[sys.executable,'-X','utf8',str(ROOT/'tools/build_locale.py'),phase,
                 '--game',str(game),'--output',str(out),'--locale',a.locale]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        step=dict(phase=phase.upper(),command=command,cwd=str(ROOT),input=str(game) if phase!='rollback' else str(out/'MODIFIED_FILE.zar'),
                  stdout=result.stdout,stderr=result.stderr,exit_status=result.returncode)
        steps.append(step)
        (out/(phase+'.stdout.txt')).write_text(result.stdout,encoding='utf-8')
        (out/(phase+'.stderr.txt')).write_text(result.stderr,encoding='utf-8')
        print(result.stdout,end='',flush=True)
        if result.returncode:
            write_json(out/'verification-failure.json',steps)
            raise RuntimeError(phase+' failed: '+result.stderr)
    if manifest(game)!=before:raise ValueError('Original installation changed')
    shutil.copyfile(ROOT/'ROLLBACK_LOCALE.sh',out/'ROLLBACK.sh')
    (out/'ROLLBACK.sh').chmod(0o755)
    report=json.loads((out/'build-report.json').read_text(encoding='utf-8'))
    artifacts={name:str((out/name).resolve()) for name in ['MODIFIED_FILE.zar','DIFF_FILE.json','VERIFICATION.txt','ROLLBACK.sh']}
    receipt=dict(field=report['field'],locale=a.locale,artifacts=artifacts,steps=steps,
                 restored_behavior='Original New Game, original font and byte-widen decoder in isolated rollback-sample',
                 modified_retained=True,original_input_unchanged=True,game_launched=False,
                 visual_acceptance='NOT_TESTED',modified_archive_sha256=filehash(out/'MODIFIED_FILE.zar'))
    write_json(out/'verification.json',receipt)
    lines=['FIELD: '+report['field'],'LOCALE: '+a.locale]
    lines.extend(f'{k}: {v}' for k,v in artifacts.items())
    for step in steps:
        lines.extend(['',step['phase'],'COMMAND: '+subprocess.list2cmdline(step['command']),
            'CWD: '+step['cwd'],'INPUT: '+step['input'],'STDOUT:',step['stdout'].rstrip(),
            'STDERR:',step['stderr'].rstrip(),'EXIT STATUS: '+str(step['exit_status'])])
    lines.extend(['','RESTORED: '+receipt['restored_behavior'],'MODIFIED: retained',
        'INPUT: all original installation identities unchanged','GAME LAUNCHED: false','IN-GAME ACCEPTANCE: NOT_TESTED'])
    (out/'VERIFICATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Reopen all four claimed deliverables, including large artifacts via hashing.
    for name,path in artifacts.items():
        target=Path(path)
        if not target.is_file() or not target.stat().st_size:raise ValueError('Missing deliverable '+name)
        filehash(target)
    print('VERIFICATION PASS baseline=0 modified=0 rollback=0 artifacts=4 reopened input=unchanged game-launched=false')

if __name__=='__main__':main()
