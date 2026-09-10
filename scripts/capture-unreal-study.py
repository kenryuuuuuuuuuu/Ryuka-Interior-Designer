"""Render a saved Unreal editor study offscreen using the installed GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from solar_position import validate_cases
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine',type=Path,required=True)
parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--cache',type=Path,required=True)
parser.add_argument('--name',default='interior-unreal',help='New PNG basename for this capture')
parser.add_argument('--variant',choices=('natural','warm','reference'),help='Temporary finish override; does not save the level')
parser.add_argument('--elevation',type=float,help='Temporary manual sun elevation in degrees')
parser.add_argument('--sun-case',type=int,help='Zero-based index in the generated project sun-cases.json')
parser.add_argument('--state',type=Path,help='W08-G: a specific comparison state json to render (already selected/validated '
    'by the caller -- e.g. the newest of the editor save and the walkthrough F5 save). Used verbatim except the '
    'ACTIVE room\'s variant (from --variant); the level is never saved.')
args=parser.parse_args()
project=args.project.resolve(); cache=args.cache.resolve()
if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
    parser.error('Capture name may contain letters, numbers, hyphens and underscores only.')
image=project/'Saved'/(args.name+'.png')
if args.sun_case is not None:
    if args.elevation is not None: parser.error('Choose --sun-case or --elevation, not both.')
    cases=validate_cases(json.loads((project/'sun-cases.json').read_text(encoding='utf-8')))['cases']
    if not 0<=args.sun_case<len(cases) or not cases[args.sun_case]['usable']: parser.error('Unsupported solar case.')
if args.elevation is not None and not 1<=args.elevation<=89: parser.error('Elevation must be in [1, 89].')
if (args.variant or args.elevation is not None or args.sun_case is not None) and not (project/'study-state.json').exists():
    parser.error('Rebuild this project with the comparison controls first.')
if not (project/'import-verification.json').is_file(): parser.error('A successfully verified generated project is required.')
if image.exists(): parser.error('Capture exists; use a new --name or another project.')
state_payload=None
if args.state is not None:
    if not args.state.is_file(): parser.error('--state file not found: '+str(args.state))
    state_payload=json.loads(args.state.read_text(encoding='utf-8-sig'))
shutil.copy2(ROOT/'unreal/capture_study.py',project/'capture_study.py')
level_file=project/'Content/Generated/House.umap'
level_before=hashlib.sha256(level_file.read_bytes()).hexdigest()
(project/'capture-job.json').write_text(json.dumps(dict(name=args.name,variant=args.variant,elevation=args.elevation,
    sunCase=args.sun_case,state=state_payload)),encoding='utf-8')
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
import_report=json.loads((project/'import-verification.json').read_text(encoding='utf-8'))
report['siteContext']=import_report.get('siteContext')
report['floorShaderSHA256']=import_report.get('floorShaderSHA256')
conditions=project/'Saved'/(args.name+'-conditions.json')
if conditions.exists():
    report['comparisonState']=json.loads(conditions.read_text(encoding='utf-8'))
    report['conditionsSHA256']=hashlib.sha256(conditions.read_bytes()).hexdigest()
if (project/'finish-settings.json').exists():
    report['finishSettingsSHA256']=hashlib.sha256((project/'finish-settings.json').read_bytes()).hexdigest()
image.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(image)
