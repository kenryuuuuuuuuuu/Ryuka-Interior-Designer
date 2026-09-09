"""Run inside UE's Python commandlet in a newly generated project only."""
import hashlib
import json
import math
from pathlib import Path
import unreal
from finish_settings import details_for_variant
from material_builder import material, marker_material
from surface_finish_overrides import resolve_finish
from lighting import validate_lighting_bindings
import multi_room_state as mrs


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    project = Path(unreal.Paths.project_dir()).resolve()
    job = json.loads((project/'import-job.json').read_text(encoding='utf-8'))
    package = project/'SourcePackage'
    manifest = json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    for name, artifact in manifest['artifacts'].items():
        assert hashlib.sha256((package/name).read_bytes()).hexdigest() == artifact['sha256'], name
    study = json.loads((package/'study.json').read_text(encoding='utf-8'))
    verification = json.loads((package/'verification.json').read_text(encoding='utf-8'))
    expected = verification['meshBoundsBlenderMetres']
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert not unreal.EditorAssetLibrary.does_asset_exist('/Game/Generated/House'), 'Use a new output project.'
    assert level.new_level('/Game/Generated/House')
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    params = unreal.ImportAssetParameters()
    params.is_automated = True
    params.replace_existing = False
    assert manager.import_scene('/Game/Generated/Geometry', manager.create_source_data(str(package/'interior.glb')), params)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    meshes = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)]
    # The measured Interchange mapping is UE=(Blender X,-Y,Z)*100.
    by_name = {name.replace('.', '_'): bounds for name,bounds in expected.items()}
    assert len(by_name) == len(expected), 'Sanitized names collide.'
    assert {a.get_actor_label() for a in meshes} == by_name.keys(), 'Lost/extra meshes on import.'
    errors = []
    for actor in meshes:
        b = by_name[actor.get_actor_label()]
        reference = [b[0]*100, -b[4]*100, b[2]*100, b[3]*100, -b[1]*100, b[5]*100]
        center, extent = actor.get_actor_bounds(False)
        actual = list((center-extent).to_tuple())+list((center+extent).to_tuple())
        errors += [abs(x-y) for x,y in zip(reference, actual)]
        actor.set_folder_path('Generated/House')
    assert max(errors) < .1, f'Import bounds differ by {max(errors)} cm (limit 1mm).'
    finish_document=json.loads((project/'finish-settings.json').read_text(encoding='utf-8'))
    library={}
    for variant,palette in study['settings']['variants'].items():
        details=details_for_variant(finish_document,variant)
        library[variant]={role:material(variant+'_'+role,palette[detail.get('paletteRole',role)],
            roughness=detail['roughness'],detail=detail) for role,detail in details.items()}
    # W07-G1: role-bindings.json (Blender's own knowledge of which room a
    # furniture/decor object belongs to -- envelope/exterior/roof geometry
    # is never in it, see blender/build_interior.py) decides which room's
    # OWN active variant a given actor's whole-scene role slots use;
    # anything not in it (exterior walls/roof, un-owned geometry) uses the
    # fixed baseline variant (spec section 3: "対象外室/外皮は既存の基準
    # 材質を維持"). This is only the INITIAL assignment -- every later
    # apply_state() (including the one this same import performs below)
    # re-derives it the same way from study-bindings.json's own roomId tag.
    role_bindings_doc=json.loads((package/'role-bindings.json').read_text(encoding='utf-8'))
    actor_room={name.replace('.','_'):room_id for name,room_id in role_bindings_doc['actors'].items()}
    room_materials={room_id:library[study['roomStates'][room_id]['variant']] for room_id in study['roomIds']}
    base_materials=library[mrs.BASE_VARIANT]
    glass=material('Glass_provisional','ffffff',.02,glass=True)
    bindings={}
    for actor in meshes:
        comp = actor.static_mesh_component
        label=actor.get_actor_label()
        room_id=actor_room.get(label)
        materials=room_materials[room_id] if room_id in room_materials else base_materials
        for index, mat in enumerate(comp.get_materials()):
            if mat.get_name() in materials:
                role='floor' if label.startswith('slab_') and mat.get_name()=='wood' else mat.get_name()
                entry=bindings.setdefault(label,dict(roomId=room_id,slots={}))
                entry['slots'][str(index)]=role
                comp.set_material(index, materials[role])
            elif mat.get_name()=='Glass_provisional':
                comp.set_material(index,glass)
        if label.endswith('_glass'):
            comp.set_cast_shadow(False)

    # W04: rebuild surface-bindings.json using the ACTUAL imported actor
    # labels (Blender's own dotted mesh names get sanitized on import, same
    # rule already used above for meshBoundsBlenderMetres).
    #
    # W04 review v2 R1: one PARAMETRIC marker material is built per (surface,
    # variant) -- not just the current study.variant -- because each
    # variant's own pattern (planks/tile/plain noise; resolve_finish()'s
    # 'detail') is baked into that material's node graph at creation time,
    # not something a MID's Color/Roughness parameters can change. Switching
    # the effective variant later (whole-scene, a per-surface override, a
    # loaded scenario, A/B) means switching which of these PARENT materials
    # a slot's MID is built from -- see study_controls.apply_state() and
    # Walkthrough.cpp's ApplyConditions(), which both load
    # M_Surf_<surfaceId>_<variant> by name rather than reusing whatever
    # parent happens to already be assigned. Only the slot for the initial
    # study.variant is actually assigned here; every later apply (including
    # the one study_controls.apply_state() below performs for this same
    # import) picks the correct parent itself.
    blender_bindings = json.loads((package/'surface-bindings.json').read_text(encoding='utf-8'))
    finish_document = json.loads((project/'finish-settings.json').read_text(encoding='utf-8'))
    actor_by_label = {a.get_actor_label(): a for a in meshes}
    surface_bindings = {}
    for surface_id, info in blender_bindings['surfaces'].items():
        markers_by_variant = {}
        for variant in study['settings']['variants']:
            finish = resolve_finish(finish_document, study['settings']['variants'], info['kind'], variant)
            markers_by_variant[variant] = marker_material(
                f'Surf_{surface_id}_{variant}', finish['colorHex'], finish['roughness'], detail=finish['detail'])
        marker = markers_by_variant[study['roomStates'][info['roomId']]['variant']]
        entry = dict(roomId=info['roomId'], kind=info['kind'], status=info['status'],
            label=info.get('label'), meshes=[])
        for mesh_ref in info['meshes']:
            actor_label = mesh_ref['name'].replace('.', '_')
            actor = actor_by_label.get(actor_label)
            if actor is None:
                continue  # should not happen: the earlier bounds check already asserted no meshes were lost on import
            actor.static_mesh_component.set_material(mesh_ref['slot'], marker)
            entry['meshes'].append(dict(actor=actor_label, slot=mesh_ref['slot']))
        surface_bindings[surface_id] = entry
    write_json(project/'surface-bindings.json', dict(schemaVersion='1.0.0', surfaces=surface_bindings))

    def spawn(cls, label, location=unreal.Vector(), rotation=unreal.Rotator()):
        actor = actors.spawn_actor_from_class(cls, location, rotation)
        actor.set_actor_label(label)
        actor.set_folder_path('Generated/Study')
        return actor
    context_report=None
    if (project/'site-context.json').exists():
        from site_context import create_context
        context_report=dict(sha256=hashlib.sha256((project/'site-context.json').read_bytes()).hexdigest(),
            boxes=create_context(json.loads((project/'site-context.json').read_text(encoding='utf-8-sig')),
                                 material('Context_estimated','9c9c9c',.85)))
    # W06: fixtures/lights resolved ONCE by Blender (build_electrical_lighting())
    # into lighting-bindings.json; UE only spawns the LIGHT actors at those
    # already-resolved positions/directions, it never re-derives mount
    # geometry itself. The fixture MESH is not spawned separately here --
    # Blender's build_electrical_lighting() already added it to the scene
    # exported into interior.glb, so it arrives through the normal Interchange
    # import above like any other geometry (W06-v1 review R2: a previous
    # version also spawned a fixed-size placeholder Cylinder here, doubling
    # every fixture's visible geometry). A pre-W06 package simply has no
    # lighting-bindings.json -- nothing to spawn, study_controls.py's own
    # lighting menu/apply_state() likewise treat its absence as "no fixtures
    # in this project".
    lighting_report=None
    lighting_path=package/'lighting-bindings.json'
    if lighting_path.exists():
        lighting_bindings=validate_lighting_bindings(json.loads(lighting_path.read_text(encoding='utf-8')))
        write_json(project/'lighting-bindings.json',lighting_bindings)
        for fixture in lighting_bindings['fixtures']:
            # W06-v1 review R2: the light itself sits at emitPositionM (the
            # fixture housing's underside), not positionM (the mesh's mount
            # origin/top) -- never inside the ceiling void or the fixture's
            # own opaque body.
            x,y,z=fixture['emitPositionM']
            location=unreal.Vector(x*100,z*100,y*100)
            dx,dy,dz=fixture['directionVector']
            direction=unreal.Vector(dx,dz,dy)
            light_class=unreal.SpotLight if fixture['source']=='spot' else unreal.PointLight
            light_actor=spawn(light_class,'Light_'+fixture['id'],location,
                unreal.MathLibrary.find_look_at_rotation(unreal.Vector(),direction))
            light_actor.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            light_actor.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
            light_actor.light_component.set_intensity(0)  # study_controls.apply_state() sets the real initial value below
            light_actor.light_component.set_editor_property('use_temperature',True)
            light_actor.light_component.set_editor_property('temperature',fixture['temperatureK'])
            if fixture['source']=='spot':
                light_actor.light_component.set_editor_property('inner_cone_angle',fixture['spotAngleDeg']/2)
                light_actor.light_component.set_editor_property('outer_cone_angle',fixture['spotAngleDeg']/2)
        lighting_report=dict(sha256=hashlib.sha256(lighting_path.read_bytes()).hexdigest(),
            fixtureIds=[f['id'] for f in lighting_bindings['fixtures']])
    lighting = study['lighting']
    az = math.radians(lighting['azimuthDeg'])
    el = math.radians(lighting['elevationDeg'])
    direction = unreal.Vector(-math.sin(az)*math.cos(el), math.cos(az)*math.cos(el), -math.sin(el))
    sun = spawn(unreal.DirectionalLight, 'Sun_manual_angle', rotation=unreal.MathLibrary.find_look_at_rotation(unreal.Vector(),direction))
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(job['sunLux'])
    sun.light_component.set_editor_property('atmosphere_sun_light', True)
    spawn(unreal.SkyAtmosphere, 'Sky')
    sky = spawn(unreal.SkyLight, 'SkyLight')
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('real_time_capture', True)
    sky.light_component.set_intensity(1)
    post = spawn(unreal.PostProcessVolume, 'Fixed_exposure')
    post.set_editor_property('unbound', True)
    pp = unreal.PostProcessSettings()
    for key,value in dict(auto_exposure_min_brightness=job['exposureEV100'],
                          auto_exposure_max_brightness=job['exposureEV100'],
                          auto_exposure_bias=0.0).items():
        pp.set_editor_property('override_'+key, True)
        pp.set_editor_property(key,value)
    post.set_editor_property('settings',pp)
    # W07-G1: the initial camera is the scope's default (walkable) room's
    # own safe camera (data/visual/room-render-settings.json), not a single
    # project-wide one -- study_controls.select_room() uses the exact same
    # source/conversion for every later room switch.
    source = json.loads((package/'inputs/data/house.json').read_text(encoding='utf-8'))
    room_render_settings=mrs.validate_room_render_settings(
        json.loads((package/'inputs/data/visual/room-render-settings.json').read_text(encoding='utf-8')))
    legacy_study=json.loads((package/'inputs/data/visual/guest-ldk-study.json').read_text(encoding='utf-8'))
    camera_room=next(r for r in source['rooms'] if r['id']==study['activeRoomId'])
    camera_data = mrs.room_render(room_render_settings,study['activeRoomId'],legacy_study)['camera']
    floor = source['levels'][f"fl{camera_room['level']}"]
    def point(p): return unreal.Vector(p[0]*100,p[1]*100,(p[2]+floor)*100)
    position,target = point(camera_data['position']),point(camera_data['target'])
    camera = spawn(unreal.CineCameraActor, 'Camera_guest_LDK', position, unreal.MathLibrary.find_look_at_rotation(position,target))
    cc = camera.get_cine_camera_component()
    cc.set_editor_property('filmback',unreal.CameraFilmbackSettings(sensor_width=36,sensor_height=20.25))
    cc.set_editor_property('current_focal_length',camera_data['lensMm'])
    focus=unreal.CameraFocusSettings()
    focus.set_editor_property('focus_method',unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings',focus)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(position,camera.get_actor_rotation())
    write_json(project/'study-bindings.json',bindings)
    import study_controls
    state=study_controls.initial_state()
    study_controls.apply_state(state)
    study_controls.save()
    unreal.EditorAssetLibrary.save_directory('/Game/Generated',only_if_is_dirty=False,recursive=True)
    assert level.save_current_level()
    state=study_controls.current_state()
    result=dict(engineVersion=unreal.SystemLibrary.get_engine_version(), meshes=len(meshes),
                maxBoundsErrorCm=max(errors),unrealImportVerified=True,siteDaylightCalibrated=False,
                sourceManifestSHA256=hashlib.sha256((package/'manifest.json').read_bytes()).hexdigest(),
                siteContext=context_report,
                lighting=lighting_report,
                surfaceShaderSHA256=hashlib.sha256((project/'surface_finish.hlsl').read_bytes()).hexdigest(),
                floorShaderSHA256=hashlib.sha256((project/'floor_finish.hlsl').read_bytes()).hexdigest(),
                coordinates='UE centimetres: X=source x, Y=source z, Z=source y',
                scopeId=state['scopeId'],roomIds=study['roomIds'],activeRoomId=state['activeRoomId'],
                activeVariant=state['roomStates'][state['activeRoomId']]['variant'],
                sunAzimuth=state['azimuthDeg'],sunElevation=state['elevationDeg'],
                sunLux=state['sunLux'],exposureEV100=state['exposureEV100'],
                comparisonState=state,finishSettingsSHA256=hashlib.sha256((project/'finish-settings.json').read_bytes()).hexdigest(),
                limitations=['Procedural world-space finishes are estimated, not measured product textures',
                             'Glass shadow disabled; transmission and illuminance not calibrated',
                             'Editor study; no runtime interface or collision walkthrough yet'])
    write_json(project/'import-verification.json',result)
    unreal.log('VISUAL_TWIN_IMPORT_OK '+json.dumps(result))


if __name__ == '__main__':
    main()
