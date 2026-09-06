"""Local, explicitly sourced box approximations for neighbouring shade geometry."""
import math
import re


def validate_context(value):
    if not isinstance(value,dict) or value.get('schemaVersion')!='1.0.0':
        raise ValueError('Invalid site context schema')
    boxes=value.get('boxes')
    if not isinstance(boxes,list) or len(boxes)>200: raise ValueError('Expected up to 200 context boxes')
    ids=set()
    for box in boxes:
        if not isinstance(box,dict): raise ValueError('Invalid context box')
        name=box.get('id')
        if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',name) or name in ids:
            raise ValueError('Context IDs must be unique safe names')
        ids.add(name)
        if box.get('status') not in ('estimated','verified') or not isinstance(box.get('note'),str) or not box['note'].strip():
            raise ValueError('Each context box requires status and provenance note')
        for key in ('centerMetres','sizeMetres'):
            v=box.get(key)
            if not isinstance(v,list) or len(v)!=3 or any(isinstance(n,bool) or not isinstance(n,(float,int)) or not math.isfinite(n) for n in v):
                raise ValueError('Invalid '+key)
        if any(abs(n)>1000 for n in box['centerMetres']): raise ValueError('Context centre outside local study extent')
        if any(not .01<=n<=200 for n in box['sizeMetres']): raise ValueError('Context size must be in [0.01, 200] m')
        yaw=box.get('rotationDeg',0)
        if isinstance(yaw,bool) or not isinstance(yaw,(float,int)) or not math.isfinite(yaw) or not 0<=yaw<360:
            raise ValueError('Invalid context rotation')
    return value


def transform(box):
    # Input [source x, source z, GL height], centre of the solid, not its base.
    return dict(locationCm=[v*100 for v in box['centerMetres']],
                scale=box['sizeMetres'],yaw=box.get('rotationDeg',0))


def expected_bounds(box):
    x,y,z=transform(box)['locationCm']
    w,d,h=[v*100 for v in box['sizeMetres']]
    a=math.radians(box.get('rotationDeg',0))
    ex=(abs(math.cos(a))*w+abs(math.sin(a))*d)/2
    ey=(abs(math.sin(a))*w+abs(math.cos(a))*d)/2
    return [x-ex,y-ey,z-h/2,x+ex,y+ey,z+h/2]


def create_context(value, material):
    import unreal
    validate_context(value)
    mesh=unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    if mesh is None: raise RuntimeError('Engine unit cube unavailable')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    verified=[]
    for box in value['boxes']:
        t=transform(box)
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*t['locationCm']),
                                            unreal.Rotator(pitch=0,yaw=t['yaw'],roll=0))
        actor.set_actor_label('Context_'+box['id']); actor.set_folder_path('Local/SiteContext')
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_material(0,material)
        actor.set_actor_scale3d(unreal.Vector(*t['scale']))
        center,extent=actor.get_actor_bounds(False)
        actual=list((center-extent).to_tuple())+list((center+extent).to_tuple())
        error=max(abs(a-b) for a,b in zip(actual,expected_bounds(box)))
        if error>.1: raise RuntimeError('Context bounds mismatch: '+box['id'])
        verified.append(dict(id=box['id'],status=box['status'],maxBoundsErrorCm=error))
    return verified


def verify_scene(value):
    import unreal
    validate_context(value)
    actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_actor_label().startswith('Context_')}
    if set(actors)!={'Context_'+b['id'] for b in value['boxes']}: raise RuntimeError('Context actors changed; regenerate from local settings')
    for box in value['boxes']:
        actor=actors['Context_'+box['id']]
        center,extent=actor.get_actor_bounds(False)
        actual=list((center-extent).to_tuple())+list((center+extent).to_tuple())
        if max(abs(a-b) for a,b in zip(actual,expected_bounds(box)))>.1:
            raise RuntimeError('Context moved; update local settings and regenerate: '+box['id'])
        if actor.get_editor_property('hidden') or actor.is_hidden_ed() or not actor.static_mesh_component.get_editor_property('cast_shadow'):
            raise RuntimeError('Context visibility or shadows changed: '+box['id'])
