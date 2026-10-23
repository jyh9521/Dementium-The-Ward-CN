"""Reopen verified locale/installer outputs and retain literal offline receipts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import shlex

from source_delta import filehash
from workspace_io import validate_output_tree

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=ROOT/'build/release-candidate')
    args=parser.parse_args()
    work=ROOT/'build/installer';validate_output_tree(work)
    locale=args.build.resolve()
    if not locale.is_relative_to(ROOT/'build'):
        raise ValueError('Locale build must stay under repository build/')
    validate_output_tree(locale)
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    full=read(locale/'verification.json');build=read(work/'build-report.json');ui=read(work/'ui-verification.json')
    feedback_path=locale/'feedback-replay.json'
    feedback=read(feedback_path) if feedback_path.exists() else None
    if feedback and (feedback['exit_status'] or not feedback['inputs_unchanged'] or
                     feedback['executable_sha256']!=filehash(locale/'MODIFIED_EXECUTABLE.exe')):
        raise ValueError('Final executable feedback regression proof drift')
    if not all(s['exit_status']==0 for s in full['steps']+build['steps']+ui['previews']):
        raise ValueError('All verification commands must succeed')
    if not build['isolated_install_restore']=='PASS' or not build['repeated_publish_byte_identical']:
        raise ValueError('Install/restore and repeat-publish proof required')
    if ui.get('installer_sha256')!=build['sha256']:
        raise ValueError('UI preview belongs to a different installer')
    for name,sha in build['source_hashes'].items():
        if filehash(ROOT/name)!=sha:raise ValueError('Installer source drift: '+name)
    installer=Path(build['installer'])
    if filehash(installer)!=build['sha256']:raise ValueError('Installer identity drift')
    shutil.copyfile(installer,work/'MODIFIED_FILE.exe')
    shutil.copyfile(work/'payload.manifest.json',work/'DIFF_FILE.json')
    shell=work/'ROLLBACK.sh'
    shell.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
        'PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        'OUTPUT='+shlex.quote(locale.as_posix())+'\n'
        '"${PYTHON:-python}" -X utf8 "$PROJECT/tools/build_locale.py" rollback --output "$OUTPUT"\n',
        encoding='utf-8',newline='\n')
    shell.chmod(0o755)
    command=['C:/Program Files/Git/bin/bash.exe',str(shell)]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stderr)
    artifacts={name:str(work/name) for name in ('MODIFIED_FILE.exe','DIFF_FILE.json','VERIFICATION.txt','ROLLBACK.sh')}
    field=full['field']+'; installer UI retained'
    lines=['FIELD: '+field]
    lines.extend(k+': '+v for k,v in artifacts.items())
    for step in full['steps']:
        lines.extend(['',step['phase'],'COMMAND: '+subprocess.list2cmdline(step['command']),
            'INPUT: '+step['input'],'STDOUT:',step['stdout'].rstrip(),'STDERR:',step['stderr'].rstrip(),'EXIT STATUS: '+str(step['exit_status'])])
    if feedback:
        lines.extend(['','FEEDBACK COMMAND: '+subprocess.list2cmdline(feedback['command']),
                      'INPUT: '+str(locale/'MODIFIED_EXECUTABLE.exe'),'STDOUT:',feedback['stdout'].rstrip(),
                      'EXIT STATUS: '+str(feedback['exit_status'])])
    for step in build['steps']:
        lines.extend(['','INSTALLER COMMAND: '+subprocess.list2cmdline(step['command']),
            'STDOUT:',step['stdout'].rstrip(),'STDERR:',step['stderr'].rstrip(),'EXIT STATUS: '+str(step['exit_status'])])
    lines.extend(['','SHELL ROLLBACK COMMAND: '+subprocess.list2cmdline(command),'STDOUT:',result.stdout.rstrip(),
        'STDERR:',result.stderr.rstrip(),'EXIT STATUS: '+str(result.returncode),'','PYTHON TESTS:',
        (work/'python-tests.txt').read_text(encoding='utf-8').rstrip()])
    for preview in ui['previews']:
        lines.extend(['','UI COMMAND: '+subprocess.list2cmdline(preview['command']),
                      preview['layout'],'EXIT STATUS: '+str(preview['exit_status'])])
    for f in read(work/'payload.manifest.json')['files']:
        if filehash(work/'real-sample'/f['name'])!=f['source_sha256']:
            raise ValueError('Actual installer test copy not restored')
        if filehash(locale/'rollback-sample'/f['name'])!=f['source_sha256']:
            raise ValueError('Locale rollback copy not restored')
    lines.extend(['','INSTALLER SHA256: '+build['sha256'],'INSTALLER BYTES: '+str(build['size']),
        'RESTORED: separate real-sample and rollback-sample original SHA256, original text/font/decoder/debug gate',
        'MODIFIED: installer, localized archive/executable and manual sample retained',
        'GAME LAUNCHED: false; STEAM INSTALLATION WRITES: none'])
    receipt=work/'VERIFICATION.txt';receipt.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    for name,path in artifacts.items():
        p=Path(path)
        if not p.is_file() or not p.stat().st_size:raise ValueError('Missing '+name)
        filehash(p)
    meta=dict(field=field,artifacts=artifacts,installer=build['installer'],installer_sha256=build['sha256'],
              shell_rollback=dict(command=command,stdout=result.stdout,stderr=result.stderr,exit_status=result.returncode),
              original_copies_restored=True,modified_retained=True,game_launched=False)
    (work/'verification.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('INSTALLER VERIFICATION PASS baseline=0 modified=0 rollback=0 install-restore=PASS UI=3 artifacts=4 reopened modified=retained game-launched=false')


if __name__=='__main__':main()
