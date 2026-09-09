"""W03-B: previous-vs-current change diff and current-source reference checks.
Representative normal path and simple failure paths, per
docs/tasks/W03-B-source-changes.md's lightweight acceptance scope."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import source_changes as sc


def room(id,label='Room',polygon=None,status='estimated',note=''):
    return dict(id=id,level='1F',label=label,polygon=polygon or [[0,0],[1,0],[1,1],[0,1]],status=status,note=note)

def item(id,type='chair',room='room-a',x=0,z=0,rotation=0,elevation=0,label='Item',status='estimated',note=''):
    return dict(id=id,type=type,room=room,label=label,level='1F',x=x,z=z,rotation=rotation,elevation=elevation,status=status,note=note)

def ctype(type,label='Type',width=0.5,depth=0.5,height=0.5,category='seating',shape='box',rotationConvention='n',clearance=0,note=''):
    return dict(type=type,label=label,category=category,shape=shape,rotationConvention=rotationConvention,
        width=width,depth=depth,height=height,clearance=clearance,note=note)

def lighting_profile(source='point',lumens=500,temperatureK=2700,spotAngleDeg=None,directionLocal=None,status='estimated',note=''):
    return dict(source=source,lumens=lumens,temperatureK=temperatureK,spotAngleDeg=spotAngleDeg,
        directionLocal=directionLocal or [0,-1,0],status=status,note=note)


class SourceChangesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.previous=root/'previous'; self.current=root/'current'
        self.house=dict(schemaVersion='0.1.0',rooms=[room('room-a'),room('room-b')])
        self.furniture=dict(schemaVersion='0.1.0',items=[item('fur-1',room='room-a'),item('fur-2',room='room-b')])
        self.catalog=dict(schemaVersion='0.1.0',categories=[],types=[ctype('chair'),ctype('table',category='surface')])
        self.study=dict(schemaVersion='0.1.0',roomId='room-a')
        self.bindings=dict(schemaVersion='1.0.0',bindings=[dict(furnitureId='fur-1',assetId='chair-v1',sizing='parametric',status='estimated',note='')])
        self.decor=dict(schemaVersion='1.0.0',roomId='room-a',items=[dict(id='decor-1',kind='rug',furnitureId='fur-1',width=1,depth=1,status='estimated',note='')])
        self.openings=dict(schemaVersion='0.1.0',items=[dict(id='op-1',type='window',face='N',offset=0,level='1F',hingeSide=None,swingDir=None,label='Window',status='estimated')])
        self.lighting=dict(schemaVersion='1.0.0',
            profiles={'light-downlight':lighting_profile(),'light-ceiling':lighting_profile(lumens=3000)},
            unsupportedTypes={},
            groups=[dict(id='group-a',label='Group A',fixtureIds=['elec-1'])])
        self.write_current(); self.write_previous()

    def write_json(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')

    def write_current(self):
        self.write_json(self.current/'data/house.json',self.house)
        self.write_json(self.current/'data/furniture.json',self.furniture)
        self.write_json(self.current/'data/furniture-catalog.json',self.catalog)
        self.write_json(self.current/'data/visual/guest-ldk-study.json',self.study)
        self.write_json(self.current/'data/visual/asset-bindings.json',self.bindings)
        self.write_json(self.current/'data/visual/guest-decor.json',self.decor)
        self.write_json(self.current/'data/openings.json',self.openings)
        self.write_json(self.current/'data/visual/lighting-settings.json',self.lighting)

    def write_previous(self,house=None,furniture=None,catalog=None,lighting=None):
        inputs=self.previous/'SourcePackage/inputs'
        files={'data/house.json':house or self.house,'data/furniture.json':furniture or self.furniture,
               'data/furniture-catalog.json':catalog or self.catalog,
               'data/visual/lighting-settings.json':lighting or self.lighting}
        hashes={}
        for relpath,value in files.items():
            path=inputs/relpath
            self.write_json(path,value)
            hashes[relpath]=sc.content_sha(path)
        self.write_json(self.previous/'SourcePackage/manifest.json',dict(sourceCommit='abc',sourceHashes=hashes))

    # --- happy path: moved/added/removed furniture, catalog dim change, room rename ---

    def test_representative_changes_are_diffed_by_id_not_array_order(self):
        self.house['rooms']=[room('room-b',label='B'),room('room-a',label='A・改名')]  # reordered + renamed
        self.furniture['items']=[item('fur-2',type='table',room='room-b'),item('fur-1',room='room-a',x=5),
            item('fur-3',type='table',room='room-a',label='New table')]
        self.catalog['types']=[ctype('table',category='surface'),ctype('chair',width=0.6)]
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['baselineStatus'],'available')
        self.assertEqual(changes['furniture']['added'][0]['id'],'fur-3')
        self.assertEqual(changes['furniture']['removed'],[])
        mod=next(m for m in changes['furniture']['modified'] if m['id']=='fur-1')
        field=next(f for f in mod['fields'] if f['field']=='x')
        self.assertEqual((field['before'],field['after'],field['category']),(0,5,'配置'))
        room_mod=next(m for m in changes['rooms']['modified'] if m['id']=='room-a')
        self.assertEqual(next(f for f in room_mod['fields'] if f['field']=='label')['category'],'名称・注記')
        cat_mod=next(m for m in changes['catalog']['modified'] if m['id']=='chair')
        self.assertEqual(cat_mod['affectedFurnitureIds'],['fur-1'])  # candidate impact via current furniture
        self.assertEqual(changes['rooms']['added'],[]); self.assertEqual(changes['rooms']['removed'],[])
        self.assertEqual(changes['issues'],[])

    def test_lighting_profile_and_group_changes_are_diffed(self):
        # W06-v1 review R4: lighting-settings.json's profiles/groups must
        # appear in the change report too, same shallow keyed-diff treatment
        # as rooms/furniture/catalog (not electrical.json's full fixture list).
        self.lighting['profiles']['light-downlight']=lighting_profile(lumens=900)  # changed
        self.lighting['profiles']['light-pendant']=lighting_profile(source='point',lumens=800)  # added
        self.lighting['groups']=[dict(id='group-a',label='Group A・改名',fixtureIds=['elec-1','elec-2'])]
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['baselineStatus'],'available')
        profile_mod=next(m for m in changes['lightingProfiles']['modified'] if m['id']=='light-downlight')
        field=next(f for f in profile_mod['fields'] if f['field']=='lumens')
        self.assertEqual((field['before'],field['after'],field['category']),(500,900,'光学値'))
        self.assertEqual(changes['lightingProfiles']['added'][0]['id'],'light-pendant')
        group_mod=next(m for m in changes['lightingGroups']['modified'] if m['id']=='group-a')
        categories={f['category'] for f in group_mod['fields']}
        self.assertEqual(categories,{'構成','名称'})
        page=sc.render_html(changes)
        self.assertIn('照明プロファイル',page); self.assertIn('照明グループ',page)

    def test_array_reorder_alone_is_not_a_change(self):
        self.house['rooms']=list(reversed(self.house['rooms']))
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['rooms'],dict(added=[],removed=[],modified=[]))

    # --- reference issues stop before generation; fixing them clears the issue ---

    def test_removed_furniture_with_dangling_decor_reference_is_an_issue(self):
        self.furniture['items']=[item('fur-2',room='room-b')]  # fur-1 removed, decor still points at it
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        self.assertTrue(any(i['targetId']=='fur-1' and i['sourceFile']=='data/visual/guest-decor.json' for i in changes['issues']))
        self.assertTrue(any('decor-1' in i['message'] and 'fur-1' in i['message'] for i in changes['issues']))

    def test_removing_the_dangling_reference_too_clears_the_issue(self):
        self.furniture['items']=[item('fur-2',room='room-b')]
        self.decor['items']=[]  # both references removed along with the furniture
        self.bindings['bindings']=[]
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['issues'],[])

    def test_missing_room_reference_and_duplicate_id_are_issues(self):
        self.furniture['items']=[item('fur-1',room='room-missing'),item('fur-1',room='room-a')]  # dup id + bad room
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        codes={(i['code'],i['sourceId']) for i in changes['issues']}
        self.assertIn(('duplicate-id','fur-1'),codes)
        self.assertIn(('missing-reference','fur-1'),codes)

    # --- stale/unusable baseline: warning only, current items are not "all added" ---

    def test_missing_baseline_snapshot_is_a_warning_not_all_added(self):
        import shutil
        shutil.rmtree(self.previous/'SourcePackage')
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['baselineStatus'],'unavailable')
        self.assertIsNone(changes['furniture'])
        self.assertEqual(changes['issues'],[])  # current source itself is still fine

    def test_tampered_baseline_hash_is_unavailable(self):
        (self.previous/'SourcePackage/inputs/data/house.json').write_text('{"rooms":[]}',encoding='utf-8')
        changes=sc.compare(self.previous,self.current)
        self.assertEqual(changes['baselineStatus'],'unavailable')

    # --- html rendering escapes and includes the scope disclaimer ---

    def test_html_escapes_and_states_scope(self):
        self.house['rooms']=[room('room-a',label='<script>bad</script>'),room('room-b')]
        self.write_current()
        changes=sc.compare(self.previous,self.current)
        page=sc.render_html(changes)
        self.assertNotIn('<script>bad</script>',page)
        self.assertIn('&lt;script&gt;',page)
        self.assertIn('屋根・階段・設備・開口全体の変更検出は含みません',page)


if __name__=='__main__': unittest.main()
