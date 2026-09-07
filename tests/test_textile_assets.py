import math
import sys
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'blender'))
from guest_decor import build, resolve
from textile_assets import styling_parts


class TextileAssets(unittest.TestCase):
    def test_closed_meshes_at_supported_sizes(self):
        for kind,dimensions in [('sofa-textiles',(1.2,.7,.65)),('sofa-textiles',(2.4,1.05,1)),
                                ('tabletop',(.65,.32,.25)),('tabletop',(1.4,.8,.65))]:
            for part in styling_parts(kind,*dimensions):
                edges=Counter()
                for face in part['faces']:
                    for a,b in zip(face,face[1:]+face[:1]): edges[tuple(sorted((a,b)))]+=1
                self.assertTrue(all(count==2 for count in edges.values()),part['name'])
                self.assertTrue(all(math.isfinite(v) for vertex in part['vertices'] for v in vertex))

    def test_tabletop_tracks_rotation_height_and_size(self):
        document=dict(schemaVersion='0.1.0',roomId='r',items=[dict(id='props',kind='tabletop',furnitureId='t',status='estimated',note='Test')])
        data=dict(rooms=[dict(id='r',level=1)],levels=dict(fl1=.707))
        catalog=dict(types=[dict(type='table',shape='table',width=.85,depth=.4,height=.4)])
        for width in (.65,1.2):
            for rotation in (0,90,180,270):
                item=dict(id='t',type='table',level=1,x=3,z=5,rotation=rotation,elevation=.12,widthOverride=width,heightOverride=.5)
                captured=[]
                def capture(name,vertices,faces,material,source):
                    captured.extend(vertices)
                    return SimpleNamespace(data=SimpleNamespace(polygons=[]))
                build(document,data,[item],[],dict(wood=None,fabric=None,stone=None),None,capture,catalog)
                self.assertAlmostEqual(min(v[2] for v in captured),.707+.12+.5+.001)
                angle=math.radians(rotation); c,s=math.cos(angle),math.sin(angle)
                local=[(c*(x-3)-s*(-y-5),s*(x-3)+c*(-y-5)) for x,y,_ in captured]
                self.assertLessEqual(max(abs(x) for x,z in local),width/2)
                self.assertLessEqual(max(abs(z) for x,z in local),.4/2)
                self.assertAlmostEqual(max(x for x,z in local),width*.25+.065)
        with self.assertRaises(ValueError): resolve(document,data,[],[],catalog)
        catalog['types'][0]['shape']='chair'
        with self.assertRaises(ValueError): resolve(document,data,[item],[],catalog)

    def test_out_of_range_fails_before_generation(self):
        for args in [('sofa-textiles',.8,.8,.8),('tabletop',.6,.4,.4),('tabletop',.8,float('nan'),.4)]:
            with self.assertRaises(ValueError): styling_parts(*args)


if __name__=='__main__': unittest.main()
