"""Render a saved Unreal editor study offscreen using the installed GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine',type=Path,required=True)
parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--cache',type=Path,required=True)
parser.add_argument('--name',default='interior-unreal',help='New PNG basename for this capture')
args=parser.parse_args()
project=args.project.resolve(); cache=args.cache.resolve()
if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
    parser.error('Capture name may contain letters, numbers, hyphens and underscores only.')
image=project/'Saved'/(args.name+'.png')
if not (project/'import-verification.json').is_file(): parser.error('A successfully verified generated project is required.')
if image.exists(): parser.error('Capture exists; use a new --name or another project.')
shutil.copy2(ROOT/'unreal/capture_study.py',project/'capture_study.py')
(project/'capture-job.json').write_text(json.dumps(dict(name=args.name)),encoding='utf-8')
command=[str(args.engine.resolve()/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),
         str(project/'RyukaInterior.uproject'),
         "-ExecCmds=py import runpy; runpy.run_path(__import__('unreal').Paths.project_dir()+'capture_study.py')",
         '-unattended','-RenderOffscreen','-NoSound','-nosplash','-NoSourceControl',
         '-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+str(cache),
         '-ShaderWorkingDir='+str(cache/'shaders')]
with (project/'capture.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=600)
if result.returncode or not image.is_file(): raise RuntimeError(f'Capture failed; inspect {project}/Saved/Logs.')
log=(project/'Saved/Logs/RyukaInterior.log').read_text(encoding='utf-8',errors='replace')
report=dict(imageSHA256=hashlib.sha256(image.read_bytes()).hexdigest(),
    hardwareRayTracingEnabled='Ray tracing is enabled' in log,
    width=1600,height=900,siteDaylightCalibrated=False)
image.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(image)
