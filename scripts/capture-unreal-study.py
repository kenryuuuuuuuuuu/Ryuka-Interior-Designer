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
parser.add_argument('--variant',choices=('natural','warm'),help='Temporary finish override; does not save the level')
parser.add_argument('--elevation',type=float,help='Temporary manual sun elevation in degrees')
args=parser.parse_args()
project=args.project.resolve(); cache=args.cache.resolve()
if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
    parser.error('Capture name may contain letters, numbers, hyphens and underscores only.')
image=project/'Saved'/(args.name+'.png')
if args.elevation is not None and not 1<=args.elevation<=89: parser.error('Elevation must be in [1, 89].')
if (args.variant or args.elevation is not None) and not (project/'study-state.json').exists():
    parser.error('Rebuild this project with the comparison controls first.')
if not (project/'import-verification.json').is_file(): parser.error('A successfully verified generated project is required.')
if image.exists(): parser.error('Capture exists; use a new --name or another project.')
shutil.copy2(ROOT/'unreal/capture_study.py',project/'capture_study.py')
level_file=project/'Content/Generated/House.umap'
level_before=hashlib.sha256(level_file.read_bytes()).hexdigest()
(project/'capture-job.json').write_text(json.dumps(dict(name=args.name,variant=args.variant,elevation=args.elevation)),encoding='utf-8')
command=[str(args.engine.resolve()/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),
         str(project/'RyukaInterior.uproject'),
         "-ExecCmds=py import runpy; runpy.run_path(__import__('unreal').Paths.project_dir()+'capture_study.py')",
         '-unattended','-RenderOffscreen','-NoSound','-nosplash','-NoSourceControl',
         '-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+str(cache),
         '-ShaderWorkingDir='+str(cache/'shaders')]
with (project/'capture.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=600)
if result.returncode or not image.is_file(): raise RuntimeError(f'Capture failed; inspect {project}/Saved/Logs.')
if hashlib.sha256(level_file.read_bytes()).hexdigest()!=level_before:
    raise RuntimeError('Capture unexpectedly changed the saved level.')
log=(project/'Saved/Logs/RyukaInterior.log').read_text(encoding='utf-8',errors='replace')
if 'Failed to compile Material' in log or 'LogPython: Error:' in log:
    raise RuntimeError('Capture has shader/Python errors; inspect Saved/Logs before using the image.')
report=dict(imageSHA256=hashlib.sha256(image.read_bytes()).hexdigest(),
    hardwareRayTracingEnabled='Ray tracing is enabled' in log,
    width=1600,height=900,siteDaylightCalibrated=False,levelFileUnchanged=True)
conditions=project/'Saved'/(args.name+'-conditions.json')
if conditions.exists():
    report['comparisonState']=json.loads(conditions.read_text(encoding='utf-8'))
    report['conditionsSHA256']=hashlib.sha256(conditions.read_bytes()).hexdigest()
if (project/'finish-settings.json').exists():
    report['finishSettingsSHA256']=hashlib.sha256((project/'finish-settings.json').read_bytes()).hexdigest()
image.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(image)
