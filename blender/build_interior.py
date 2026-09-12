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
from stair_geometry import layout as stair_layout, walking_ramps, wall_clearances
from surface_bindings import partition_room_faces, split_wall_at, wall_cap_for_room, decompose_rectilinear, subtract_rects, intersect_rect
from electrical_assets import build_lighting_bindings, merged_item, create_fixture_mesh, ceiling_height_at
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'unreal'))
from finish_settings import details_for_variant
from furniture_assets import validate_bindings, asset_parts
from guest_decor import build as build_decor
from wall_geometry import opening_plane
from interior_geometry import ceiling_y, point_in_room, wall_polygons
from study_state import validate_state as validate_legacy_state
import multi_room_state as mrs
import circulation
from surface_finish_overrides import resolve_finish, marker_material_name
from lighting import validate_lighting_settings, effective_fixture, kelvin_to_rgb
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_registry import resolve_from as resolve_surface_registry

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


def mesh(name, vertices, faces, mat, source=None, role=None, face_materials=None):
    # face_materials (W04): {face_index: material} assigns specific faces (by
    # their position in `faces`) to an ADDITIONAL slot, on top of the default
    # `mat` in slot 0 -- used to give a wall panel's room-facing cap its own
    # surface-registry marker material without recolouring the rest of the
    # same prism (back face, thickness edges).
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces); data.update()
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if mat:
        data.materials.append(mat)
    if face_materials:
        bm.faces.ensure_lookup_table()
        slot_for = {}
        for face_index, extra_mat in face_materials.items():
            if extra_mat.name not in slot_for:
                data.materials.append(extra_mat)
                slot_for[extra_mat.name] = len(data.materials)-1
            bm.faces[face_index].material_index = slot_for[extra_mat.name]
    bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data); bpy.context.scene.collection.objects.link(obj)
    if source:
        obj['source_json'] = json.dumps(source, ensure_ascii=False)
    if role:
        obj['surface_role'] = role
    return obj


def prism(name, polygon, vector, mat, source=None, role=None, face_materials=None):
    n = len(polygon)
    vertices = polygon + [tuple(Vector(v)+Vector(vector)) for v in polygon]
    return mesh(name, vertices, [tuple(range(n-1, -1, -1)), tuple(range(n, 2*n))] +
                [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)], mat, source, role, face_materials)


def block(name, x0, x1, z0, z1, y0, y1, mat, bevel=0, source=None, face_materials=None):
    # face_materials (W04 review R5): {0: mat} for the bottom cap (at y0) or
    # {1: mat} for the top cap (at y1) -- see prism()'s own face_materials
    # note. Used to give a floor slab's walkable TOP or a ceiling slab's
    # room-facing UNDERSIDE its own surface-registry marker material without
    # recolouring the opposite face or the thin side faces.
    obj = prism(name, [(x0,-z0,y0), (x1,-z0,y0), (x1,-z1,y0), (x0,-z1,y0)],
                (0,0,y1-y0), mat, source, face_materials=face_materials)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL'); mod.width = bevel; mod.segments = 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def panel(name, wall, polygon, mat, source=None, marker=None):
    # marker (W04, dict form since W07-G1): {cap_index: material} -- cap
    # index 0 is the face at the ORIGINAL polygon position (prism()'s "cap
    # A": the smaller-at side, i.e. north for a horizontal wall / west for a
    # vertical one); 1 is the extruded "cap B" (south/east). See
    # surface_bindings.wall_cap_for_room(), which this module calls to
    # decide which one a given room is on. A SHARED wall can mark BOTH caps
    # on the same object (one registered surface per side, W07-G1); a
    # single-sided wall marks just the one cap its registration matched.
    t = wall['thickness']
    if wall['orientation'] == 'H':
        at = wall['z0']
        vertices = [(u, -at+t/2, y) for u, y in polygon]; vector = (0,-t,0)
    else:
        at = wall['x0']
        vertices = [(at-t/2, -u, y) for u, y in polygon]; vector = (t,0,0)
    return prism(name, vertices, vector, mat, source or wall, 'wall', marker)


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


class SurfaceBinder:
    """W04: tracks which surface-registry.json IDs actually got real
    geometry during this build (and with what material), so build_envelope()
    can look up "does this wall/floor/ceiling piece belong to a registered
    surface, and if so which marker material" and later write
    surface-bindings.json. Only ever sees resolved (roomId/edge exist in the
    current house.json) registrations -- build-visual-twin.py's --interior
    preflight (and refresh-visual-study.py's own step) already stop before
    Blender runs if anything is unresolved, so there is nothing to recover
    from here."""
    def __init__(self, data, resolved_surfaces, overrides, finish_document, study_variants, variant_by_room):
        # W07-G1: variant_by_room replaces the pre-G1 single base_variant --
        # each registered surface resolves its finish using ITS OWN room's
        # active variant, so switching one room's variant never touches
        # another in-scope room's (or an out-of-scope room's) surfaces
        # (spec section 3: "LDKをwarmにしても洋室の壁/床/天井...までwarmへ
        # 変わらない"). A room with no entry (should not happen for anything
        # actually registered under the current scope) falls back to
        # multi_room_state.BASE_VARIANT rather than raising, matching the
        # "対象外室/外皮は既存の基準材質を維持" contract for anything not
        # actively room-state-controlled.
        self.rooms_by_id = {r['id']: r for r in data['rooms']}
        self.by_room_kind = {}
        self.materials = {}
        self.detail = {}
        self.status = {}
        self.bound_meshes = {}
        # W07-G3 review R1: the surface REGISTRY is validated in full (all
        # entries must still resolve against the current house.json -- the
        # build-visual-twin / refresh preflight does that). But an EDITABLE
        # binding is only produced for a surface whose room is in the current
        # edit scope. A narrower scope (guest-pilot's 2 rooms) must not emit
        # bindings for room-1f-02 etc.: study.roomStates has no entry for
        # them, so import_study.py's `study['roomStates'][roomId]['variant']`
        # and study_controls would KeyError. Out-of-scope wall/floor/ceiling
        # geometry is still built by build_envelope(); with no registration
        # matched it simply keeps the plain base material (spec section 2:
        # "対象外の遮蔽形状と基準材質は残します").
        in_scope = set(variant_by_room)
        for s in resolved_surfaces:
            if s['status'] != 'resolved':
                continue
            if s['roomId'] not in in_scope:
                continue
            self.by_room_kind.setdefault((s['roomId'], s['kind']), []).append(s)
            self.status[s['id']] = dict(roomId=s['roomId'], kind=s['kind'], label=s.get('label'), state='no-surface')
            base_variant = variant_by_room.get(s['roomId'], mrs.BASE_VARIANT)
            finish = resolve_finish(finish_document, study_variants, s['kind'], base_variant, overrides.get(s['id']))
            self.detail[s['id']] = finish
            # W04 review v2 R1: give this marker the SAME base texture as the
            # whole-scene material it stands in for -- e.g. a registered
            # floor's paletteRole is 'wood' (finish-settings.json), and the
            # whole-scene floor reuses mats['wood'] (texture='wood') rather
            # than being flat, so the marker must match or a floor loses its
            # wood grain the moment it becomes a registered surface, even
            # with no override at all. Only 'wood'/'fabric' get noise here,
            # matching the mats={...texture=...} construction above.
            texture = 'wood' if finish['paletteRole'] == 'wood' else 'fabric' if finish['paletteRole'] == 'fabric' else None
            mat = material(marker_material_name(s['kind'], s['id']), finish['colorHex'], roughness=finish['roughness'], texture=texture)
            # Pattern (reference variant's tile/board detail) takes priority
            # over the plain texture above -- apply_pattern() overwrites the
            # Base Color link Blender-side, same precedence as the
            # whole-scene materials (built flat/textured first, then
            # apply_pattern() layered on afterward where a pattern exists).
            # The override's resolved colorHex is what it must modulate, not
            # the un-overridden palette colour, or an override's colour is
            # silently cancelled back out by the pattern step.
            if finish['pattern']:
                apply_pattern(mat, finish['colorHex'], finish, rgb)
            self.materials[s['id']] = mat

    def room_polygon(self, room_id): return self.rooms_by_id[room_id]['polygon']
    def wall_surfaces(self): return [s for (rid,kind),ss in self.by_room_kind.items() if kind=='wall' for s in ss]
    def floor_surfaces(self): return [s for (rid,kind),ss in self.by_room_kind.items() if kind=='floor' for s in ss]
    def ceiling_surface(self, room_id):
        matches = self.by_room_kind.get((room_id,'ceiling'),[])
        return matches[0] if matches else None

    def mark_bound(self, surface_id, obj_name, slot):
        self.status[surface_id]['state']='bound'
        self.bound_meshes.setdefault(surface_id,[]).append(dict(name=obj_name,slot=slot))

    def bindings_json(self):
        surfaces={}
        for surface_id,info in self.status.items():
            surfaces[surface_id]=dict(roomId=info['roomId'],kind=info['kind'],label=info.get('label'),
                status=info['state'],meshes=self.bound_meshes.get(surface_id,[]))
        return dict(schemaVersion='1.0.0',surfaces=surfaces)


def _room_bbox(polygon):
    return (min(p[0] for p in polygon),max(p[0] for p in polygon),min(p[1] for p in polygon),max(p[1] for p in polygon))


def _rects_overlap(a,b):
    return not (a[1]<=b[0] or a[0]>=b[1] or a[3]<=b[2] or a[2]>=b[3])


def build_envelope(data, mats, binder=None):
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
    wall_registrations = binder.wall_surfaces() if binder else []
    for w in walls:
        horizontal = w['orientation']=='H'
        at = w['z0'] if horizontal else w['x0']
        cuts = [] if 'guardHeight' in w else [o for o in ops if o['level']==w['level'] and
                o['orientation']==w['orientation'] and abs(o['at']-at)<1e-6]
        cuts += wall_clearances(w,data)
        # Registered wall surfaces on this same wall LINE (same orientation +
        # at) whose registered edge overlaps this wall entity's own span.
        # There can be up to two (a wall shared by two registered rooms); a
        # merged wall's span can also be longer than a single room's edge.
        wall_start,wall_end = (w['x0'],w['x1']) if horizontal else (w['z0'],w['z1'])
        # matches: (lo,hi,cap,s) -- cap resolved ONCE per registration here
        # (from its own overlap midpoint), not re-derived per output piece,
        # since a registration's entire range is always on the same cap.
        matches=[]
        for s in wall_registrations:
            if binder.rooms_by_id[s['roomId']]['level'] != w['level']: continue
            (ex0,ez0),(ex1,ez1) = s['edge']
            if abs(ex0-ex1)>1e-6 and abs(ez0-ez1)>1e-6: continue
            s_horizontal = abs(ez0-ez1) < 1e-6
            if s_horizontal != horizontal: continue
            s_at = ez0 if s_horizontal else ex0
            if abs(s_at-at) > 1e-6: continue
            lo,hi = sorted((ex0,ex1) if horizontal else (ez0,ez1))
            lo,hi = max(lo,wall_start),min(hi,wall_end)
            if hi-lo <= 1e-6: continue
            cap=wall_cap_for_room(at,(lo+hi)/2,horizontal,binder.room_polygon(s['roomId']))
            if cap is None:
                # Edge/room mismatch (should not happen once surface_registry
                # has resolved the edge against this same room polygon) --
                # fail safe to the plain default material rather than guessing.
                continue
            matches.append((lo,hi,cap,s))
        for i, poly in enumerate(wall_polygons(data,w,cuts)):
            if not matches:
                panel(f"wall.{w['id']}.{i}",w,poly,mats['wall'],dict(wall=w,openings=cuts))
                continue
            # W07-G1: split at the UNION of every registration's boundaries
            # FIRST, then classify each resulting piece by cap -- a SHARED
            # wall (e.g. LDK's south face and the western room's north face,
            # both registered on the SAME wall entity) must give each cap its
            # own marker on the SAME piece, never let whichever registration
            # is processed first consume the other side's range entirely
            # (the previous sequential-consume approach did exactly that).
            breakpoints={b for lo,hi,cap,s in matches for b in (lo,hi)}
            for j,piece in enumerate(split_wall_at(poly,breakpoints)):
                mid_u=sum(p[0] for p in piece)/len(piece)
                face_materials={}
                bound=[]
                for lo,hi,cap,s in matches:
                    if lo-1e-6<=mid_u<=hi+1e-6 and cap not in face_materials:
                        face_materials[cap]=binder.materials[s['id']]
                        bound.append(s['id'])
                if face_materials:
                    obj=panel(f"wall.{w['id']}.{i}.{j}",w,piece,mats['wall'],dict(wall=w,openings=cuts),marker=face_materials)
                    # W07-G1 fix: a SHARED wall piece (both caps registered)
                    # gets TWO distinct extra materials, and mesh()'s own
                    # slot_for assigns them slots 1, 2, ... in the order
                    # face_materials was populated -- the same order `bound`
                    # was appended in above. A single-cap piece still lands at
                    # slot 1. Hardcoding slot 1 for every entry here (the
                    # pre-fix bug) silently pointed BOTH sides' surface-
                    # bindings.json entries at slot 1, so one side's expected
                    # marker material never matched what was actually there.
                    for slot,surface_id in enumerate(bound,start=1):
                        binder.mark_bound(surface_id,obj.name,slot)
                else:
                    panel(f"wall.{w['id']}.{i}.{j}",w,piece,mats['wall'],dict(wall=w,openings=cuts))
    floor_registrations = binder.floor_surfaces() if binder else []
    for kind,key,offset,depth,cap in [('floor','slabs',0,-.12,0),('ceiling','flatCeilings',data['defaults']['ceilingHeight'],.025,0)]:
        for i,r in enumerate(data['envelope'][key]):
            y=data['levels'][f"fl{r['level']}"]+offset
            rect=(r['x0'],r['x1'],r['z0'],r['z1'])
            registrations={rid:ss[0] for (rid,k),ss in binder.by_room_kind.items()
                           if k==kind and binder.rooms_by_id[rid]['level']==r['level']} if binder else {}
            rooms=[binder.rooms_by_id[rid] for rid in registrations]
            for j,(poly,rid) in enumerate(partition_room_faces(rect,rooms)):
                registration=registrations.get(rid)
                fm={cap:binder.materials[registration['id']]} if registration else None
                vertices=[(x,-z,y) for x,z in poly]
                obj=prism(f"{'slab' if kind=='floor' else 'ceiling.flat'}.{i}.{j}",vertices,(0,0,depth),mats['wood'] if kind=='floor' else mats['ceiling'],face_materials=fm)
                if registration: binder.mark_bound(registration['id'],obj.name,1)
    for stair in data.get('stairs',[]):
        shape=stair_layout(stair,data['levels'])
        for i,step in enumerate(shape['steps']):
            rid='room-1f-10' if step['top']<(data['levels']['fl1']+data['levels']['fl2'])/2 else 'room-2f-02'
            registrations=binder.by_room_kind.get((rid,'floor'),[]) if binder else []
            registration=registrations[0] if registrations else None
            for j,poly in enumerate(step['polygons']):
                faces={1:binder.materials[registration['id']]} if registration else {}
                underside=None
                if binder and 'hiddenBelow' in stair:
                    hole=stair['hiddenBelow'];cx=sum(p[0] for p in poly)/len(poly);cz=sum(p[1] for p in poly)/len(poly)
                    if hole['x0']<cx<hole['x1'] and hole['z0']<cz<hole['z1']:
                        underside=binder.ceiling_surface('room-1f-21')
                        if underside:faces[0]=binder.materials[underside['id']]
                obj=prism(f"stair.{stair['id']}.{i:02}.{j}",[(x,-z,step['bottom']) for x,z in poly],
                      (0,0,step['top']-step['bottom']),mats['wood'],stair,'stairs',faces or None)
                if registration: binder.mark_bound(registration['id'],obj.name,1)
                if underside:binder.mark_bound(underside['id'],obj.name,2 if registration else 1)
    for stair in data.get('stairs',[]):
        for i,(vertices,faces) in enumerate(walking_ramps(stair,data['levels'])):
            obj=mesh(f"stair_collision.{stair['id']}.{i}",[(x,-z,y) for x,z,y in vertices],faces,mats['wood'],stair)
            obj.hide_render=True
            obj['walkthrough_collision_only']=True
    pieces = data['envelope']['slopedCeilingPieces']
    for i,p in enumerate(pieces):
        if not p['sloped']:
            continue
        ceiling_surface = binder.ceiling_surface(p['roomId']) if binder else None
        y0,y1 = ceiling_y(data,p,p['z0']),ceiling_y(data,p,p['z1'])
        # W04 review R5: only the room-facing face (cap 0 -- the polygon as
        # given, before the .025m extrusion into the roof-side topside) gets
        # the marker material; the base `mat` (plain ceiling) covers the
        # topside and thin edge faces.
        face_materials = {0: binder.materials[ceiling_surface['id']]} if ceiling_surface else None
        obj=prism(f"ceiling.{p['roomId']}.{i}",[(p['x0'],-p['z0'],y0),(p['x1'],-p['z0'],y0),
              (p['x1'],-p['z1'],y1),(p['x0'],-p['z1'],y1)],(0,0,.025),mats['ceiling'],p,'ceiling',face_materials)
        if ceiling_surface: binder.mark_bound(ceiling_surface['id'],obj.name,1)
        for flat in pieces:
            if flat['sloped'] or flat['roomId'] != p['roomId']:
                continue
            for at in (p['x0'],p['x1']):
                if min(abs(at-flat['x0']),abs(at-flat['x1'])) > 1e-6:
                    continue
                a,b = max(p['z0'],flat['z0']),min(p['z1'],flat['z1'])
                if b-a > 1e-6:
                    low = data['levels']['fl1']+data['defaults']['ceilingHeight']
                    # W04 review R5: the riser (the short vertical step where
                    # the slope height jumps) is explicitly out of scope for
                    # per-surface finishing -- always the plain ceiling
                    # material, never marked bound.
                    panel(f"ceiling.riser.{i}.{at}",dict(orientation='V',x0=at,thickness=.04),
                          [(a,low),(b,low),(b,ceiling_y(data,p,b)),(a,ceiling_y(data,p,a))],mats['ceiling'],p)
    # Retain the rest of the building as sun occluders.
    roof_coll = house_builder.collection('Roofs')
    fps = {f['id']:f for f in data['footprints']}
    for roof in data['roofs']:
        house_builder.build_roof(data,roof,fps[roof['footprintId']],roof_coll,mats['frame'])
    return ops


def _hinge_blender_xy(orientation, wall_at, hinge_source_xz, thickness):
    """The Blender-space (X, Y) a swing leaf's OWN object origin must sit at
    for a hinge at source (x, z) `hinge_source_xz` to be correct -- same
    (u, at, thickness) -> (X, Y) convention panel() itself uses for this
    wall orientation, so a leaf recentred here rotates exactly where the
    door frame built by the SAME rect()/panel() call actually is."""
    hinge_x, hinge_z = hinge_source_xz
    if orientation == 'H':
        return (hinge_x, -wall_at + thickness / 2)
    return (wall_at - thickness / 2, -hinge_z)


def _recenter_object(obj, pivot_xy):
    """Shift every vertex by -pivot (world space unchanged) and move the
    object's own origin to pivot -- so a later SetActorRotation() in UE
    (which always rotates about the actor's own origin) swings the leaf
    around `pivot_xy`, not around the world origin every other object in
    this pipeline is built directly in (see build_furniture()/panel()'s own
    'vertices already in world space, object origin at (0,0,0)' convention;
    a movable, rotatable leaf is the one kind of object here that needs its
    own real pivot)."""
    px, py = pivot_xy
    for v in obj.data.vertices:
        v.co.x -= px; v.co.y -= py
    obj.location.x += px; obj.location.y += py


def build_openings(ops, settings, mats, door_connections_by_id=None, door_states=None):
    # W07-G2: `door_connections_by_id` (circulation.resolve_connections()'s
    # output, keyed by door id) names exactly the doors the ACTIVE walkthrough
    # profile actually walks through -- every other opening (windows, and any
    # door outside today's profile) keeps the pre-G2 flat, non-movable
    # closed-leaf placeholder unchanged. `door_states` (the given --state's
    # own doorStates, or {} for none/default) decides each in-profile leaf's
    # INITIAL baked pose (review R1) -- see the is_open comment below.
    door_connections_by_id = door_connections_by_id or {}
    door_states = door_states or {}
    door_bindings = {}
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
            # W07-G2: a frameless 'open' door in the active profile is still
            # a real connection (always passable, no leaf) -- recorded so
            # resolve_door_overrides() can name it precisely ("no leaf")
            # rather than "unknown id" if a state ever names it in
            # doorStates. 'open-arch' (a window-like arched opening) never
            # matches a circulation.py connection (unsupported operation),
            # so it never reaches here regardless.
            connection=door_connections_by_id.get(o['id'])
            if connection is not None:
                door_bindings[o['id']]=dict(level=connection['level'],roomIds=connection['roomIds'],
                    operation=connection['operation'],openable=False,leaves=[])
            continue
        w=dict(orientation=o['orientation'], x0=o['at'], z0=o['at'], thickness=cfg['frameDepth'])
        a,b,low,high=o['start'],o['end'],o['bottom'],o['top']
        def rect(suffix,x0,x1,y0,y1,mat,thickness=None):
            return panel(f"opening.{o['id']}.{suffix}",dict(w,thickness=thickness or w['thickness']),
                         [(x0,y0),(x1,y0),(x1,y1),(x0,y1)],mat,o)
        frame_parts=[('left',a,a+fw,low,high),('right',b-fw,b,low,high),('head',a+fw,b-fw,high-fw,high)]
        # W07-G2: openings()'s own interiorDoors branch sets bottom=base (the
        # LEVEL's own absolute floor height, e.g. 0.707m for level 1 here) --
        # not base+sill like the exterior-openings branch -- so every
        # interior door's own sill catalog value is never actually applied to
        # its geometry; `low` is exactly floor level for EVERY interior door,
        # unconditionally (an absolute-vs-relative mismatch first found by
        # comparing catalog sill=0 against the actual `low` value here, which
        # is NOT near 0 in world space -- checking o['exterior'] instead of a
        # numeric threshold on `low` is what actually distinguishes this).
        # A floor-level 'sill' trim piece is therefore a full-width,
        # frameWidth-tall (4.5cm) solid strip sitting right across the
        # doorway's own walkable centre, for every interior door. That never
        # mattered while the native walkthrough was single-room (G1: nobody
        # ever needed to actually cross a door's own threshold) -- G2's real
        # room-to-room walking discovered it as real blocking collision,
        # exceeding AWalkthroughCharacter's MaxStepHeight (2cm unchanged
        # since G1), regardless of open/closed leaf state (this frame piece
        # is not part of the movable leaf at all). An exterior opening's own
        # sill IS applied (base+o['sill']) and stays elevated above where
        # anyone walks for every window in this house (sill>0); its trim
        # piece is unaffected.
        if o['exterior']:
            frame_parts.append(('sill',a+fw,b-fw,low,low+fw))
        for suffix,x0,x1,y0,y1 in frame_parts:
            rect(suffix,x0,x1,y0,y1,mats['frame'])
        if o['category']=='window':
            rect('glass',a+fw,b-fw,low+fw,high-fw,glass,cfg['glassThickness'])
            if o['operation']=='openable':
                mid=(a+b)/2
                rect('mullion',mid-fw/2,mid+fw/2,low+fw,high-fw,mats['frame'])
            continue
        connection = door_connections_by_id.get(o['id'])
        if connection is None:
            # Unchanged pre-G2 behaviour: a single flat, non-movable panel
            # standing in for a closed leaf -- correct for a door outside
            # today's walkthrough profile, which nobody walks up to.
            rect('closed-leaf',a+fw,b-fw,low+.005,high-fw,mats['cabinet'],.035)
            continue
        # W07-G2: this door IS part of the active walkthrough profile -- build
        # a real, independently-movable leaf (or two, for double-swing) with
        # a proper hinge pivot for swing, and record door-bindings.json so UE
        # knows which actor(s) to move and by how much when the door toggles.
        #
        # W07-G2 review R1: the leaf's INITIAL pose (this generation's own
        # render, and what UE actually imports) must match the given state's
        # doorStates -- previously every leaf always started closed here
        # regardless of doorStates, so a saved "door open" condition showed
        # closed in both this preview render and the freshly-imported UE
        # level until something else moved it later. `is_open` below is
        # applied to the object's own transform (on top of the always-closed
        # geometry `rect()`/`_recenter_object()` already build), and recorded
        # per leaf as `bakedOpen` so every later consumer (UE's initial
        # import, and the native walkthrough's own lazy closed-baseline
        # capture for a slide leaf) can recover the TRUE closed baseline
        # regardless of whichever doorStates is active when it first looks.
        #
        # Blender-space axis convention (same as _hinge_blender_xy()/panel()
        # above): Blender X = source x unchanged; Blender Y = -(source z).
        # circulation.py's angles/offsets are all source/UE-space, so a
        # rotation must be NEGATED for Blender's own Y-flipped axes, and a
        # slide offset's z-component must be negated the same way (its
        # x-component is not).
        is_open=circulation.effective_door_open(o['id'],door_states)
        leaves=[]
        if connection['operation'] in ('fold','double-fold'):
            # Each pair folds about its jamb; the outer panel follows the
            # meeting hinge with a translation plus opposite rotation.
            pairs=[(a,b,connection.get('hingeSide') or 'L')]
            if connection['operation']=='double-fold': pairs=[(a,(a+b)/2,'L'),((a+b)/2,b,'R')]
            for pair_index,(pl,ph,side) in enumerate(pairs):
                sign=1 if side=='L' else -1
                jamb=pl+fw if side=='L' else ph-fw
                length=(ph-pl-fw)/2
                hinge=(jamb,o['at']) if o['orientation']=='H' else (o['at'],jamb)
                delta=circulation._swing_delta_deg(dict(connection,hingeSide=side,maxSwingDeltaDeg=80))
                for panel_index in range(2):
                    start=jamb+sign*length*panel_index; end=start+sign*length
                    obj=rect(f'fold-{pair_index}-{panel_index}',min(start,end),max(start,end),low+.005,high-fw,mats['cabinet'],.025)
                    pivot=(start,o['at']) if o['orientation']=='H' else (o['at'],start)
                    _recenter_object(obj,_hinge_blender_xy(o['orientation'],o['at'],pivot,w['thickness']))
                    yaw=delta if panel_index==0 else -delta
                    leaf=dict(actor=obj.name,kind='fold',openYawDeltaDeg=yaw,bakedOpen=is_open)
                    if panel_index:
                        angle=math.radians(delta); vx,vz=(sign*length,0) if o['orientation']=='H' else (0,sign*length)
                        dx=vx*math.cos(angle)-vz*math.sin(angle)-vx
                        dz=vx*math.sin(angle)+vz*math.cos(angle)-vz
                        leaf['openOffsetCm']=[dx*100,dz*100,0]
                        if is_open: obj.location.x+=dx; obj.location.y-=dz
                    if is_open: obj.rotation_euler[2]=math.radians(-yaw)
                    leaves.append(leaf)
        elif connection['operation']=='double-swing':
            mid=(a+b)/2
            spans=dict(left=(a,mid),right=(mid,b))
            for hinge_xz,delta_deg,kind in circulation.double_swing_hinges_and_deltas(connection):
                lo_u,hi_u=spans[kind]
                x0=lo_u+(fw if kind=='left' else 0); x1=hi_u-(fw if kind=='right' else 0)
                obj=rect(f'leaf-{kind}',x0,x1,low+.005,high-fw,mats['cabinet'],.035)
                _recenter_object(obj,_hinge_blender_xy(o['orientation'],o['at'],hinge_xz,w['thickness']))
                if is_open: obj.rotation_euler[2]=math.radians(-delta_deg)
                leaves.append(dict(actor=obj.name,kind=kind,openYawDeltaDeg=delta_deg,bakedOpen=is_open))
        elif connection['operation']=='swing':
            hinge_xz,delta_deg=circulation.swing_hinge_and_delta(connection,None)
            obj=rect('leaf',a+fw,b-fw,low+.005,high-fw,mats['cabinet'],.035)
            _recenter_object(obj,_hinge_blender_xy(o['orientation'],o['at'],hinge_xz,w['thickness']))
            if is_open: obj.rotation_euler[2]=math.radians(-delta_deg)
            leaves.append(dict(actor=obj.name,kind='single',openYawDeltaDeg=delta_deg,bakedOpen=is_open))
        elif connection['operation']=='slide':
            obj=rect('leaf',a+fw,b-fw,low+.005,high-fw,mats['cabinet'],.035)
            # A pure translation needs no pivot change -- the object's
            # existing world-space origin is fine either way.
            #
            # W07-G2 review R3: model this as an OUTSET sliding door
            # (アウトセット引き戸) -- the leaf sits on ONE FACE of its wall,
            # both closed and (slid aside) open -- rather than a pocket door
            # whose open leaf embeds in a wall cavity that is not modelled.
            # The perpendicular outset (toward the +wall-normal side: +source
            # z for an H wall, +source x for a V wall) is baked into the
            # leaf's CLOSED placement here, so `openOffsetCm` stays a pure
            # along-wall translation and every consumer (UE import, native
            # walkthrough) captures the already-outset closed baseline
            # automatically. Closed, the leaf still spans the doorway (a few
            # cm off its centre plane), so it still blocks passage.
            outset=w['thickness']/2+.035/2+.01
            if o['orientation']=='H': obj.location.y-=outset   # Blender Y = -(source z): -Y is +source z
            else: obj.location.x+=outset                       # Blender X = source x
            dx,dz=circulation.slide_open_offset(connection)
            if is_open: obj.location.x+=dx; obj.location.y+=-dz
            leaves.append(dict(actor=obj.name,kind='single',openOffsetCm=[dx*100,dz*100,0],bakedOpen=is_open))
        else:
            raise ValueError(f"Unsupported openable door operation: {connection['operation']!r} ({o['id']})")
        door_bindings[o['id']]=dict(level=connection['level'],roomIds=connection['roomIds'],
            operation=connection['operation'],openable=True,leaves=leaves)
    return door_bindings


def build_furniture(data,room_ids,mats_by_room):
    # W07-G1: only items belonging to an IN-SCOPE room are generated at all
    # (spec section 3: "家具は対象roomIdsに属する既存配置を生成します") --
    # room reference (item['room']) and actual coordinates must agree; a
    # mismatch is named and stopped rather than silently trusting the
    # coordinates to move the item into a different (possibly out-of-scope)
    # room, or generating it twice.
    catalog={t['type']:t for t in read(ROOT/'data/furniture-catalog.json')['types']}
    bindings=validate_bindings(read(ROOT/'data/visual/asset-bindings.json'),
        read(ROOT/'data/furniture.json')['items'],read(ROOT/'data/furniture-catalog.json'))
    rooms_by_id={r['id']:r for r in data['rooms']}
    items=[]
    for i in read(ROOT/'data/furniture.json')['items']:
        if i['room'] not in room_ids:
            continue
        room=rooms_by_id.get(i['room'])
        if room is None or i['level']!=room['level'] or not point_in_room(i['x'],i['z'],room['polygon']):
            raise ValueError(f"furniture.json: {i['id']} claims room {i['room']!r} but its coordinates "
                "do not actually fall inside that room's current polygon/level.")
        items.append(i)
    role_bindings={}
    for item in items:
        # W07-G1 review R5: each item's OWN room's materials set -- every
        # `mats[...]` reference below now resolves against that room's
        # actual variant instead of always the fixed baseline, so Blender's
        # own preview render agrees with UE's per-room role material
        # application instead of only LDK's variant ever showing correctly.
        mats=mats_by_room[item['room']]
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
        native_asset={'raisedPlatform':'raised-platform-v1','mattress':'mattress-v1',
                      'sofaWorkTable':'sofa-work-table-v1','roundTable':'round-table-v1','timberChair':'chair-timber-v1',
                      'rangeHood':'range-hood-v1','faucet':'faucet-v1','airConditioner':'air-conditioner-v1'}.get(shape)
        if binding or native_asset:
            binding=binding or dict(furnitureId=item['id'],assetId=native_asset,sizing='parametric',
                                    status='estimated',note='Default renderer for catalog shape; no explicit override.')
            for spec in asset_parts(binding['assetId'],w,d,h):
                kind=spec.get('kind','box')
                if kind!='box':
                    x0,x1,z0,z1,y0,y1=spec['bounds']
                    if kind=='disc':
                        # W07-G3 review R3: a circle standing in the VERTICAL
                        # x/height plane, thin along depth -- for a front-load
                        # washer door the round opening actually reads as
                        # round from the front (the plan-plane 'ellipse' made
                        # a thin sliver extruded upward instead). Ring in
                        # (x, height) at the near depth face, extruded through
                        # the depth span z0->z1.
                        cx,cy=(x0+x1)/2,(y0+y1)/2; rx,ry=(x1-x0)/2,(y1-y0)/2
                        ring=[(cx+rx*math.cos(j*2*math.pi/64),cy+ry*math.sin(j*2*math.pi/64)) for j in range(64)]
                        obj=prism(f"furniture.{item['id']}.{spec['name']}",[(px,-z0,py) for px,py in ring],
                                  (0,-(z1-z0),0),mats[spec['material']],item)
                    else:
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
            # W07-G1: this object's whole-scene role-slot material must
            # follow ITS OWN room's active variant, never a single global
            # one -- both here (review R5: `mats` above is now this item's
            # own room's materials set, not always the fixed baseline) and
            # in UE's apply_state(), once per room.
            role_bindings[obj.name]=item['room']
    return items,role_bindings


def build_electrical_lighting(data, room_ids, room_states, mats):
    """W06/W07-G1: resolve every fixture in `room_ids` into
    lighting-bindings.json (the same artifact UE's import_study.py reads to
    spawn its own actors/lights -- resolved ONCE, here, for the whole scope,
    and reused by both -- W06 spec section 1; W07-G1 spec section 3: one
    shared resolution per scope, not one per room), build a simple
    placeholder mesh per fixture, and add a real Blender lamp per fixture
    reflecting its OWN room's fixtures overrides (room_states[fixture
    roomId].fixtures; on/off is independent of day/night mode, unchanged
    from W06) so a --state render actually shows the requested condition,
    not just UE's."""
    electrical = read(ROOT/'data/electrical.json')
    catalog = read(ROOT/'data/electrical-catalog.json')
    lighting_settings = validate_lighting_settings(read(ROOT/'data/visual/lighting-settings.json'))
    bindings = build_lighting_bindings(data, electrical, catalog, lighting_settings, room_ids)
    catalog_by_type = {t['type']: t for t in catalog['types']}
    items_by_id = {i['id']: i for i in electrical['items']}
    for binding in bindings['fixtures']:
        item = items_by_id[binding['id']]
        merged = merged_item(item, catalog_by_type)
        # W06-v1 review R2: the rod (if any) spans from the ACTUAL ceiling
        # surface (pre-mountHeight) down to the housing's top -- only
        # meaningful for a ceiling mount.
        ceiling_height = (ceiling_height_at(data, merged['x'], merged['z'], merged['room'])
            if merged['mount'] == 'ceiling' else None)
        create_fixture_mesh(binding, merged, mats, block, item, ceiling_height)
        fixture_overrides = room_states.get(binding['roomId'], {}).get('fixtures', {})
        effective = effective_fixture(binding, fixture_overrides.get(binding['id']))
        light_type = 'SPOT' if binding['source'] == 'spot' else 'POINT'
        # W06-v1 review R2: the light itself sits at emitPositionM (the
        # housing's underside), not positionM (the mount origin/top) -- never
        # inside the ceiling void or the fixture's own opaque body.
        x, y, z = binding['emitPositionM']
        bpy.ops.object.light_add(type=light_type, location=(x, -z, y))
        lamp = bpy.context.object
        lamp.name = f"Light.{binding['id']}"
        # W06: documented approximation, not a photometric match -- Blender's
        # POINT/SPOT light `energy` is radiant watts, not lumens. Using the
        # commonly-cited 683 lm/W peak luminous-efficacy constant to convert
        # is a simplification (assumes a monochromatic 555nm source); this
        # project does not require Blender/UE pixel-for-pixel agreement (W05/
        # W06 precedent), only a documented, consistent conversion.
        lamp.data.energy = effective['effectiveLumens'] / 683
        lamp.data.color = kelvin_to_rgb(effective['temperatureK'])
        if light_type == 'SPOT':
            lamp.data.spot_size = math.radians(binding['spotAngleDeg'])
        dx, dy, dz = binding['directionVector']
        # W06-v1 review R2: `direction` here is already the ray-TRAVEL
        # direction (e.g. straight down for a ceiling fixture) -- unlike
        # setup_lighting()'s sun vector (which points TOWARD the sun and is
        # negated before to_track_quat()), this must NOT be negated, or the
        # lamp's local -Z (its own shine axis) ends up pointing the opposite
        # way (e.g. a downlight aimed up into the ceiling instead of down).
        direction = Vector((dx, -dz, dy))
        lamp.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return bindings


def setup_lighting(settings, args, state=None):
    light=dict(settings['lighting'])
    # W05: state.azimuthDeg/elevationDeg (already plan-relative, same
    # convention as settings['lighting']) take priority over --elevation,
    # matching the existing state.variant-over---variant precedence -- a
    # date/time comparison's saved azimuth was previously dropped here
    # entirely (only --elevation and only elevation, never azimuth, were
    # ever applied), so a Blender render from --state showed the DEFAULT
    # angle instead of that state's actual sun position.
    if state is not None:
        light['azimuthDeg']=state['azimuthDeg']
        light['elevationDeg']=state['elevationDeg']
    elif args.elevation is not None:
        light['elevationDeg']=args.elevation
    az,el=math.radians(light['azimuthDeg']),math.radians(light['elevationDeg'])
    direction=Vector((math.sin(az)*math.cos(el), math.cos(az)*math.cos(el), math.sin(el)))
    # W06-v1 review R3: night must actually disable the sun/sky here too, not
    # just record lighting.mode in study.json -- previously this always used
    # the plain day sunStrength/skyStrength regardless of state['lighting'],
    # so a "night" --state render still showed full daylight in Blender. day
    # (or no lighting state at all) keeps the existing behaviour unchanged.
    is_night = state is not None and state.get('lighting', {}).get('mode') == 'night'
    bpy.ops.object.light_add(type='SUN')
    sun=bpy.context.object; sun.name='Sun.manual-angle'
    sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    sun.data.energy=0 if is_night else light['sunStrength']; sun.data.angle=math.radians(.53)
    world=bpy.data.worlds.new('Sky.manual-angle'); bpy.context.scene.world=world; world.use_nodes=True
    sky=world.node_tree.nodes.new('ShaderNodeTexSky')
    supported=sky.bl_rna.properties['sky_type'].enum_items.keys()
    sky.sky_type='MULTIPLE_SCATTERING' if 'MULTIPLE_SCATTERING' in supported else 'NISHITA'
    sky.sun_disc=False; sky.sun_elevation=el; sky.sun_rotation=math.atan2(direction.y,direction.x)
    background=world.node_tree.nodes.get('Background')
    background.inputs['Strength'].default_value=0 if is_night else light['skyStrength']
    world.node_tree.links.new(sky.outputs['Color'],background.inputs['Color'])
    return light


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--scope',help='data/visual/study-scopes.json scopeId. Defaults to --state\'s own '
        'scopeId, or "guest-ldk" (single-room, pre-W07 compatible) if neither is given.')
    parser.add_argument('--variant',default='natural',help='Uniform initial variant for every room in scope '
        'when --state is omitted; overridden per-room by --state.roomStates[*].variant.')
    parser.add_argument('--state',type=Path,help='Validated study-state.json/scenario state (schemaVersion '
        '1.0.0-2.0.0; anything older than 2.0.0 is migrated in-memory to a single-room 2.0.0 state -- see '
        'unreal/multi_room_state.py). Carries per-room surfaceOverrides/fixtures and sets the sun to '
        "state's azimuthDeg/elevationDeg (overriding --elevation). Omit for the plain default (no overrides).")
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--samples',type=int,default=128)
    parser.add_argument('--width',type=int,default=1600)
    parser.add_argument('--elevation',type=float)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.samples < 1 or args.width < 64 or (args.elevation is not None and not 0 < args.elevation <= 90):
        parser.error('samples >= 1, width >= 64 and 0 < sun elevation <= 90 are required.')
    args.output=args.output.resolve()
    if args.state: args.state=args.state.resolve()  # before chdir below, or a relative --state cannot be found
    if args.output.exists():
        raise RuntimeError('Choose a new output directory; existing studies are never overwritten.')
    args.output.mkdir(parents=True)
    # Drivers may fall back to cwd when their user-profile cache is unavailable.
    os.chdir(args.output)
    legacy_study=read(ROOT/'data/visual/guest-ldk-study.json')
    scopes_document=mrs.validate_scopes(read(ROOT/'data/visual/study-scopes.json'))
    room_render_settings=mrs.validate_room_render_settings(read(ROOT/'data/visual/room-render-settings.json'))
    variants=legacy_study['variants']
    raw_state=json.loads(args.state.read_text(encoding='utf-8')) if args.state else None
    scope_id=args.scope or (raw_state or {}).get('scopeId') or 'guest-ldk'
    scope=mrs.resolve_scope(scopes_document,scope_id)
    room_ids=scope['roomIds']
    state=mrs.validate_state(raw_state,room_ids,variants,scopes_document,legacy_study) if raw_state is not None else None
    if state is not None:
        # build_interior.py's OWN contract is "a --state must already cover
        # the FULL resolved scope, or none at all" -- merging a state that
        # only covers a SUBSET of the scope with a previous generation's
        # state (W07-G1 spec section 2: "不足室の基準状態が必要...不足室を
        # 明示して停止") is the ORCHESTRATION layer's job (refresh_inputs.py/
        # refresh-visual-study.py/study_controls.py's mrs.partial_apply()),
        # not this low-level generator's -- a state reaching here incomplete
        # is a caller error, reported plainly rather than crashing on a
        # missing roomStates key below.
        missing=[room_id for room_id in room_ids if room_id not in state['roomStates']]
        if missing:
            raise RuntimeError('--state is missing roomStates for room(s) in scope '+scope_id+': '+', '.join(missing))
    room_states=(state['roomStates'] if state else
        {room_id:dict(variant=args.variant,surfaceOverrides={},fixtures={}) for room_id in room_ids})
    variant_by_room={room_id:room_states[room_id]['variant'] for room_id in room_ids}
    overrides={surface_id:override for room_id in room_ids for surface_id,override in room_states[room_id]['surfaceOverrides'].items()}
    active_room_id=state['activeRoomId'] if state else scope['defaultRoomId']
    data=house_builder.load_data(ROOT/'data/house.json')
    data['envelope']=read(ROOT/'generated/visual-envelope.json')
    profiles={t['type']:t for filename in ('door-catalog.json','window-catalog.json') for t in read(ROOT/'data'/filename)['types']}
    for o in data['openings']+data['interiorDoors']:
        for key in ('operation','category','archRise'):
            if key in profiles[o['type']]: o[key]=profiles[o['type']][key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # W07-G1: the ENVELOPE's own base materials (mats['wall'] etc.) use the
    # fixed baseline variant, never a per-room one -- every in-scope room's
    # OWN registered wall/floor/ceiling pieces get their own marker material
    # (SurfaceBinder, per-room) regardless, so this only shows through on
    # genuinely un-owned geometry (exterior walls/roof, thin unmarked wall
    # side faces, out-of-scope rooms) -- spec section 3: "対象外室/外皮は
    # 既存の基準材質を維持". Furniture/decor are NOT envelope -- they are
    # exactly the role-owned geometry role-bindings.json exists to let UE
    # switch per room, so Blender's own preview render must build one
    # materials set PER ROOM VARIANT and let build_furniture()/build_decor()
    # pick each item's own room's set, instead of (review R5's finding) every
    # room's furniture always using the fixed baseline regardless of that
    # room's actual variant -- UE and Blender then agree again.
    finish_document=read(ROOT/'data/visual/unreal-finishes.json')
    # frame/stone/metal/black are fixed hex colours, not driven by any
    # variant's palette (review R5: "固定色の金属等...変更する必要はない") --
    # built once and shared across every room's materials set.
    extras=dict(frame=material('Frame','38332d',.38),stone=material('Counter','e4e0d5',.32),
                metal=material('Metal','b8b8b2',.3,.7),black=material('Glass.black','15191b',.12))
    def build_palette_materials(variant):
        palette=variants[variant]
        # W07-G1 review v2 fix: UE's Interchange import sanitizes '.' out of
        # imported material names (confirmed via a real import: Blender's
        # own 'natural.wall' comes back as 'natural_wall' when queried via
        # mat.get_name() in import_study.py) -- '_' survives the round trip
        # unchanged, so the separator must be '_', matching the UE-side
        # library's own M_{variant}_{role} naming convention.
        result={key:material(f'{variant}_{key}',value,texture='wood' if key=='wood' else 'fabric' if key=='fabric' else None)
                for key,value in palette.items() if key!='label'}
        surface_details=details_for_variant(finish_document,variant)
        for role,detail in surface_details.items():
            if detail.get('pattern'): apply_pattern(result[role],palette[detail['paletteRole']],detail,rgb)
        result.update(extras)
        return result
    mats_by_variant={mrs.BASE_VARIANT:build_palette_materials(mrs.BASE_VARIANT)}
    def mats_for_variant(variant):
        if variant not in mats_by_variant: mats_by_variant[variant]=build_palette_materials(variant)
        return mats_by_variant[variant]
    mats=mats_by_variant[mrs.BASE_VARIANT]  # the envelope's own fixed baseline set, unchanged usage below
    mats_by_room={room_id:mats_for_variant(variant_by_room[room_id]) for room_id in room_ids}
    # W04: registered surface IDs -> real wall/floor/ceiling geometry. Every
    # override key here must resolve to real bound geometry; anything else
    # stops the build rather than silently dropping the override. The
    # surface-registry preflight (build-visual-twin.py --interior, and
    # refresh-visual-study.py's own step) already guarantee every REGISTERED
    # id here is resolved against the current house.json -- an override
    # naming something outside that resolved set at all is a plain unknown id.
    resolved=resolve_surface_registry(ROOT)
    binder=SurfaceBinder(data,resolved['surfaces'],overrides,finish_document,variants,variant_by_room)
    unknown=[surface_id for surface_id in overrides if surface_id not in binder.materials]
    if unknown:
        raise RuntimeError('surfaceOverrides references unknown surface id(s): '+', '.join(unknown))
    # W07-G2: the walkthrough profile for THIS scope decides which doors get
    # real, independently-movable leaves (spec section 1: profiles live in
    # their own file, separate from the edit scope). rooms outside the
    # profile (and every door touching them) keep the pre-G2 flat closed-leaf
    # placeholder -- correct, since generation for a narrower scope must
    # never require a wider one's rooms to already be modelled.
    walkthrough_profiles=circulation.validate_profiles(read(ROOT/'data/visual/walkthrough-profiles.json'))
    walk_profile=circulation.resolve_profile_for_scope(walkthrough_profiles,scope_id)
    rooms_by_id={r['id']:r for r in data['rooms']}
    door_catalog_by_type={t['type']:t for t in read(ROOT/'data/door-catalog.json')['types']}
    connections=circulation.resolve_connections(rooms_by_id,data['interiorDoors'],door_catalog_by_type,walk_profile['roomIds'])
    door_connections_by_id={c['id']:c for c in connections}
    # W07-G2 review R1: the SAME doorStates given to this generation (default
    # {} = every door closed, matching mrs.default_state_v2()'s own "every
    # profile door starts closed" contract) decides each leaf's initial baked
    # pose -- not always closed regardless of --state, as before.
    door_states=state['doorStates'] if state else {}
    ops=build_envelope(data,mats,binder); door_bindings=build_openings(ops,legacy_study,mats,door_connections_by_id,door_states)
    circulation.validate_door_bindings(dict(schemaVersion=circulation.DOOR_BINDINGS_SCHEMA,doors=door_bindings))
    (args.output/'door-bindings.json').write_text(
        json.dumps(dict(schemaVersion=circulation.DOOR_BINDINGS_SCHEMA,doors=door_bindings),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    no_surface=[surface_id for surface_id in overrides if binder.status[surface_id]['state']!='bound']
    if no_surface:
        raise RuntimeError('surfaceOverrides references no-surface id(s) (no matching geometry found): '+', '.join(no_surface))
    (args.output/'surface-bindings.json').write_text(json.dumps(binder.bindings_json(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    items,role_bindings=build_furniture(data,room_ids,mats_by_room)
    # guest-decor.json is fixed to room-1f-06 (LDK) by its own roomId field
    # (see the role_bindings loop below) -- its own room's materials set,
    # same as any other LDK furniture (review R5).
    decor_document=read(ROOT/'data/visual/guest-decor.json')
    decorations=build_decor(decor_document,data,items,ops,mats_by_room[decor_document['roomId']],block,mesh,read(ROOT/'data/furniture-catalog.json')) if decor_document['roomId'] in room_ids else []
    # guest-decor.json is fixed to room-1f-06 (LDK) by its own roomId field
    # (unchanged by W07-G1: "新しい小物・画像相当の装飾は不要" for the
    # western room) -- every decoration object it just created belongs there.
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('decoration.'): role_bindings[obj.name]='room-1f-06'
    block('Ground.context-provisional',-60,70,-60,60,-.1,0,material('Ground','888276'))
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.name.startswith(('slab.','ceiling.')): assign_surface_uv(obj)
    lighting_mode=state['lighting']['mode'] if state else 'day'
    light=setup_lighting(legacy_study,args,state)
    lighting_bindings=build_electrical_lighting(data,room_ids,room_states,mats)
    (args.output/'lighting-bindings.json').write_text(json.dumps(lighting_bindings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output/'role-bindings.json').write_text(json.dumps(
        dict(schemaVersion='1.0.0',actors=role_bindings),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    active_render=mrs.room_render(room_render_settings,active_room_id,legacy_study)
    room=next(r for r in data['rooms'] if r['id']==active_room_id); floor=data['levels'][f"fl{room['level']}"]
    x,z,y=active_render['camera']['position']; bpy.ops.object.camera_add(location=(x,-z,y+floor))
    camera=bpy.context.object; camera.name='Camera.guest-ldk.fixed'
    tx,tz,ty=active_render['camera']['target']
    camera.rotation_euler=(Vector((tx,-tz,ty+floor))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=active_render['camera']['lensMm']; camera.data.clip_start=.03
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
    # W07-G2: walkableRoomId (a single fixed room id) predates multi-room
    # circulation and is no longer read anywhere (scripts/enable-unreal-
    # walkthrough.py resolves the walkthrough profile from scopeId via
    # circulation.resolve_profile_for_scope() instead) -- dropped rather than
    # left behind naming a stale single room.
    report=dict(status='estimated',schemaVersion='2.0.0',scopeId=scope['scopeId'],roomIds=room_ids,
                activeRoomId=active_room_id,roomStates=room_states,
                # W07-G2 review R1: recorded here (study.json is this
                # generation's own persistent record, same role roomStates
                # already plays) so import_study.py can independently apply
                # the SAME doorStates to each leaf's actual UE transform,
                # regardless of whether --state was a file or the internal
                # default -- not just trust that Blender's own bake (above)
                # survived the GLB export/Interchange import unchanged.
                doorStates=door_states,
                settings=dict(variants=legacy_study['variants'],lighting=legacy_study['lighting'],window=legacy_study['window'],
                              note=legacy_study['note']),
                lighting=light,decorations=decorations,furnitureIds=[i['id'] for i in items],
                siteDaylightCalibrated=False,unrealImportVerified=False,
                electricalLighting=dict(mode=lighting_mode,fixtureIds=[f['id'] for f in lighting_bindings['fixtures']]),
                limitations=['Furniture is procedural, with approximate details; source placement retained',
                             'Window frames and per-surface shadow transmittance .9 (pane approx .81) are estimated',
                             'No neighbouring buildings or measured site orientation',
                             'Canonical stair treads and guard walls; estimated dimensions retained',
                             'Roof/gable details incomplete; source ceiling heights remain estimated',
                             'Procedural materials and glass shadow shader require UE counterparts',
                             'Electrical fixture geometry is a simple placeholder; lumens/colour temperature are estimated profiles, not measured photometry (see data/visual/lighting-settings.json)',
                             'Guest circulation (W07-G2) supports swing/double-swing/slide/open doors across the walkthrough profile\'s rooms; the fold operation and the remaining non-guest rooms are out of scope this round'],
                render=dict(engine='Cycles',samples=args.samples,width=args.width,colorManagement='AgX',device=scene.cycles.device))
    (args.output/'study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'interior.blend'))
    bpy.ops.export_scene.gltf(filepath=str(args.output/'interior.glb'),export_format='GLB',export_extras=True)
    if args.render: bpy.ops.render.render(write_still=True)
    print(f'Interior study saved: {args.output}')


if __name__=='__main__':
    main()
