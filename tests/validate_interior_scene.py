"""Blender integration checks: closed solids, guest ceiling rays, glazing, GLB round-trip."""
import argparse
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector


def bounds(obj):
    pts=[obj.matrix_world @ Vector(v) for v in obj.bound_box]
    return [min(p[i] for p in pts) for i in range(3)]+[max(p[i] for p in pts) for i in range(3)]


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--study',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]); root=args.study.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(root/'interior.blend'))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for obj in meshes:
        bm=bmesh.new(); bm.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in bm.edges), f'Non-manifold solid: {obj.name}'
        assert bm.calc_volume(signed=True)>1e-10, f'Invalid volume/normals: {obj.name}'
        bm.free()
    scene=bpy.context.scene; deps=bpy.context.evaluated_depsgraph_get()
    hits=[]
    for x,z in [(2.2,3.1),(2.2,5.7),(3.5,5.2),(5.3,4.5),(6.5,5.7)]:
        hit,location,normal,index,obj,matrix=scene.ray_cast(deps,Vector((x,-z,2.8)),Vector((0,0,1)),distance=10)
        expected=3.4+(z+.5)*.15-.075-.15
        assert hit and obj.name.startswith('ceiling.room-1f-06.'), f'Ceiling gap at {x,z}: {obj.name if hit else None}'
        assert abs(location.z-expected)<1e-5, (location.z,expected)
        hits.append(dict(x=x,z=z,ceilingGL=location.z))
    hit,location,normal,index,obj,matrix=scene.ray_cast(deps,Vector((3.3,-6.1,2.407)),Vector((0,-1,0)),distance=.6)
    assert hit and obj.name=='opening.op-006.glass', f'Guest window blocked: {obj.name if hit else None}'
    detail_checks={}
    sink=next((o for o in meshes if o.name.endswith('.sink-bottom')),None)
    if sink is not None:
        bb=bounds(sink); x=(bb[0]+bb[3])/2; y=(bb[1]+bb[4])/2
        hit,location,normal,index,obj,matrix=scene.ray_cast(deps,Vector((x,y,bb[5]+.25)),Vector((0,0,-1)),distance=.5)
        assert hit and obj==sink, 'Sink basin is filled or covered by another solid'
        assert abs(location.z-bb[5])<.001
        detail_checks['sinkBasinOpen']=True
        hob=next(o for o in meshes if o.name.endswith('.hob'))
        hb=bounds(hob)
        hit,location,normal,index,obj,matrix=scene.ray_cast(deps,Vector(((hb[0]+hb[3])/2,(hb[1]+hb[4])/2,hb[5]+.1)),Vector((0,0,-1)),distance=.2)
        assert hit and obj==hob, 'Worktop covers the inset hob'
        detail_checks['hobUncovered']=True
        root_data=Path(__file__).resolve().parents[1]/'data'
        items=json.loads((root_data/'furniture.json').read_text(encoding='utf-8'))['items']
        catalog={t['type']:t for t in json.loads((root_data/'furniture-catalog.json').read_text(encoding='utf-8'))['types']}
        house=json.loads((root_data/'house.json').read_text(encoding='utf-8'))
        import math
        for item in items:
            if item['type'] not in ('kitchen-counter','refrigerator'): continue
            parts=[o for o in meshes if o.name.startswith('furniture.'+item['id']+'.')]
            if not parts: continue
            w,d,h=[item.get(k+'Override',catalog[item['type']][k]) for k in ('width','depth','height')]
            a=math.radians(item['rotation']); c,s=math.cos(a),math.sin(a)
            for part in parts:
                assert json.loads(part['source_json'])==item, 'Furniture provenance changed'
                for vertex in part.data.vertices:
                    v=part.matrix_world@vertex.co
                    px=v.x-item['x']; py=v.y+item['z']
                    local_x=c*px+s*py; local_z=s*px-c*py
                    assert abs(local_x)<=w/2+.0001 and abs(local_z)<=d/2+.0001, part.name
                    assert -.0001<=v.z-house['levels'][f"fl{item['level']}"]<=h+.0001, part.name
        detail_checks['appliancePartsWithinSourceBounds']=True
    # Every generated furniture part must retain its source and vertical offset.
    import math
    root_source=Path(__file__).resolve().parents[1]
    furniture=json.loads((root_source/'data/furniture.json').read_text(encoding='utf-8'))['items']
    cat={t['type']:t for t in json.loads((root_source/'data/furniture-catalog.json').read_text(encoding='utf-8'))['types']}
    house=json.loads((root_source/'data/house.json').read_text(encoding='utf-8'))
    for item in furniture:
        parts=[o for o in meshes if o.name.startswith('furniture.'+item['id']+'.')]
        if not parts: continue
        for part in parts:
            assert json.loads(part['source_json'])==item
        if item['type']!='television': continue
        w,d,h=[item.get(k+'Override',cat[item['type']][k]) for k in ('width','depth','height')]
        theta=math.radians(item['rotation']); c,s=math.cos(theta),math.sin(theta)
        coordinates=[]
        for part in parts:
            for vertex in part.data.vertices:
                v=part.matrix_world @ vertex.co
                px,py=v.x-item['x'],v.y+item['z']
                coordinates.append((c*px+s*py,s*px-c*py,v.z-house['levels'][f"fl{item['level']}"]))
        lo=[min(v[a] for v in coordinates) for a in range(3)]
        hi=[max(v[a] for v in coordinates) for a in range(3)]
        expected_lo=[-w/2,-d/2,item.get('elevation',0)]
        expected_hi=[w/2,d/2,item.get('elevation',0)+h]
        assert max(abs(a-b) for a,b in zip(lo+hi,expected_lo+expected_hi))<.0001
        detail_checks['televisionSourceBoundsAndElevation']=True
    expected={o.name:bounds(o) for o in meshes}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/'interior.glb'))
    actual={o.name:bounds(o) for o in bpy.context.scene.objects if o.type=='MESH'}
    assert expected.keys()==actual.keys(), 'GLB lost mesh identities'
    # GLB applies the bevel modifier. Compare its expanded bounds within 1mm.
    error=max(abs(a-b) for name in expected for a,b in zip(expected[name],actual[name]))
    assert error<.001, f'GLB axis/scale discrepancy: {error}'
    result=dict(meshes=len(meshes),closedSolids=True,ceilingCheckpoints=hits,
                guestWindowUnblocked=True,glbMaxBoundsErrorMetres=error,unrealImportVerified=False,
                meshBoundsBlenderMetres=actual,furnitureDetails=detail_checks)
    (root/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='meshBoundsBlenderMetres'}))


if __name__=='__main__': main()
