"""Create an isolated Unreal editor study from a verified Blender package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',type=Path,required=True,help='UE installation directory')
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='New project directory; never overwrite')
    parser.add_argument('--cache',type=Path,required=True,help='Writable DDC path, at most 119 characters')
    parser.add_argument('--sun-lux',type=float,default=50000,help='Provisional UE light intensity')
    parser.add_argument('--exposure-ev100',type=float,default=7.5,help='Fixed UE exposure (not Blender EV)')
    args=parser.parse_args()
    exe=args.engine.resolve()/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    output=args.output.resolve(); package=args.package.resolve(); cache=args.cache.resolve()
    if not exe.is_file(): parser.error('UnrealEditor-Cmd.exe not found.')
    if output.exists(): parser.error('Output exists. Choose a new project directory.')
    if len(str(cache))>119: parser.error('Unreal filesystem DDC requires a cache path of at most 119 characters.')
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['artifacts'].items():
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=info['sha256']:
            parser.error('Package artifact checksum mismatch: '+name)
    verified=json.loads((package/'verification.json').read_text(encoding='utf-8'))
    if not verified.get('meshBoundsBlenderMetres'): parser.error('Rebuild package with current Blender verifier.')
    shutil.copytree(ROOT/'unreal/template',output)
    shutil.copytree(package,output/'SourcePackage')
    shutil.copy2(ROOT/'unreal/import_study.py',output/'import_study.py')
    (output/'import-job.json').write_text(json.dumps(dict(sunLux=args.sun_lux,
        exposureEV100=args.exposure_ev100),indent=2)+'\n',encoding='utf-8')
    cache.mkdir(parents=True,exist_ok=True)
    # Commandlet Python unescapes backslashes (e.g. \\r); always pass forward-slash paths.
    command=[str(exe),(output/'RyukaInterior.uproject').as_posix(),'-run=pythonscript',
             '-script='+(output/'import_study.py').as_posix(),'-unattended','-NullRHI','-NoSound',
             '-nosplash','-NoSourceControl','-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+cache.as_posix()]
    with (output/'import.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=output,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    report=output/'import-verification.json'
    if result.returncode or not report.is_file():
        raise RuntimeError(f'Unreal import failed. Inspect {output / "import.log"}; source package is untouched.')
    print(report.read_text(encoding='utf-8'))
    print('Project: '+str(output/'RyukaInterior.uproject'))


if __name__=='__main__': main()
