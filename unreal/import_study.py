"""Run inside UE's Python commandlet in a newly generated project only."""
import hashlib
import json
import math
from pathlib import Path
import unreal


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def material(name, color, roughness=.6, glass=False, detail=None):
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_'+name, '/Game/Generated/Finishes', unreal.Material, unreal.MaterialFactoryNew())
    editing = unreal.MaterialEditingLibrary
    def connect(source,output,target,pin):
        if not editing.connect_material_expressions(source,output,target,pin):
            raise RuntimeError(f'Material connection failed: {target.get_class().get_name()} / {pin}')
    rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    node = editing.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
    node.set_editor_property('constant', unreal.LinearColor(*rgb, 1))
    output=node
    if detail:
        # World coordinates are centimetres. No UV dependency or geometry displacement.
        position=editing.create_material_expression(asset,unreal.MaterialExpressionWorldPosition)
        scale=editing.create_material_expression(asset,unreal.MaterialExpressionConstant3Vector)
        scale.set_editor_property('constant',unreal.LinearColor(*detail['noiseScalePerCm'],1))
        stretched=editing.create_material_expression(asset,unreal.MaterialExpressionMultiply)
        connect(position,'',stretched,'A')
        connect(scale,'',stretched,'B')
        noise=editing.create_material_expression(asset,unreal.MaterialExpressionNoise)
        for key,value in dict(scale=1.0,levels=2,quality=1,output_min=detail['colorMin'],output_max=detail['colorMax']).items():
            noise.set_editor_property(key,value)
        connect(stretched,'',noise,'')
        modulation=noise
        if detail.get('grain'):
            # Long, gently distorted grain; small-scale random noise alone looks like grit.
            noise.set_editor_property('output_min',0.0); noise.set_editor_property('output_max',1.0)
            across=editing.create_material_expression(asset,unreal.MaterialExpressionComponentMask)
            across.set_editor_property('r',False); across.set_editor_property('g',True)
            across.set_editor_property('b',False); across.set_editor_property('a',False)
            connect(stretched,'',across,'')
            phase=editing.create_material_expression(asset,unreal.MaterialExpressionAdd)
            connect(across,'',phase,'A')
            connect(noise,'',phase,'B')
            wave=editing.create_material_expression(asset,unreal.MaterialExpressionSine)
            wave.set_editor_property('period',1.0)
            connect(phase,'',wave,'')
            amplitude=editing.create_material_expression(asset,unreal.MaterialExpressionMultiply)
            amplitude.set_editor_property('const_b',(detail['colorMax']-detail['colorMin'])/2)
            connect(wave,'',amplitude,'A')
            modulation=editing.create_material_expression(asset,unreal.MaterialExpressionAdd)
            modulation.set_editor_property('const_b',(detail['colorMax']+detail['colorMin'])/2)
            connect(amplitude,'',modulation,'A')
        output=editing.create_material_expression(asset,unreal.MaterialExpressionMultiply)
        connect(node,'',output,'A')
        connect(modulation,'',output,'B')
    editing.connect_material_property(output, '', unreal.MaterialProperty.MP_BASE_COLOR)
    def scalar(prop, value):
        expr = editing.create_material_expression(asset, unreal.MaterialExpressionConstant)
        expr.set_editor_property('r', value)
        editing.connect_material_property(expr, '', prop)
    scalar(unreal.MaterialProperty.MP_ROUGHNESS, roughness)
    if glass:
        asset.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        scalar(unreal.MaterialProperty.MP_OPACITY, .08)
        # Provisional clear visual pane. No calibrated transmitted shadows/refraction.
        asset.set_editor_property('two_sided', True)
    editing.recompile_material(asset)
    return asset


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
    details=json.loads((project/'finish-settings.json').read_text(encoding='utf-8'))['roles']
    library={variant:{role:material(variant+'_'+role,palette[role],
        roughness=details[role]['roughness'],detail=details[role]) for role in details}
        for variant,palette in study['settings']['variants'].items()}
    materials=library[study['variant']]
    glass=material('Glass_provisional','ffffff',.02,glass=True)
    bindings={}
    for actor in meshes:
        comp = actor.static_mesh_component
        for index, mat in enumerate(comp.get_materials()):
            if mat.get_name() in materials:
                bindings.setdefault(actor.get_actor_label(),{})[str(index)]=mat.get_name()
                comp.set_material(index, materials[mat.get_name()])
            elif mat.get_name()=='Glass_provisional':
                comp.set_material(index,glass)
        if actor.get_actor_label().endswith('_glass'):
            comp.set_cast_shadow(False)

    def spawn(cls, label, location=unreal.Vector(), rotation=unreal.Rotator()):
        actor = actors.spawn_actor_from_class(cls, location, rotation)
        actor.set_actor_label(label)
        actor.set_folder_path('Generated/Study')
        return actor
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
    camera_data = study['settings']['camera']
    source = json.loads((package/'inputs/data/house.json').read_text(encoding='utf-8'))
    floor = source['levels']['fl1']
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
                coordinates='UE centimetres: X=source x, Y=source z, Z=source y',
                variant=state['variant'],sunAzimuth=state['azimuthDeg'],sunElevation=state['elevationDeg'],
                sunLux=state['sunLux'],exposureEV100=state['exposureEV100'],
                comparisonState=state,finishSettingsSHA256=hashlib.sha256((project/'finish-settings.json').read_bytes()).hexdigest(),
                limitations=['Procedural world-space finishes are estimated, not measured product textures',
                             'Glass shadow disabled; transmission and illuminance not calibrated',
                             'Editor study; no runtime interface or collision walkthrough yet'])
    write_json(project/'import-verification.json',result)
    unreal.log('VISUAL_TWIN_IMPORT_OK '+json.dumps(result))


if __name__ == '__main__':
    main()
