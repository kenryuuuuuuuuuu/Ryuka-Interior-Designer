"""Dimensioned surface UVs and Cycles reference finishes; no geometry displacement."""
import math


def assign_surface_uv(obj):
    # Current generated ceilings have slope along source z. Keep x as board length.
    uv=obj.data.uv_layers.new(name='SurfaceMetres')
    for polygon in obj.data.polygons:
        normal=polygon.normal
        factor=math.sqrt(1+(normal.y/normal.z)**2) if abs(normal.z)>.5 else 1
        for index in polygon.loop_indices:
            vertex=obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv=(vertex.x,-vertex.y*factor)
    obj['surface_uv_units']='metres; U=source x, V=source z corrected for plane slope'


def apply_pattern(mat,color,detail,rgb):
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    shader=nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=detail['roughness']
    pattern=detail['pattern']
    tex=nodes.new('ShaderNodeTexCoord')
    mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Rotation'].default_value[2]=-math.radians(pattern['rotationDeg'])
    links.new(tex.outputs['UV'],mapping.inputs['Vector'])
    brick=nodes.new('ShaderNodeTexBrick');brick.offset=0;brick.offset_frequency=1
    brick.inputs['Scale'].default_value=1
    brick.inputs['Brick Width'].default_value=pattern['lengthCm']/100
    brick.inputs['Row Height'].default_value=pattern['widthCm']/100
    brick.inputs['Mortar Size'].default_value=pattern['seamCm']/200
    brick.inputs['Mortar Smooth'].default_value=.0003
    base=rgb(color)
    brick.inputs['Color1'].default_value=(*[v*.97 for v in base],1)
    brick.inputs['Color2'].default_value=(*[v*1.03 for v in base],1)
    brick.inputs['Mortar'].default_value=(*[v*(.62 if pattern['kind']=='boards' else .84) for v in base],1)
    links.new(mapping.outputs['Vector'],brick.inputs['Vector'])
    links.new(brick.outputs['Color'],shader.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0005
    bump.invert=True
    links.new(brick.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
