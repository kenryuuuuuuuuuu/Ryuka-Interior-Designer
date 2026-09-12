"""Run inside an isolated generated UE editor (Python commandlet).

Does not save the level or replace user state. Writes evidence and capture states.
"""
import copy,json,traceback
from pathlib import Path
import unreal
import study_controls as ctl

project=Path(unreal.Paths.project_dir()).resolve()
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Generated/House')
checks={}
initial=ctl.initial_state()
state_file=project/'study-state.json'
original=state_file.read_bytes() if state_file.exists() else None
out=project/'Saved/W07-home-verification';out.mkdir(parents=True,exist_ok=True)
try:
 ctl.apply_state(copy.deepcopy(initial))
 base=ctl.scene_state(ctl.current_state())
 checks['allRoomStates']=len(base['roomStates']) in (25,33)
 surfaces=ctl.surface_bindings()['surfaces']
 actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
 checks['allBoundSurfaceActors']=all(m['actor'] in actors for s in surfaces.values() for m in s.get('meshes',[]))
 # The upper floor must keep its own finish after changing the lower floor.
 changed=copy.deepcopy(base)
 changed['roomStates']['room-1f-11']['variant']='warm'
 changed['roomStates']['room-2f-04']['variant']='reference'
 ctl.apply_state(changed)
 roundtrip=ctl.scene_state(ctl.current_state())
 checks['independentFloorFinishes']=roundtrip['roomStates']==changed['roomStates']
 # One light on each level is explicitly overridden; all others must survive.
 fixtures={f['id']:f for f in ctl.lighting_bindings()['fixtures']}
 selected=[]
 for rid in ('room-1f-11','room-2f-04'):
  fid=next(k for k,v in fixtures.items() if v['roomId']==rid)
  selected.append(fid)
  changed['roomStates'][rid]['fixtures'][fid]={'on':True,'dimming':.6,'temperatureK':3200}
 ctl.apply_state(changed)
 checks['independentFloorLights']=ctl.scene_state(ctl.current_state())['roomStates']==changed['roomStates']
 # Empty-room base finish is retained even when every available face differs.
 empty='room-1f-19';empty_state=copy.deepcopy(changed)
 empty_state['roomStates'][empty]['variant']='natural'
 empty_state['roomStates'][empty]['surfaceOverrides']={sid:{'variant':'warm'} for sid,s in surfaces.items() if s['roomId']==empty and s['status']=='bound'}
 ctl.apply_state(empty_state)
 checks['emptyRoomBaseVariant']=ctl.scene_state(ctl.current_state())['roomStates'][empty]['variant']=='natural'
 empty_state['roomStates'][empty]['surfaceOverrides']={}
 ctl.apply_state(empty_state)
 checks['emptyRoomReset']=ctl.scene_state(ctl.current_state())['roomStates'][empty]['variant']=='natural'
 # Every folding leaf supports its full authored transform; reopening after
 # closing must not accumulate offsets on the second panel.
 for did in ('door-023','door-026','door-027'):
  if did not in ctl.door_bindings()['doors']:continue
  poses=[]
  for opened in (True,False,True):
   test=copy.deepcopy(changed);test['doorStates'][did]={'open':opened};ctl.apply_state(test)
   poses.append([(tuple(actors[l['actor']].get_actor_location().to_tuple()),tuple(getattr(actors[l['actor']].get_actor_rotation(),k) for k in ('pitch','yaw','roll'))) for l in ctl.door_bindings()['doors'][did]['leaves']])
  (out/(did+'-poses.json')).write_text(json.dumps(poses,indent=2),encoding='utf8')
  # Imported float rotation differs by ~8e-6 degrees from native doubles.
  drift=max(abs(a-b) for left,right in zip(poses[0],poses[2]) for xs,ys in zip(left,right) for a,b in zip(xs,ys))
  checks[did+'FoldReopenStable']=drift<1e-4 and poses[0]!=poses[1]
 ctl.apply_state(changed)
 saved=ctl.scene_state(ctl.current_state())
 (out/'roundtrip-state.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf8')
 ctl.apply_state(copy.deepcopy(base));ctl.apply_state(json.loads((out/'roundtrip-state.json').read_text(encoding='utf8')))
 checks['diskRoundTrip']=ctl.scene_state(ctl.current_state())['roomStates']==saved['roomStates']
 for rid in ('room-1f-11','room-2f-04','room-1f-15','room-2f-03'):
  ctl.select_room(rid)
  view=ctl.scene_state(ctl.current_state())
  (out/(rid+'-day.json')).write_text(json.dumps(view,ensure_ascii=False,indent=2),encoding='utf8')
 checks['sourceSaveUnchanged']=(state_file.read_bytes() if state_file.exists() else None)==original
except Exception:
 checks['exception']=traceback.format_exc()
finally:
 ctl.apply_state(copy.deepcopy(initial))
 (out/'result.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
if not all(v is True for v in checks.values()):raise RuntimeError(str(checks))
unreal.log('W07 home verification PASS: '+str(checks))
