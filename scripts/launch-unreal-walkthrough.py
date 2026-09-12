"""Launch a generated native walkthrough; --smoke verifies a fresh study offscreen."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'unreal'))
import multi_room_state as mrs
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--rhi',choices=('d3d12','d3d11'),default='d3d12');p.add_argument('--smoke',action='store_true');p.add_argument('--logic-only',action='store_true');p.add_argument('--home-smoke',action='store_true');p.add_argument('--entry',choices=('resume','home','guest'),default='resume');a=p.parse_args()
if a.home_smoke:a.smoke=True
project=a.project.resolve();report=project/'walkthrough-verification.json'
if not json.loads(report.read_text(encoding='utf-8')).get('configured'):p.error('Enable walkthrough first')
if a.home_smoke and not json.loads((project/'walkthrough.json').read_text(encoding='utf-8')).get('stairs'):p.error('--home-smoke requires a home/whole stair profile')
state=project/('Saved/walkthrough-smoke-state.json' if a.smoke else 'Saved/walkthrough-state.json')
if a.smoke:
 if not project.is_relative_to(ROOT/'build'):p.error('Smoke tests are restricted to generated build projects')
 for name in ('walkthrough-smoke-state.json','walkthrough-smoke.txt','walkthrough-smoke.png'):
  (project/'Saved'/name).unlink(missing_ok=True)
cmd=[str(a.engine.resolve()/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),(project/'RyukaInterior.uproject').as_posix(),'/Game/Generated/House','-game','-'+a.rhi,('-sm6' if a.rhi=='d3d12' else '-sm5'),'-windowed',('-ResX=1920' if a.home_smoke else '-ResX=1600'),('-ResY=1080' if a.home_smoke else '-ResY=900'),'-NoSourceControl','-NoSound','-nosplash','-ShaderWorkingDir='+str(a.cache.resolve()/'shaders'),'-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+a.cache.resolve().as_posix()]
if a.logic_only and not a.smoke:p.error('--logic-only requires --smoke')
if a.smoke:cmd+=[('-NullRHI' if a.logic_only else '-RenderOffscreen'),'-unattended','-RyukaSmoke']
if a.home_smoke:cmd+=['-RyukaHomeSmoke']
if a.entry!='resume':
 config=json.loads((project/'walkthrough.json').read_text(encoding='utf-8'))
 rid={'home':'room-1f-19','guest':'room-1f-02'}[a.entry]
 if not config.get('launcherEntrySelection') or rid not in set(config['rooms']):p.error('Update the model to enable this entry')
 cmd+=['-RyukaEntryRoom='+rid]
print('WASD / mouse: walk and look. 1-3: finishes. 4-5: sun. F5: save. F9: restore. Tab: cursor.',flush=True)
with (project/('walkthrough-smoke.log' if a.smoke else 'walkthrough-run.log')).open('w',encoding='utf-8') as log:
 r=subprocess.run(cmd,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=180 if a.smoke else None)
if r.returncode:raise RuntimeError('Unreal runtime failed; inspect walkthrough log')
if a.smoke:
 assert (project/'Saved/walkthrough-smoke.txt').read_text(encoding='utf-8-sig')=='PASS'
 if not a.logic_only: assert (project/'Saved/walkthrough-smoke.png').is_file()
 # W07-G1: the round-tripped state is now always 2.0.0/multi-room-shaped
 # (AC5: 洋室's roomState must survive an F5/F9 cycle even though only LDK
 # is walked) -- validated against its OWN declared scope, the same way
 # refresh_inputs.py confirms a saved state is internally consistent.
 study=json.loads((project/'SourcePackage/study.json').read_text(encoding='utf-8'))
 scopes_document=json.loads((project/'SourcePackage/inputs/data/visual/study-scopes.json').read_text(encoding='utf-8'))
 legacy_study=json.loads((project/'SourcePackage/inputs/data/visual/guest-ldk-study.json').read_text(encoding='utf-8'))
 saved=mrs.validate_state_own_scope(json.loads(state.read_text(encoding='utf-8')),scopes_document,legacy_study,study['settings']['variants'])
 result=json.loads(report.read_text(encoding='utf-8'));result.update(runtimeVerified=True,renderVerified=not a.logic_only,renderRHI=a.rhi if not a.logic_only else None,checks=(['safe spawn','continuous stair ascent and descent','stair and upper-floor save/restore','floor attribution'] if a.home_smoke else ['safe spawn','blocking capsule sweep','finish and sun switch','state save and restore']),savedState=saved)
 report.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
