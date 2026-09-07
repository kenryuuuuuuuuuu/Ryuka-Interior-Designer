"""Compile and install the native walkthrough into a generated local UE study."""
import argparse,json,subprocess,shutil,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
a=p.parse_args();project=a.project.resolve();engine=a.engine.resolve()
report=json.loads((project/'import-verification.json').read_text(encoding='utf-8'))
if not report.get('unrealImportVerified'):raise ValueError('Verified study required')
if not project.is_relative_to(ROOT/'build'):raise ValueError('Only generated worktree build projects supported')
shutil.copytree(ROOT/'unreal/walkthrough/Source',project/'Source',dirs_exist_ok=True)
u=project/'RyukaInterior.uproject';doc=json.loads(u.read_text(encoding='utf-8-sig'));doc['Modules']=[dict(Name='RyukaInterior',Type='Runtime',LoadingPhase='Default')];u.write_text(json.dumps(doc,indent=2),encoding='utf-8')
study=json.loads((project/'SourcePackage/study.json').read_text(encoding='utf-8'));house=json.loads((project/'SourcePackage/inputs/data/house.json').read_text(encoding='utf-8'))
room=next(r for r in house['rooms'] if r['id']==study['roomId'])
config=dict(schemaVersion='1.0.0',roomId=room['id'],cachePath=a.cache.resolve().as_posix(),floorCm=house['levels'][f"fl{room['level']}"]*100,polygonCm=[[x*100,z*100] for x,z in room['polygon']])
(project/'walkthrough.json').write_text(json.dumps(config),encoding='utf-8')
# Native toolchain response files require a short ASCII path on this Windows setup.
native=Path(tempfile.mkdtemp(prefix='ryuka-native-'))
shutil.copytree(project/'Source',native/'Source')
shutil.copy2(u,native/u.name)
command=[str(engine/'Engine/Build/BatchFiles/Build.bat'),'RyukaInteriorEditor','Win64','Development','-Project='+str(native/u.name),'-WaitMutex','-NoHotReloadFromIDE','-NoUBA','-MaxParallelActions=2']
with (project/'walkthrough-compile.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('Compile failed; see walkthrough-compile.log')
shutil.copytree(native/'Binaries',project/'Binaries',dirs_exist_ok=True)
shutil.copy2(ROOT/'unreal/study_controls.py',project/'Content/Python/study_controls.py')
shutil.copy2(ROOT/'unreal/configure_walkthrough.py',project/'configure_walkthrough.py')
command=[str(engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),u.as_posix(),'-run=pythonscript','-script='+(project/'configure_walkthrough.py').as_posix(),'-unattended','-NullRHI','-NoSound','-NoSourceControl','-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+a.cache.resolve().as_posix()]
with (project/'walkthrough-configure.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=project)
if r.returncode:raise RuntimeError('Configuration failed; see walkthrough-configure.log')
print('Walkthrough ready:',u)
