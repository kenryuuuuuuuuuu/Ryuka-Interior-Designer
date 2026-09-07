"""Blender --background --python this.py -- package-directory: physical UV scale."""
import sys
from pathlib import Path
import bpy
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(root/'interior.blend'))
def verify():
    surfaces=edges=0
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith(('slab.','ceiling.')):continue
        assert obj.data.uv_layers.active,obj.name
        uv=obj.data.uv_layers.active.data
        for face in obj.data.polygons:
            if abs(face.normal.z)<.5:continue
            if abs(face.normal.x)>1e-5:continue
            loops=list(face.loop_indices)
            for a,b in zip(loops,loops[1:]+loops[:1]):
                pa=obj.data.vertices[obj.data.loops[a].vertex_index].co
                pb=obj.data.vertices[obj.data.loops[b].vertex_index].co
                assert abs((pa-pb).length-(uv[a].uv-uv[b].uv).length)<.0001,obj.name
                edges+=1
        surfaces+=1
    assert surfaces>0 and edges>0
    return surfaces,edges
print('Blend surface scale:',verify())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/'interior.glb'))
print('GLB surface scale:',verify())
