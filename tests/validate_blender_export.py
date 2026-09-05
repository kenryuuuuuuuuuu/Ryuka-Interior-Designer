"""Run in a fresh background Blender: --python this_file -- --package <path>.

Verify GLB round-trip names, world bounds, source metadata, and GL floor height.
This is not a substitute for Unreal import/lighting validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def bounds(obj):
    points = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    return [min(p[i] for p in points) for i in range(3)] + [max(p[i] for p in points) for i in range(3)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--render-plan', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    package = args.package.resolve()
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    for name, artifact in manifest['artifacts'].items():
        assert hashlib.sha256((package / name).read_bytes()).hexdigest() == artifact['sha256'], name
    bpy.ops.wm.open_mainfile(filepath=str(package / 'house.blend'))
    expected = {o.name: bounds(o) for o in bpy.context.scene.objects if o.type == 'MESH'}
    metadata = {o.name: o['source_wall'] for o in bpy.context.scene.objects if 'source_wall' in o}
    assert abs(expected['slab-1f-a1'][5] - .707) < 1e-5, '1F GL floor offset'
    assert abs(expected['slab-2f-main'][5] - 3.439) < 1e-5, '2F GL floor offset'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(package / 'house.glb'))
    actual = {o.name: bounds(o) for o in bpy.context.scene.objects if o.type == 'MESH'}
    assert expected.keys() == actual.keys(), 'Object identities changed during GLB round-trip'
    maximum = max(abs(a-b) for name in expected for a, b in zip(expected[name], actual[name]))
    assert maximum < 1e-5, f'Axis/scale/bounds mismatch: {maximum} m'
    for name, value in metadata.items():
        assert bpy.data.objects[name]['source_wall'] == value, name
    result = dict(meshes=len(expected), maxBoundsErrorMetres=maximum,
                  exteriorObjectsWithMetadata=len(metadata), unrealImportVerified=False)
    (package / 'verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))
    if args.render_plan:
        # Diagnostic 1F plan only: roofs/2F hidden; no implication of interior realism.
        bpy.ops.wm.open_mainfile(filepath=str(package / 'house.blend'))
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                obj.hide_render = bounds(obj)[2] > 3.3 or any(c.name == 'Roofs' for c in obj.users_collection)
        bpy.ops.object.camera_add(location=(9.5, -3.2, 30))
        camera = bpy.context.object
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 21
        bpy.context.scene.camera = camera
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.show_cavity = True
        scene.display.shading.background_type = 'WORLD'
        scene.world.color = (.8, .8, .8)
        scene.render.resolution_x, scene.render.resolution_y = 1400, 560
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(package / 'qa-plan.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
