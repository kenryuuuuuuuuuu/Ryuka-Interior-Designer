"""UE material creation, shared by the one-time import (import_study.py) and
the ongoing editor session (study_controls.py) -- moved out of import_study.py
so both can create materials identically without study_controls.py reaching
into a script that only runs once via the import commandlet.

material() builds the node graph for one finish (whole-scene role material,
or -- with parametric=True -- a single surface-registry id's marker
material). Both share the exact same pattern/plank/noise logic (`detail`),
so a registered-but-un-overridden surface renders with the same texture as
its surroundings, not a flat colour (W04 review R1: replacing every bound
surface's material with a flat Color/Roughness constant regressed even
un-overridden surfaces). parametric=True additionally exposes the material's
base colour/roughness as a MaterialExpressionVectorParameter/
ScalarParameter ('Color'/'Roughness') instead of baked constants, still
multiplied against the same pattern/noise nodes -- a UMaterialInstanceDynamic
made from it is how a per-surface override actually changes just the colour/
roughness while keeping the pattern, at both editor-time (study_controls.py)
and PIE/packaged runtime (Walkthrough.cpp). Creating a brand-new material
ASSET per arbitrary colour choice is an editor-only operation and not
available in the C++ walkthrough, hence the MID approach instead.
marker_material() is a thin wrapper kept for import_study.py's call site."""
from pathlib import Path
import unreal


def rgb(color):
    values = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    return [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
_rgb = rgb  # internal alias kept for the long-standing call sites below


def material(name, color, roughness=.6, glass=False, detail=None, parametric=False):
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_'+name, '/Game/Generated/Finishes', unreal.Material, unreal.MaterialFactoryNew())
    editing = unreal.MaterialEditingLibrary
    def connect(source,output,target,pin):
        if not editing.connect_material_expressions(source,output,target,pin):
            raise RuntimeError(f'Material connection failed: {target.get_class().get_name()} / {pin}')
    rgb = _rgb(color)
    if parametric:
        # Overridable base colour (W04 per-surface override), still fed into
        # the same pattern/noise multiply chain below as the plain constant
        # would be -- a MID made from this asset can change 'Color' without
        # losing the underlying texture.
        node = editing.create_material_expression(asset, unreal.MaterialExpressionVectorParameter)
        node.set_editor_property('parameter_name', 'Color')
        node.set_editor_property('default_value', unreal.LinearColor(*rgb, 1))
    else:
        node = editing.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
        node.set_editor_property('constant', unreal.LinearColor(*rgb, 1))
    output=node
    if detail and detail.get('pattern'):
        coordinates=editing.create_material_expression(asset,unreal.MaterialExpressionTextureCoordinate)
        coordinates.set_editor_property('coordinate_index',0)
        pattern=editing.create_material_expression(asset,unreal.MaterialExpressionCustom)
        pattern.set_editor_property('code',(Path(unreal.Paths.project_dir())/'surface_finish.hlsl').read_text(encoding='utf-8'))
        pattern.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        names=['UV','Width','Length','Seam','Angle','Mode']; inputs=[]
        for key in names:
            entry=unreal.CustomInput();entry.set_editor_property('input_name',key);inputs.append(entry)
        pattern.set_editor_property('inputs',inputs);connect(coordinates,'',pattern,'UV')
        values=[detail['pattern'][k] for k in ['widthCm','lengthCm','seamCm','rotationDeg']]+[1 if detail['pattern']['kind']=='boards' else 0]
        for key,value in zip(names[1:],values):
            constant=editing.create_material_expression(asset,unreal.MaterialExpressionConstant)
            constant.set_editor_property('r',value);connect(constant,'',pattern,key)
        output=editing.create_material_expression(asset,unreal.MaterialExpressionMultiply)
        connect(node,'',output,'A');connect(pattern,'',output,'B')
    elif detail and detail.get('planks'):
        position=editing.create_material_expression(asset,unreal.MaterialExpressionWorldPosition)
        pattern=editing.create_material_expression(asset,unreal.MaterialExpressionCustom)
        pattern.set_editor_property('code',(Path(unreal.Paths.project_dir())/'floor_finish.hlsl').read_text(encoding='utf-8'))
        pattern.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        names=['P','Width','Length','Seam','Angle']
        inputs=[]
        for name in names:
            custom_input=unreal.CustomInput(); custom_input.set_editor_property('input_name',name)
            inputs.append(custom_input)
        pattern.set_editor_property('inputs',inputs)
        connect(position,'',pattern,'P')
        for name,key in zip(names[1:],['widthCm','lengthCm','seamCm','rotationDeg']):
            scalar_input=editing.create_material_expression(asset,unreal.MaterialExpressionConstant)
            scalar_input.set_editor_property('r',detail['planks'][key])
            connect(scalar_input,'',pattern,name)
        output=editing.create_material_expression(asset,unreal.MaterialExpressionMultiply)
        connect(node,'',output,'A'); connect(pattern,'',output,'B')
    elif detail:
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
    if parametric:
        rough_param = editing.create_material_expression(asset, unreal.MaterialExpressionScalarParameter)
        rough_param.set_editor_property('parameter_name', 'Roughness')
        rough_param.set_editor_property('default_value', roughness)
        editing.connect_material_property(rough_param, '', unreal.MaterialProperty.MP_ROUGHNESS)
    else:
        scalar(unreal.MaterialProperty.MP_ROUGHNESS, roughness)
    if glass:
        asset.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        scalar(unreal.MaterialProperty.MP_OPACITY, .08)
        # Provisional clear visual pane. No calibrated transmitted shadows/refraction.
        asset.set_editor_property('two_sided', True)
    editing.recompile_material(asset)
    return asset


def marker_material(name, color, roughness=.6, detail=None):
    """A parametric base for one surface-registry id's marker slot: 'Color'
    (Vector) and 'Roughness' (Scalar) parameters, defaulted to `color`/
    `roughness` (the surface's un-overridden, base-variant finish), with
    `detail` (the same per-kind/variant pattern/plank/noise dict passed to
    the whole-scene role materials -- see surface_finish_overrides.
    resolve_finish()'s 'detail' field) reused so an un-overridden or
    colour-only-overridden registered surface keeps its texture (W04 review
    R1). A UMaterialInstanceDynamic created from this and given different
    parameter values is how an override is actually applied -- this asset
    itself never changes after creation."""
    return material(name, color, roughness, detail=detail, parametric=True)
