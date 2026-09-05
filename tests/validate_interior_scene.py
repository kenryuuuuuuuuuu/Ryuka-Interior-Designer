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
                meshBoundsBlenderMetres=actual)
    (root/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='meshBoundsBlenderMetres'}))


if __name__=='__main__': main()
