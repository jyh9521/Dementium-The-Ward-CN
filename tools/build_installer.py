"""Build and verify a self-contained Windows installer with source-relative deltas.

Only workspace outputs are writable; original installation files are read-only.
No game process is started, and no original full archive/executable is embedded.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from installer_branding import build as build_branding
from source_delta import build as build_delta, apply as apply_delta, filehash
from workspace_io import validate_output_tree

ROOT = Path(__file__).resolve().parents[1]


def workspace(path, folder):
    path = Path(os.path.abspath(path))
    base = ROOT / folder
    if not path.is_relative_to(base):
        raise ValueError('Output must stay under repository ' + folder)
    existing = base
    while not existing.exists():
        existing = existing.parent
    validate_output_tree(existing)
    return path.resolve()


def payload(game, build, locale):
    work = workspace(ROOT / 'build/installer', 'build')
    work.mkdir(parents=True, exist_ok=True)
    validate_output_tree(work)
    identity = json.loads((ROOT/'assets/original-identity.json').read_text(encoding='utf-8'))
    report = json.loads((build/'build-report.json').read_text(encoding='utf-8'))
    receipt = json.loads((build/'verification.json').read_text(encoding='utf-8'))
    if not all(s['exit_status'] == 0 for s in receipt['steps']) or not report['reproducible']:
        raise ValueError('Verified reproducible locale build required')
    settings = json.loads((ROOT/'locales'/locale/'installer.json').read_text(encoding='utf-8'))
    known = {r['path']: r for r in identity['files']}
    files = []
    diagnostics = []
    for name, target, resource, expected in [
        (settings['archive_file'], build/'MODIFIED_FILE.zar', 'rom.delta.gz', report['modified_sha256']),
        (settings['executable_file'], build/'MODIFIED_EXECUTABLE.exe', 'exe.delta.gz', report['executable_sha256'])]:
        source = game/name
        if source.stat().st_size != known[name]['size'] or filehash(source) != known[name]['sha256']:
            raise ValueError('Unsupported original identity: ' + name)
        if filehash(target) != expected:
            raise ValueError('Modified locale artifact identity mismatch: ' + name)
        result = build_delta(source, target, work/resource)
        if (result['source_sha256'], result['source_size']) != (known[name]['sha256'], known[name]['size']) or result['target_sha256'] != expected:
            raise ValueError('Input identity changed while constructing payload: ' + name)
        # Independently regenerate the compressed stream; all commands/bytes must match.
        second = work/('repeat-' + resource)
        if build_delta(source, target, second) != result or filehash(second) != filehash(work/resource):
            raise ValueError('Nondeterministic installer delta')
        verified = work/('verified-' + name)
        apply_delta(source, work/resource, verified, result)
        if filehash(verified) != filehash(target):
            raise ValueError('Reconstructed locale output mismatch')
        files.append(dict(name=name, resource=resource, **{k:result[k] for k in
                          ('source_size','source_sha256','target_size','target_sha256')}))
        diagnostics.append(dict(name=name, **result))
    manifest = dict(schema=1, format='source-copy-add-v1', settings=settings, files=files)
    (work/'payload.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (work/'payload-report.json').write_text(json.dumps(diagnostics,indent=2)+'\n',encoding='utf-8')
    if json.loads((work/'payload.manifest.json').read_text(encoding='utf-8')) != manifest:
        raise ValueError('Reopened installer manifest mismatch')
    return manifest, diagnostics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--build', type=Path, default=ROOT/'build/release-candidate')
    p.add_argument('--locale', default='zh-CN')
    p.add_argument('--dotnet', type=Path, default=os.environ.get('DOTNET_EXE'))
    p.add_argument('--output', type=Path, default=ROOT/'dist/Dementium-The-Ward-zh-CN-Setup.exe')
    a = p.parse_args()
    output = workspace(a.output, 'dist')
    build = workspace(a.build, 'build')
    game = a.game.resolve()
    compiler = str(a.dotnet) if a.dotnet else shutil.which('dotnet')
    if not compiler:
        raise ValueError('Specify a .NET 10 SDK with --dotnet or DOTNET_EXE')
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    branding = build_branding(ROOT/'installer')
    manifest, diagnostics = payload(game, build, a.locale)
    work = ROOT/'build/installer'
    steps=[]
    def run(command):
        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        steps.append(dict(command=command,stdout=result.stdout,stderr=result.stderr,exit_status=result.returncode))
        (work/'build-commands.json').write_text(json.dumps(steps,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(result.stdout,end='',flush=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
    run([compiler,'--version'])
    run([compiler,'publish',str(ROOT/'installer/Installer.csproj'),'-c','Release',
         '-p:RestoreLockedMode=true','-o',str(work/'publish')])
    run([compiler,'publish',str(ROOT/'installer/Installer.csproj'),'-c','Release',
         '-p:RestoreLockedMode=true','-o',str(work/'publish-repeat')])
    if filehash(work/'publish/Dementium-The-Ward-zh-CN-Setup.exe') != filehash(work/'publish-repeat/Dementium-The-Ward-zh-CN-Setup.exe'):
        raise ValueError('Repeated installer publish differs')
    run([compiler,'build',str(ROOT/'installer/Tests.csproj'),'-c','Release'])
    tests=work/'tests/net10.0-windows10.0.17763.0/InstallerTests.dll'
    # C# engine verifies embedded resources against a completely separate original copy.
    fixture=work/'real-sample'
    fixture.mkdir(exist_ok=True);validate_output_tree(fixture)
    allowed={f['name'] for f in manifest['files']}
    if any(q.name not in allowed for q in fixture.iterdir()):
        raise ValueError('Unexpected real installer fixture file')
    for f in manifest['files']:
        shutil.copyfile(game/f['name'],fixture/f['name'])
    run([compiler,str(tests),'--real',str(fixture)])
    for f in manifest['files']:
        if filehash(fixture/f['name'])!=f['source_sha256'] or filehash(game/f['name'])!=f['source_sha256']:
            raise ValueError('Installer rollback/input identity mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(work/'publish/Dementium-The-Ward-zh-CN-Setup.exe',output)
    report=dict(installer=str(output),size=output.stat().st_size,sha256=filehash(output),
                version=manifest['settings']['version'],source_build='21501403',
                payloads=diagnostics,branding=branding,steps=steps,
                compiler=str(Path(compiler).resolve()),compiler_sha256=filehash(compiler),
                source_hashes={p.relative_to(ROOT).as_posix():filehash(p) for p in
                    sorted((ROOT/'installer').rglob('*')) if p.is_file()},
                self_contained=True,requires_python=False,requires_separate_dotnet_runtime=False,
                repeated_publish_byte_identical=True,
                UI='MaterialDesignThemes 5.3.2 / Material Design 3, same upstream layout',
                full_original_game_files_embedded=False,isolated_install_restore='PASS',
                original_inputs_unchanged=True,game_launched=False)
    (work/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if filehash(output)!=report['sha256']:
        raise ValueError('Reopened installer identity mismatch')
    print('INSTALLER PASS bytes='+str(report['size'])+' sha256='+report['sha256']+
          ' self-contained=true isolated-install-restore=PASS input=unchanged game-launched=false')


if __name__=='__main__':
    main()
