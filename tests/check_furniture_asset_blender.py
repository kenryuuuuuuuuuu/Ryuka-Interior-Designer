"""Run in Blender: production furniture generator against isolated in-memory edits."""
import copy
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
import build_interior as builder

original_read=builder.read
catalog=original_read(ROOT/'data/furniture-catalog.json')
source=original_read(ROOT/'data/furniture.json')
bindings=original_read(ROOT/'data/visual/asset-bindings.json')
original=next(i for i in source['items'] if i['id']=='fur-011')
data={'levels':{'fl1':.707},'rooms':[{'id':'test-room','level':1,'polygon':[[-10,-10],[10,-10],[10,10],[-10,10]]}]}
settings={'roomId':'test-room'}
report=[]

for rotation,w,d,h,elevation in [(0,1.7,.78,.78,0),(90,2.1,.9,.85,.2),(180,1.2,.7,.65,0),(270,2.4,1.05,1,.4)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    item=copy.deepcopy(original)
    item.update(x=4,z=5,rotation=rotation,widthOverride=w,depthOverride=d,heightOverride=h,elevation=elevation)
    def fixture_read(path):
        if path.name=='furniture.json': return {'items':[item]}
        if path.name=='asset-bindings.json': return bindings
        return original_read(path)
    builder.read=fixture_read
    mats={role:builder.material(role,'998877') for role in ('wood','fabric')}
    builder.build_furniture(data,settings,mats)
    objects=list(bpy.context.scene.objects)
    assert len(objects)==19, len(objects)
    coords=[];c,s=math.cos(math.radians(rotation)),math.sin(math.radians(rotation))
    for obj in objects:
        assert obj['asset_id']=='sofa-timber-v1'
        assert json.loads(obj['source_json'])==item
        assert json.loads(obj['asset_binding_json'])==bindings['bindings'][0]
        bm=bmesh.new();bm.from_mesh(obj.data)
        assert all(e.is_manifold for e in bm.edges)
        assert bm.calc_volume(signed=True)>0
        bm.free()
        for v in obj.data.vertices:
            x,y,z=v.co;px,py=x-item['x'],y+item['z']
            coords.append((c*px+s*py,s*px-c*py,z-.707))
    actual=[min(v[a] for v in coords) for a in range(3)]+[max(v[a] for v in coords) for a in range(3)]
    expected=[-w/2,-d/2,elevation,w/2,d/2,elevation+h]
    assert max(abs(a-b) for a,b in zip(actual,expected))<1e-5,(actual,expected)
    report.append({'rotation':rotation,'dimensions':[w,d,h],'elevation':elevation,'parts':len(objects)})

# Deleted source with binding must fail; removing both produces no orphan geometry.
bpy.ops.wm.read_factory_settings(use_empty=True)
def deleted_read(path):
    if path.name=='furniture.json': return {'items':[]}
    if path.name=='asset-bindings.json': return bindings
    return original_read(path)
builder.read=deleted_read
try: builder.build_furniture(data,settings,{})
except ValueError as error: assert 'orphan' in str(error)
else: raise AssertionError('Orphan binding accepted')
bindings={'schemaVersion':'1.0.0','bindings':[]}
builder.build_furniture(data,settings,{})
assert not list(bpy.context.scene.objects)
print(json.dumps({'cases':report,'removedBindingLeavesNoGeometry':True}))
