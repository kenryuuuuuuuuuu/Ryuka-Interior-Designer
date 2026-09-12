"""Compile and install the native walkthrough into a generated local UE study."""
import argparse,json,subprocess,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
sys.path.insert(0,str(ROOT/'blender'))
from stair_geometry import layout as stair_layout
import circulation
import multi_room_state as mrs
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
a=p.parse_args();project=a.project.resolve();engine=a.engine.resolve()
report=json.loads((project/'import-verification.json').read_text(encoding='utf-8'))
if not report.get('unrealImportVerified'):raise ValueError('Verified study required')
if not project.is_relative_to(ROOT/'build'):raise ValueError('Only generated worktree build projects supported')
shutil.copytree(ROOT/'unreal/walkthrough/Source',project/'Source',dirs_exist_ok=True)
u=project/'RyukaInterior.uproject';doc=json.loads(u.read_text(encoding='utf-8-sig'));doc['Modules']=[dict(Name='RyukaInterior',Type='Runtime',LoadingPhase='Default')];u.write_text(json.dumps(doc,indent=2),encoding='utf-8')
study=json.loads((project/'SourcePackage/study.json').read_text(encoding='utf-8'))
house=json.loads((project/'SourcePackage/inputs/data/house.json').read_text(encoding='utf-8'))
interior_doors=json.loads((project/'SourcePackage/inputs/data/interior-doors.json').read_text(encoding='utf-8'))['items']
door_catalog={t['type']:t for t in json.loads((project/'SourcePackage/inputs/data/door-catalog.json').read_text(encoding='utf-8'))['types']}
scopes_document=mrs.validate_scopes(json.loads((project/'SourcePackage/inputs/data/visual/study-scopes.json').read_text(encoding='utf-8')))
profiles_document=circulation.validate_profiles(json.loads((project/'SourcePackage/inputs/data/visual/walkthrough-profiles.json').read_text(encoding='utf-8')))
# W07-G2: the walkthrough profile is looked up from the project's OWN edit
# scope (never the other way around) -- guest-pilot gets the multi-room
# guest-circulation profile, guest-ldk (and any pre-W07 project) keeps the
# traditional single-room walk (spec section 1: "旧guest-ldkでは従来の単室
# 内覧を保持します"). Both are the SAME generalised C++ code path; a
# single-room/zero-door profile degenerates to the old behaviour exactly,
# not a separate implementation.
profile=circulation.resolve_profile_for_scope(profiles_document,study['scopeId'])
edit_scope=mrs.resolve_scope(scopes_document,study['scopeId'])
rooms_by_id={r['id']:r for r in house['rooms']}
connections=circulation.resolve_connections(rooms_by_id,interior_doors,door_catalog,profile['roomIds'])
door_bindings=json.loads((project/'door-bindings.json').read_text(encoding='utf-8'))['doors']
# W07-G2 spec section 1: several guest-area door labels in interior-doors.json
# are stale (authored before the hall was split out of the old genkan room)
# and name the WRONG room pair -- resolve_connections() above already
# ignores that label text entirely for CONNECTIVITY (geometry only), but the
# HUD's on-screen door prompt must not show that same wrong text to the
# operator either. Building the displayed label from the two rooms
# resolve_connections() actually found (their own current house.json labels)
# guarantees it always matches the real connection, never the door's own
# possibly-stale name.
rooms_config={}
for room_id in profile['roomIds']:
    room=rooms_by_id[room_id]
    rooms_config[room_id]=dict(level=room['level'],floorCm=house['levels'][f"fl{room['level']}"]*100,
        polygonCm=[[x*100,z*100] for x,z in room['polygon']],label=room.get('label') or room_id)
connections_config=[]
for c in connections:
    lo,hi=c['center']-c['width']/2,c['center']+c['width']/2
    leaves=door_bindings.get(c['id'],{}).get('leaves',[])
    connection_label='⟷'.join(rooms_by_id[room_id].get('label') or room_id for room_id in c['roomIds'])
    connections_config.append(dict(id=c['id'],roomIds=c['roomIds'],operation=c['operation'],
        openable=c['operation'] in circulation.OPENABLE_OPERATIONS,orientation=c['orientation'],edgeCm=[[x*100,z*100] for x,z in c.get('edge',[])],
        atCm=c['wallAt']*100,loCm=lo*100,hiCm=hi*100,leaves=leaves,label=connection_label))
config=dict(schemaVersion='2.0.0',profileId=profile['profileId'],entryRoomId=profile['entryRoomId'],
    editRoomIds=edit_scope['roomIds'],cachePath=a.cache.resolve().as_posix(),
    rooms=rooms_config,connections=connections_config,
    stairs=[dict(id=t['id'],lowerRoomId='room-1f-10',upperRoomId='room-2f-02',
        steps=[dict(polygonCm=[[x*100,z*100] for x,z in poly],topCm=step['top']*100,lower=step['top']<(house['levels']['fl1']+house['levels']['fl2'])/2) for step in stair_layout(t,house['levels'])['steps'] for poly in step['polygons']])
        for t in house.get('stairs',[]) if 'room-1f-10' in profile['roomIds'] and 'room-2f-02' in profile['roomIds']])
if config['stairs']:
    # Route samples are derived from the canonical centreline for the native
    # real CharacterMovement stair test, not used for production movement.
    import math
    t=house['stairs'][0]; route=[]
    first=t['segments'][0];last=t['segments'][-1]
    dx,dz=first['x1']-first['x0'],first['z1']-first['z0'];length=math.hypot(dx,dz)
    route.append([first['x0']-dx/length*.5,first['z0']-dz/length*.5])
    for seg in t['segments']:
        if seg['type']=='straight':
            route.extend([[seg['x0']+(seg['x1']-seg['x0'])*i/8,seg['z0']+(seg['z1']-seg['z0'])*i/8] for i in range(9)])
        else:
            for i in range(1,17):
                angle=math.radians(seg['startAngleDeg']+(seg['endAngleDeg']-seg['startAngleDeg'])*i/16)
                route.append([seg['pivotX']+seg['radius']*math.cos(angle),seg['pivotZ']+seg['radius']*math.sin(angle)])
    dx,dz=last['x1']-last['x0'],last['z1']-last['z0'];length=math.hypot(dx,dz)
    route.append([last['x1']+dx/length*.5,last['z1']+dz/length*.5])
    config['stairRouteCm']=[[x*100,z*100] for x,z in route]
(project/'walkthrough.json').write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
# Native toolchain response files require a short ASCII path on this Windows setup.
native=Path(tempfile.mkdtemp(prefix='ryuka-native-'))
shutil.copytree(project/'Source',native/'Source')
shutil.copy2(u,native/u.name)
command=[str(engine/'Engine/Build/BatchFiles/Build.bat'),'RyukaInteriorEditor','Win64','Development','-Project='+str(native/u.name),'-WaitMutex','-NoHotReloadFromIDE','-NoUBA','-MaxParallelActions=2']
with (project/'walkthrough-compile.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('Compile failed; see walkthrough-compile.log')
shutil.copytree(native/'Binaries',project/'Binaries',dirs_exist_ok=True)
shutil.copy2(ROOT/'unreal/study_controls.py',project/'Content/Python/study_controls.py')
shutil.copy2(ROOT/'unreal/circulation.py',project/'Content/Python/circulation.py')
shutil.copy2(ROOT/'unreal/configure_walkthrough.py',project/'configure_walkthrough.py')
command=[str(engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),u.as_posix(),'-run=pythonscript','-script='+(project/'configure_walkthrough.py').as_posix(),'-unattended','-NullRHI','-NoSound','-NoSourceControl','-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+a.cache.resolve().as_posix()]
with (project/'walkthrough-configure.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=project)
if r.returncode:raise RuntimeError('Configuration failed; see walkthrough-configure.log')
print('Walkthrough ready:',u)
