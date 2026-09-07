"""Reproducible guest LDK material/sun-angle study, generated from shared data.

Blender --background --factory-startup --python-exit-code 1 --python this_file --
  --output build/guest-natural --variant natural --render
This is a provisional visual study, not calibrated site daylight analysis.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_house as house_builder
from surface_finishes import assign_surface_uv, apply_pattern
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'unreal'))
from finish_settings import details_for_variant
from furniture_assets import validate_bindings, asset_parts
from guest_decor import build as build_decor
from wall_geometry import opening_plane
from interior_geometry import ceiling_y, point_in_room, wall_polygons

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rgb(value):
    srgb = [int(value[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in srgb)


def material(name, color, roughness=.6, metallic=0, texture=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb(color), 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    mat.diffuse_color = (*rgb(color), 1)
    if texture:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        position = nodes.new('ShaderNodeTexCoord')
        scale = nodes.new('ShaderNodeVectorMath'); scale.operation = 'MULTIPLY'
        scale.inputs[1].default_value = (1.8, 45, 8) if texture == 'wood' else (160, 160, 160)
        links.new(position.outputs['Object'], scale.inputs[0])
        noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 1
        noise.inputs['Detail'].default_value = 3
        links.new(scale.outputs['Vector'], noise.inputs['Vector'])
        ramp = nodes.new('ShaderNodeValToRGB')
        for element, factor in zip(ramp.color_ramp.elements, (.65, 1.15)):
            element.color = (*[min(1, c*factor) for c in rgb(color)], 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0]); links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .12
        bump.inputs['Distance'].default_value = .0005
        links.new(noise.outputs['Fac'], bump.inputs['Height']); links.new(bump.outputs['Normal'], shader.inputs['Normal'])
        mat['transfer_note'] = 'Procedural detail needs baking for UE; diffuse fallback only in GLB.'
    return mat


def mesh(name, vertices, faces, mat, source=None, role=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces); data.update()
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data); bpy.context.scene.collection.objects.link(obj)
    if mat:
        data.materials.append(mat)
    if source:
        obj['source_json'] = json.dumps(source, ensure_ascii=False)
    if role:
        obj['surface_role'] = role
    return obj


def prism(name, polygon, vector, mat, source=None, role=None):
    n = len(polygon)
    vertices = polygon + [tuple(Vector(v)+Vector(vector)) for v in polygon]
    return mesh(name, vertices, [tuple(range(n-1, -1, -1)), tuple(range(n, 2*n))] +
                [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)], mat, source, role)


def block(name, x0, x1, z0, z1, y0, y1, mat, bevel=0, source=None):
    obj = prism(name, [(x0,-z0,y0), (x1,-z0,y0), (x1,-z1,y0), (x0,-z1,y0)],
                (0,0,y1-y0), mat, source)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL'); mod.width = bevel; mod.segments = 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def panel(name, wall, polygon, mat, source=None):
    t = wall['thickness']
    if wall['orientation'] == 'H':
        at = wall['z0']
        vertices = [(u, -at+t/2, y) for u, y in polygon]; vector = (0,-t,0)
    else:
        at = wall['x0']
        vertices = [(at-t/2, -u, y) for u, y in polygon]; vector = (t,0,0)
    return prism(name, vertices, vector, mat, source or wall, 'wall')


def openings(data):
    result = []
    for o in data['openings']:
        orientation, at = opening_plane(data, o)
        base = data['levels'][f"fl{o['level']}"]
        result.append(dict(o, orientation=orientation, at=at, start=o['offset'],
                           end=o['offset']+o['width'], bottom=base+o['sill'],
                           top=base+o['sill']+o['height'], exterior=True))
    for o in data['interiorDoors']:
        if o['orientation'] == 'D':
            continue
        base = data['levels'][f"fl{o['floor']}"]
        result.append(dict(o, level=o['floor'], at=o['wallAt'], start=o['center']-o['width']/2,
                           end=o['center']+o['width']/2, bottom=base, top=base+o['height'], exterior=False))
    return result


def build_envelope(data, mats):
    ops = openings(data)
    walls = [dict(w, thickness=data['defaults']['wallThickness']) for w in data['exteriorWalls']]
    walls += [dict(w, thickness=data['defaults']['interiorWallThickness']) for w in data['walls']]
    for special in data['specialWalls']:
        # Prevent coincident finish faces where the special wall overlaps an interior wall.
        remaining = []
        for w in walls:
            if w['level'] == special['level'] and w['orientation'] == 'V' and abs(w['x0']-special['x']) < 1e-6:
                for a,b in [(w['z0'], min(w['z1'], special['z0'])), (max(w['z0'], special['z1']), w['z1'])]:
                    if b-a > 1e-6:
                        remaining.append(dict(w, z0=a, z1=b))
            else:
                remaining.append(w)
        walls = remaining + [dict(special, orientation='V', x0=special['x'], x1=special['x'],
                                   thickness=data['defaults']['wallThickness'])]
    for g in data.get('guardWalls', []):
        horizontal = g['orientation'] == 'H'
        walls.append(dict(g, x0=g['from'] if horizontal else g['at'], x1=g['to'] if horizontal else g['at'],
                          z0=g['at'] if horizontal else g['from'], z1=g['at'] if horizontal else g['to'],
                          guardHeight=g['height'], thickness=data['defaults']['interiorWallThickness']))
    for w in walls:
        at = w['z0'] if w['orientation']=='H' else w['x0']
        cuts = [] if 'guardHeight' in w else [o for o in ops if o['level']==w['level'] and
                o['orientation']==w['orientation'] and abs(o['at']-at)<1e-6]
        for i, poly in enumerate(wall_polygons(data,w,cuts)):
            panel(f"wall.{w['id']}.{i}",w,poly,mats['wall'],dict(wall=w,openings=cuts))
    for i,r in enumerate(data['envelope']['slabs']):
        y = data['levels'][f"fl{r['level']}"]
        block(f"slab.{r['footprintId']}.{i}",r['x0'],r['x1'],r['z0'],r['z1'],y-.12,y,mats.get('floor',mats['wood']))
    for i,r in enumerate(data['envelope']['flatCeilings']):
        y = data['levels'][f"fl{r['level']}"]+data['defaults']['ceilingHeight']
        block(f"ceiling.flat.{i}",r['x0'],r['x1'],r['z0'],r['z1'],y,y+.025,mats['ceiling'])
    pieces = data['envelope']['slopedCeilingPieces']
    for i,p in enumerate(pieces):
        if not p['sloped']:
            continue
        y0,y1 = ceiling_y(data,p,p['z0']),ceiling_y(data,p,p['z1'])
        prism(f"ceiling.{p['roomId']}.{i}",[(p['x0'],-p['z0'],y0),(p['x1'],-p['z0'],y0),
              (p['x1'],-p['z1'],y1),(p['x0'],-p['z1'],y1)],(0,0,.025),mats['ceiling'],p,'ceiling')
        for flat in pieces:
            if flat['sloped'] or flat['roomId'] != p['roomId']:
                continue
            for at in (p['x0'],p['x1']):
                if min(abs(at-flat['x0']),abs(at-flat['x1'])) > 1e-6:
                    continue
                a,b = max(p['z0'],flat['z0']),min(p['z1'],flat['z1'])
                if b-a > 1e-6:
                    low = data['levels']['fl1']+data['defaults']['ceilingHeight']
                    panel(f"ceiling.riser.{i}.{at}",dict(orientation='V',x0=at,thickness=.04),
                          [(a,low),(b,low),(b,ceiling_y(data,p,b)),(a,ceiling_y(data,p,a))],mats['ceiling'],p)
    # Retain the rest of the building as sun occluders.
    roof_coll = house_builder.collection('Roofs')
    fps = {f['id']:f for f in data['footprints']}
    for roof in data['roofs']:
        house_builder.build_roof(data,roof,fps[roof['footprintId']],roof_coll,mats['frame'])
    return ops


def build_openings(ops, settings, mats):
    cfg = settings['window']; fw=cfg['frameWidth']
    glass=material('Glass.provisional','ffffff',.015)
    shader=glass.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Transmission Weight'].default_value=1
    shader.inputs['IOR'].default_value=cfg['ior']
    # Shadow rays pass through an estimated clear pane so Cycles does not require
    # expensive refractive caustics. This approximation is explicitly recorded.
    nodes,links=glass.node_tree.nodes,glass.node_tree.links
    path=nodes.new('ShaderNodeLightPath'); transparent=nodes.new('ShaderNodeBsdfTransparent')
    transparent.inputs[0].default_value=(.9,.9,.9,1)
    mix=nodes.new('ShaderNodeMixShader')
    links.new(path.outputs['Is Shadow Ray'],mix.inputs[0]); links.new(shader.outputs[0],mix.inputs[1])
    links.new(transparent.outputs[0],mix.inputs[2]); links.new(mix.outputs[0],nodes.get('Material Output').inputs['Surface'])
    for o in ops:
        if o['operation'] in ('open','open-arch'):
            continue
        w=dict(orientation=o['orientation'], x0=o['at'], z0=o['at'], thickness=cfg['frameDepth'])
        a,b,low,high=o['start'],o['end'],o['bottom'],o['top']
        def rect(suffix,x0,x1,y0,y1,mat,thickness=None):
            return panel(f"opening.{o['id']}.{suffix}",dict(w,thickness=thickness or w['thickness']),
                         [(x0,y0),(x1,y0),(x1,y1),(x0,y1)],mat,o)
        for suffix,x0,x1,y0,y1 in [('left',a,a+fw,low,high),('right',b-fw,b,low,high),
                                  ('head',a+fw,b-fw,high-fw,high),('sill',a+fw,b-fw,low,low+fw)]:
            rect(suffix,x0,x1,y0,y1,mats['frame'])
        if o['category']=='window':
            rect('glass',a+fw,b-fw,low+fw,high-fw,glass,cfg['glassThickness'])
            if o['operation']=='openable':
                mid=(a+b)/2
                rect('mullion',mid-fw/2,mid+fw/2,low+fw,high-fw,mats['frame'])
        else:
            # All actual leaves closed for the comparison; never turn an open arch into a marker.
            rect('closed-leaf',a+fw,b-fw,low+.005,high-fw,mats['cabinet'],.035)


def build_furniture(data,settings,mats):
    catalog={t['type']:t for t in read(ROOT/'data/furniture-catalog.json')['types']}
    bindings=validate_bindings(read(ROOT/'data/visual/asset-bindings.json'),
        read(ROOT/'data/furniture.json')['items'],read(ROOT/'data/furniture-catalog.json'))
    room=next(r for r in data['rooms'] if r['id']==settings['roomId'])
    items=[i for i in read(ROOT/'data/furniture.json')['items'] if i['level']==room['level'] and
           point_in_room(i['x'],i['z'],room['polygon'])]
    for item in items:
        profile=catalog[item['type']]
        w,d,h=[item.get(k+'Override',profile[k]) for k in ('width','depth','height')]
        created=[]
        def part(name,x0,x1,z0,z1,y0,y1,mat,bevel=.008):
            obj=block(f"furniture.{item['id']}.{name}",x0,x1,z0,z1,y0,y1,mat,bevel,item); created.append(obj)
            obj['detail_status']='estimated'
            obj['detail_note']='Procedural appearance only; source placement and outer dimensions retained. Product details unconfirmed.'
            return obj
        shape=profile['shape']
        binding=bindings.get(item['id'])
        native_asset={'roundTable':'round-table-v1','timberChair':'chair-timber-v1',
                      'rangeHood':'range-hood-v1','faucet':'faucet-v1','airConditioner':'air-conditioner-v1'}.get(shape)
        if binding or native_asset:
            binding=binding or dict(furnitureId=item['id'],assetId=native_asset,sizing='parametric',
                                    status='estimated',note='Default renderer for catalog shape; no explicit override.')
            for spec in asset_parts(binding['assetId'],w,d,h):
                kind=spec.get('kind','box')
                if kind!='box':
                    x0,x1,z0,z1,y0,y1=spec['bounds']
                    polygon=spec.get('polygon')
                    if kind=='ellipse':
                        polygon=[((x0+x1)/2+(x1-x0)/2*math.cos(j*2*math.pi/64),
                                  (z0+z1)/2+(z1-z0)/2*math.sin(j*2*math.pi/64)) for j in range(64)]
                    obj=prism(f"furniture.{item['id']}.{spec['name']}",[(x,-z,y0) for x,z in polygon],
                              (0,0,y1-y0),mats[spec['material']],item)
                    mod=obj.modifiers.new('Soft edges','BEVEL'); mod.width=spec['bevel']; mod.segments=3
                    obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
                    obj['detail_status']='estimated';created.append(obj)
                else:
                    obj=part(spec['name'],*spec['bounds'],mats[spec['material']],spec['bevel'])
                obj['asset_id']=binding['assetId']
                obj['asset_binding_json']=json.dumps(binding,ensure_ascii=False)
        elif shape in ('diningTable','coffeeTable','counterTable') or 'table' in item['type']:
            part('top',-w/2,w/2,-d/2,d/2,h-.04,h,mats['wood'],.015)
            for x in (-w/2+.045,w/2-.045):
                for z in (-d/2+.045,d/2-.045):
                    part('leg',x-.022,x+.022,z-.022,z+.022,0,h-.04,mats['frame'])
        elif item['type']=='chair':
            part('seat',-w/2,w/2,-d/2,d/2,.41,.46,mats['fabric'],.025)
            part('back',-w/2,w/2,-d/2,-d/2+.055,.46,h,mats['wood'],.015)
            for x in (-w/2+.035,w/2-.035):
                for z in (-d/2+.04,d/2-.04):
                    part('leg',x-.02,x+.02,z-.02,z+.02,0,.41,mats['wood'])
        elif 'sofa' in item['type']:
            part('base',-w/2,w/2,-d/2,d/2,.08,.31,mats['fabric'],.04)
            for j in range(2):
                a=-w/2+.07+j*(w-.14)/2
                part('cushion',a+.005,a+(w-.14)/2-.005,-d/2+.12,d/2-.01,.31,.43,mats['fabric'],.035)
            part('back',-w/2,w/2,-d/2,-d/2+.12,.31,h,mats['fabric'],.04)
            for x in (-w/2,w/2-.07):
                part('arm',x,x+.07,-d/2,d/2,.31,h*.8,mats['fabric'],.025)
        elif 'kitchen' in item['type']:
            # Partition closed solids around the basin; no hidden solid body filling it.
            sx0,sx1,sz0,sz1=-w*.27,w*.05,-d*.3,d*.22
            depth=min(.16,h*.2); top=min(.035,h*.05); lip=min(.008,d*.02)
            bottom=h-depth
            part('plinth',-w*.48,w*.48,-d*.46,d*.44,0,h*.08,mats['frame'],.003)
            part('body',-w/2,w/2,-d/2,d/2-.02,h*.08,bottom-.005,mats['cabinet'])
            surrounds=[('left',-w/2,sx0,-d/2,d/2),('right',sx1,w/2,-d/2,d/2),
                       ('rear',sx0,sx1,-d/2,sz0),('front',sx0,sx1,sz1,d/2)]
            for name,x0,x1,z0,z1 in surrounds:
                part('body-'+name,x0,x1,z0,min(z1,d/2-.02),bottom-.005,h-top,mats['cabinet'],.003)
                if name=='right':
                    hx0,hx1,hz0,hz1=w*.18,w*.43,-d*.3,d*.23
                    for k,xa,xb,za,zb in [('left',x0,hx0,z0,z1),('right',hx1,x1,z0,z1),
                                          ('rear',hx0,hx1,z0,hz0),('front',hx0,hx1,hz1,z1)]:
                        part('worktop-hob-'+k,xa,xb,za,zb,h-top,h,mats['stone'],.002)
                else:
                    part('worktop-'+name,x0,x1,z0,z1,h-top,h,mats['stone'],.002)
            part('sink-bottom',sx0,sx1,sz0,sz1,bottom-.005,bottom,mats['metal'],.002)
            for name,x0,x1,z0,z1 in [('left',sx0,sx0+lip,sz0,sz1),('right',sx1-lip,sx1,sz0,sz1),
                                    ('rear',sx0+lip,sx1-lip,sz0,sz0+lip),('front',sx0+lip,sx1-lip,sz1-lip,sz1)]:
                part('sink-'+name,x0,x1,z0,z1,bottom,h,mats['metal'],.002)
            gap=min(.004,w*.002)
            for j in range(3):
                a=-w/2+j*w/3
                part('front',a+gap,a+w/3-gap,d/2-.018,d/2-.004,h*.1,h-top-.012,mats['cabinet'],.002)
                part('pull',a+w*.04,a+w/3-w*.04,d/2-.004,d/2,h-top-.035,h-top-.025,mats['frame'],.001)
            # Thin inset hob replaces the visual proxy, kept within the source height.
            part('hob',w*.18,w*.43,-d*.3,d*.23,h-.004,h-.001,mats['black'],.001)
            for x,z in [(w*.245,-d*.12),(w*.365,d*.08)]:
                radius=min(w*.045,d*.105)
                n=48; vertices=[]
                for y in (h-.001,h):
                    vertices.extend((x+radius*math.cos(i*2*math.pi/n),-(z+radius*math.sin(i*2*math.pi/n)),y) for i in range(n))
                faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
                obj=mesh(f"furniture.{item['id']}.hob-zone",vertices,faces,mats['metal'],item)
                obj['detail_status']='estimated'; created.append(obj)
        elif 'refrigerator' in item['type']:
            front=d/2; door=min(.035,d*.08); gap=min(.006,h*.005)
            part('body',-w/2,w/2,-d/2,front-door,0,h,mats['metal'],.018)
            for name,lo,hi in [('freezer',0,h*.32-gap/2),('fridge',h*.32+gap/2,h)]:
                part(name+'-door',-w/2,w/2,front-door,front-.003,lo,hi,mats['cabinet'],.012)
                part(name+'-grip',w*.31,w*.43,front-.002,front,lo+(hi-lo)*.58,lo+(hi-lo)*.86,mats['frame'],.001)
        elif item['type']=='television':
            part('housing',-w/2,w/2,-d/2,d*.4,0,h,mats['black'],min(.003,d*.02))
            part('screen',-w*.48,w*.48,d*.4,d/2,h*.03,h*.97,mats['black'],min(.001,d*.01))
        elif 'tv' in item['type']:
            part('cabinet',-w/2,w/2,-d/2,d/2,.06,h,mats['wood'])
        else:
            part('body',-w/2,w/2,-d/2,d/2,0,h,mats['metal'] if 'refrigerator' in item['type'] else mats['cabinet'],.018)
        # Three R_y maps source +z to +x at +90deg; with Blender Y=-z,
        # this is positive R_Z (local -Y maps to +X), not negative R_Z.
        theta=math.radians(item['rotation']); c,s=math.cos(theta),math.sin(theta)
        for obj in created:
            for vertex in obj.data.vertices:
                x,y,z=vertex.co
                vertex.co=(c*x-s*y+item['x'],s*x+c*y-item['z'],z+data['levels'][f"fl{item['level']}"]+item.get('elevation',0))
    return items


def setup_lighting(settings, args):
    light=dict(settings['lighting'])
    if args.elevation is not None:
        light['elevationDeg']=args.elevation
    az,el=math.radians(light['azimuthDeg']),math.radians(light['elevationDeg'])
    direction=Vector((math.sin(az)*math.cos(el), math.cos(az)*math.cos(el), math.sin(el)))
    bpy.ops.object.light_add(type='SUN')
    sun=bpy.context.object; sun.name='Sun.manual-angle'
    sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    sun.data.energy=light['sunStrength']; sun.data.angle=math.radians(.53)
    world=bpy.data.worlds.new('Sky.manual-angle'); bpy.context.scene.world=world; world.use_nodes=True
    sky=world.node_tree.nodes.new('ShaderNodeTexSky')
    supported=sky.bl_rna.properties['sky_type'].enum_items.keys()
    sky.sky_type='MULTIPLE_SCATTERING' if 'MULTIPLE_SCATTERING' in supported else 'NISHITA'
    sky.sun_disc=False; sky.sun_elevation=el; sky.sun_rotation=math.atan2(direction.y,direction.x)
    background=world.node_tree.nodes.get('Background'); background.inputs['Strength'].default_value=light['skyStrength']
    world.node_tree.links.new(sky.outputs['Color'],background.inputs['Color'])
    return light


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--variant',default='natural')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--samples',type=int,default=128)
    parser.add_argument('--width',type=int,default=1600)
    parser.add_argument('--elevation',type=float)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.samples < 1 or args.width < 64 or (args.elevation is not None and not 0 < args.elevation <= 90):
        parser.error('samples >= 1, width >= 64 and 0 < sun elevation <= 90 are required.')
    args.output=args.output.resolve()
    if args.output.exists():
        raise RuntimeError('Choose a new output directory; existing studies are never overwritten.')
    args.output.mkdir(parents=True)
    # Drivers may fall back to cwd when their user-profile cache is unavailable.
    os.chdir(args.output)
    settings=read(ROOT/'data/visual/guest-ldk-study.json'); palette=settings['variants'][args.variant]
    data=house_builder.load_data(ROOT/'data/house.json')
    data['envelope']=read(ROOT/'generated/visual-envelope.json')
    profiles={t['type']:t for filename in ('door-catalog.json','window-catalog.json') for t in read(ROOT/'data'/filename)['types']}
    for o in data['openings']+data['interiorDoors']:
        for key in ('operation','category','archRise'):
            if key in profiles[o['type']]: o[key]=profiles[o['type']][key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats={key:material(key,value,texture='wood' if key=='wood' else 'fabric' if key=='fabric' else None)
          for key,value in palette.items() if key!='label'}
    mats.update(frame=material('Frame','38332d',.38),stone=material('Counter','e4e0d5',.32),
                metal=material('Metal','b8b8b2',.3,.7),black=material('Glass.black','15191b',.12))
    surface_details=details_for_variant(read(ROOT/'data/visual/unreal-finishes.json'),args.variant)
    for role,detail in surface_details.items():
        if detail.get('pattern'): apply_pattern(mats[role],palette[detail['paletteRole']],detail,rgb)
    ops=build_envelope(data,mats); build_openings(ops,settings,mats)
    items=build_furniture(data,settings,mats)
    decorations=build_decor(read(ROOT/'data/visual/guest-decor.json'),data,items,ops,mats,block,mesh)
    block('Ground.context-provisional',-60,70,-60,60,-.1,0,material('Ground','888276'))
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.name.startswith(('slab.','ceiling.')): assign_surface_uv(obj)
    light=setup_lighting(settings,args)
    room=next(r for r in data['rooms'] if r['id']==settings['roomId']); floor=data['levels'][f"fl{room['level']}"]
    x,z,y=settings['camera']['position']; bpy.ops.object.camera_add(location=(x,-z,y+floor))
    camera=bpy.context.object; camera.name='Camera.guest-ldk.fixed'
    tx,tz,ty=settings['camera']['target']
    camera.rotation_euler=(Vector((tx,-tz,ty+floor))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=settings['camera']['lensMm']; camera.data.clip_start=.03
    scene=bpy.context.scene; scene.camera=camera; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES'; scene.cycles.samples=args.samples; scene.cycles.use_denoising=True
    scene.cycles.max_bounces=12; scene.cycles.transmission_bounces=8; scene.cycles.transparent_max_bounces=16
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX'; prefs.get_devices()
        for device in prefs.devices: device.use=device.type=='OPTIX'
        if any(device.use for device in prefs.devices): scene.cycles.device='GPU'
    except Exception as error:
        print(f'Using CPU: {error}')
    scene.render.resolution_x=args.width; scene.render.resolution_y=round(args.width*9/16); scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=light['exposure']; scene.view_settings.gamma=1
    scene.render.image_settings.file_format='PNG'; scene.render.filepath='//interior.png'
    scene['study_status']='estimated-manual-sun-angle'; scene['site_daylight_calibrated']=False
    report=dict(status='estimated',variant=args.variant,roomId=settings['roomId'],settings=settings,lighting=light,
                decorations=decorations,furnitureIds=[i['id'] for i in items],siteDaylightCalibrated=False,unrealImportVerified=False,
                limitations=['Furniture is procedural, with approximate details; source placement retained',
                             'Window frames and per-surface shadow transmittance .9 (pane approx .81) are estimated',
                             'All actual door leaves closed; no operation animation',
                             'No neighbouring buildings or measured site orientation',
                             'Stair opening and guard walls present; stair treads still absent',
                             'Roof/gable details incomplete; source ceiling heights remain estimated',
                             'Procedural materials and glass shadow shader require UE counterparts'],
                render=dict(engine='Cycles',samples=args.samples,width=args.width,colorManagement='AgX',device=scene.cycles.device))
    (args.output/'study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'interior.blend'))
    bpy.ops.export_scene.gltf(filepath=str(args.output/'interior.glb'),export_format='GLB',export_extras=True)
    if args.render: bpy.ops.render.render(write_still=True)
    print(f'Interior study saved: {args.output}')


if __name__=='__main__':
    main()
