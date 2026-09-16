import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
sys.path.insert(0,str(ROOT/'scripts'))
from storage_assets import storage_parts, settings
from furniture_assets import asset_parts, STORAGE_ASSETS


class StorageAssets(unittest.TestCase):
    def test_layout_and_box_clearances(self):
        catalog={t['type']:t for t in json.loads((ROOT/'data/furniture-catalog.json').read_text(encoding='utf-8'))['types']}
        items=[i for i in json.loads((ROOT/'data/furniture.json').read_text(encoding='utf-8'))['items'] if i.get('room')=='room-1f-12']
        rects={}
        for item in items:
            t=catalog[item['type']];w,d,h=[item.get(k+'Override',t[k]) for k in ('width','depth','height')]
            parts=asset_parts(STORAGE_ASSETS[t['shape']],w,d,h,item.get('storage'))
            for part in parts:
                a,b,c,e,f,g=part['bounds']
                self.assertTrue(-w/2-1e-8<=a<b<=w/2+1e-8)
                self.assertTrue(-d/2-1e-8<=c<e<=d/2+1e-8)
                self.assertTrue(0<=f<g<=h+1e-8)
            if item['rotation']%180:w,d=d,w
            x,z=item['x'],item['z'];rects[item['id']]=(x-w/2,x+w/2,z-d/2,z+d/2)
            self.assertGreaterEqual(x-w/2,15.501);self.assertLessEqual(x+w/2,19.05)
            self.assertGreaterEqual(z-d/2,.06);self.assertLessEqual(z+d/2,1.79)
        for key,a in rects.items():
            for other,b in rects.items():
                if key>=other:continue
                self.assertFalse(min(a[1],b[1])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[2],b[2])>1e-6,(key,other))
        self.assertAlmostEqual(rects['fur-cloak-05'][2]-rects['fur-cloak-01'][3],.8)
        self.assertGreaterEqual(rects['fur-cloak-05'][0],17.25) # opening + full sliding leaf travel
        # East-facing box withdrawals have a clear standing area in front of both columns.
        self.assertGreaterEqual(rects['fur-cloak-04'][0]-rects['fur-cloak-05'][1],.65)
        shelf=next(i for i in items if i['id']=='fur-cloak-04')
        parts=storage_parts('closetShelves',1.1,.45,2.2,shelf['storage'])
        boxes=[p for p in parts if p['name'].startswith('box-') and p['name'].endswith('-body')]
        self.assertEqual(len(boxes),8)
        for box in boxes:
            b=box['bounds'];self.assertAlmostEqual(b[1]-b[0],.35);self.assertAlmostEqual(b[3]-b[2],.4)

    def test_invalid_and_hidden_contents(self):
        for opts in ({'railHeights':[1.8,.9]}, {'railHeights':[1,1.1]}, {'railHeights':[1,float('nan')]}, {'unknown':3}):
            with self.assertRaises(ValueError):settings('closetDouble',1,.6,2.2,opts)
        parts=storage_parts('closetDouble',1,.6,2.2,{'contents':False})
        self.assertFalse(any('garment' in p['name'] for p in parts))
        self.assertEqual(len([p for p in parts if p['kind']=='cylinderX']),2)

    def test_import_report_retains_storage_changes(self):
        from guest_launcher.furniture import build_report
        import tempfile
        doc=json.loads((ROOT/'data/furniture.json').read_text(encoding='utf-8'))
        next(i for i in doc['items'] if i['id']=='fur-cloak-03')['storage']['railHeights']=[.9,1.8]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'furniture.json';path.write_text(json.dumps(doc),encoding='utf-8')
            report=build_report(path)
            self.assertTrue(report.ok,report.validationError)
            change=next(c for c in report.changes if c.id=='fur-cloak-03')
            self.assertTrue(any(f['field']=='storage' for f in change.fields))

if __name__=='__main__':unittest.main()
