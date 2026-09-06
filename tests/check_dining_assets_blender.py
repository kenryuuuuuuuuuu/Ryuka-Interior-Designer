"""Blender integration: curved chair and elliptical table dimensions and GLB geometry."""
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
import build_interior as builder
read=builder.read
data={'levels':{'fl1':.707},'rooms':[{'id':'test','level':1,'polygon':[[-10,-10],[10,-10],[10,10],[-10,10]]}]}
results=[]
for kind,asset,dimensions,parts in [('dining-table-round','round-table-v1',[(.9,.9,.72),(1.2,.8,.75)],5),
                                    ('chair-timber','chair-timber-v1',[(.45,.48,.85),(.6,.6,.95)],9)]:
    for rotation in [0,90,180,270]:
        for w,d,h in dimensions:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            item=dict(id='fixture',type=kind,level=1,x=4,z=5,rotation=rotation,elevation=.2,
                      widthOverride=w,depthOverride=d,heightOverride=h,status='estimated',note='In-memory test')
            binding=dict(furnitureId='fixture',assetId=asset,sizing='parametric',status='estimated',note='Test')
            def fixture_read(path):
                if path.name=='furniture.json':return {'items':[item]}
                if path.name=='asset-bindings.json':return {'schemaVersion':'1.0.0','bindings':[binding]}
                return read(path)
            builder.read=fixture_read
            builder.build_furniture(data,{'roomId':'test'},{r:builder.material(r,'998877') for r in ['wood','fabric']})
            objects=list(bpy.context.scene.objects);assert len(objects)==parts
            coords=[];c,s=math.cos(math.radians(rotation)),math.sin(math.radians(rotation))
            for obj in objects:
                assert json.loads(obj['source_json'])==item
                bm=bmesh.new();bm.from_mesh(obj.data)
                assert all(e.is_manifold for e in bm.edges),obj.name
                assert bm.calc_volume(signed=True)>0,obj.name
                bm.free()
                for v in obj.data.vertices:
                    x,y,z=v.co;px,py=x-4,y+5
                    coords.append((c*px+s*py,s*px-c*py,z-.707))
            actual=[min(v[a] for v in coords) for a in range(3)]+[max(v[a] for v in coords) for a in range(3)]
            expected=[-w/2,-d/2,.2,w/2,d/2,.2+h]
            assert max(abs(a-b) for a,b in zip(actual,expected))<1e-5,(actual,expected)
            results.append([kind,rotation,w,d,h])
print(json.dumps({'closedSolidsAndSourceBounds':True,'cases':len(results)}))
