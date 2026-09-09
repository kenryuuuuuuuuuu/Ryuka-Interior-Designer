"""Preflight must retain local context and reject silent loss or stale settings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('refresh',ROOT/'scripts/refresh-visual-study.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from solar_position import make_case  # sys.path already has unreal/, inserted by m's own module code above


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous=Path(self.temp.name)
        self.state=dict(schemaVersion='1.0.0',roomId='room-1f-06',variant='warm',
                        azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None)
        self.write('study-state.json',self.state)
        self.write('import-verification.json',dict(unrealImportVerified=True,siteContext=None))

    def write(self,name,value):
        (self.previous/name).write_text(json.dumps(value),encoding='utf-8')

    def test_manual_study_and_gallery_requires_cases(self):
        self.assertEqual(set(m.retained_inputs(self.previous)),{'state'})
        with self.assertRaises(ValueError): m.retained_inputs(self.previous,gallery=True)

    def test_latest_walkthrough_state_retained_and_validated(self):
        import os
        (self.previous/'Saved').mkdir()
        runtime=self.previous/'Saved/walkthrough-state.json'
        self.write('Saved/walkthrough-state.json',dict(self.state,variant='reference'))
        os.utime(self.previous/'study-state.json',(100,100)); os.utime(runtime,(200,200))
        self.assertEqual(m.retained_inputs(self.previous)['state'],runtime)
        os.utime(self.previous/'study-state.json',(300,300))
        self.assertEqual(m.retained_inputs(self.previous)['state'],self.previous/'study-state.json')
        self.write('Saved/walkthrough-state.json',dict(self.state,roomId='wrong-room'))
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)

    def test_context_preserved_missing_or_changed_rejected(self):
        context=dict(schemaVersion='1.0.0',boxes=[])
        self.write('site-context.json',context)
        digest=m.sha(self.previous/'site-context.json')
        self.state['siteContextSHA256']=digest
        self.write('study-state.json',self.state)
        self.write('import-verification.json',dict(unrealImportVerified=True,siteContext=dict(sha256=digest)))
        self.assertIn('context',m.retained_inputs(self.previous))
        self.write('site-context.json',dict(context,note='changed'))
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)
        (self.previous/'site-context.json').unlink()
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)

    def test_old_context_without_saved_binding_rejected_early(self):
        self.write('site-context.json',dict(schemaVersion='1.0.0',boxes=[]))
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)

    def test_site_retained_and_stale_cases_rejected(self):
        # W05: site.local.json is optional and retained on its own; only
        # checked for consistency once sun-cases.json also exists.
        site=dict(schemaVersion='1.0.0',latitudeDeg=35,longitudeDeg=135,planNorthAzimuthDeg=0,
            locationStatus='estimated',northStatus='estimated',note='Synthetic test site.')
        self.write('site.local.json',site)
        self.assertIn('site',m.retained_inputs(self.previous))
        self.write('sun-cases.json',dict(schemaVersion='1.0.0',siteDaylightCalibrated=False,
            cases=[make_case(site,'2026-06-21T12:00:00+09:00')]))
        self.assertIn('site',m.retained_inputs(self.previous))
        # Site changed after the cases were computed -- must be rejected,
        # not silently retained as if it still matched.
        self.write('site.local.json',dict(site,latitudeDeg=36))
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)

    def test_state_solar_must_match_retained_site(self):
        # W05-v1 review R1: cases_match_site() only checks the retained
        # sun-cases LIST; the retained STATE's own solar must independently
        # match the retained site too. This reproduces the review's own
        # repro exactly: sun-cases match the site, but the retained state's
        # solar is stale (computed under a different site) -- a normal
        # sequence (site changed, cases recomputed, state not yet
        # reapplied), not a contrived one, and must be rejected.
        site=dict(schemaVersion='1.0.0',latitudeDeg=35,longitudeDeg=135,planNorthAzimuthDeg=0,
            locationStatus='estimated',northStatus='estimated',note='Synthetic test site.')
        other_site=dict(site,latitudeDeg=36)
        case=make_case(site,'2026-06-21T12:00:00+09:00')
        stale_solar=make_case(other_site,'2026-06-21T12:00:00+09:00')
        self.write('site.local.json',site)
        self.write('sun-cases.json',dict(schemaVersion='1.0.0',siteDaylightCalibrated=False,cases=[case]))
        self.write('study-state.json',dict(self.state,azimuthDeg=stale_solar['azimuthDeg'],
            elevationDeg=stale_solar['elevationDeg'],solar=stale_solar))
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)
        # Reapplying the current-site case (state.solar now matches) succeeds.
        self.write('study-state.json',dict(self.state,azimuthDeg=case['azimuthDeg'],
            elevationDeg=case['elevationDeg'],solar=case))
        self.assertIn('site',m.retained_inputs(self.previous))

    def test_lighting_fixture_reference_checked_against_current_source(self):
        # W06-v1 review R4: a retained state's lighting.fixtures must be
        # checked against the CURRENT source's resolvable fixtures, not left
        # for Blender to discover after the heavy build has already started.
        known_state=dict(self.state,schemaVersion='1.2.0',surfaceOverrides={},
            lighting=dict(mode='night',fixtures={'elec-008':{'on':True}}))
        self.write('study-state.json',known_state)
        self.assertIn('state',m.retained_inputs(self.previous))  # a real, current fixture id: fine
        unknown_state=dict(self.state,schemaVersion='1.2.0',surfaceOverrides={},
            lighting=dict(mode='night',fixtures={'elec-does-not-exist':{'on':True}}))
        self.write('study-state.json',unknown_state)
        with self.assertRaises(ValueError): m.retained_inputs(self.previous)

    def test_summary_escapes_note_and_links_only_requested_gallery(self):
        report=dict(note='<script>bad</script>',gallery=False,changedSourceFiles=['data/house.json'])
        page=m.summary(report)
        self.assertNotIn('<script>',page); self.assertNotIn('comparison/index.html',page)
        self.assertIn('&lt;script&gt;',page)

    def test_source_change_marks_failed_stage_without_completion_page(self):
        root=self.previous/'repo'
        (root/'data/visual').mkdir(parents=True)
        (root/'data/visual/unreal-finishes.json').write_text((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8'),encoding='utf-8')
        engine=root/'engine'; (engine/'Engine/Binaries/Win64').mkdir(parents=True)
        (engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe').touch()
        blender=root/'blender.exe'; blender.touch()
        (self.previous/'SourcePackage').mkdir()
        self.write('SourcePackage/manifest.json',dict(sourceHashes={}))
        output=root/'build/result'
        argv=['refresh','--previous',str(self.previous),'--output',str(output),'--engine',str(engine),
              '--blender',str(blender),'--cache',str(self.previous/'cache')]
        with mock.patch.object(m,'ROOT',root),mock.patch.object(m.sys,'argv',argv),\
             mock.patch.object(m,'retained_inputs',return_value={'state':self.previous/'study-state.json'}),\
             mock.patch.object(m.shutil,'which',return_value='node'),\
             mock.patch.object(m,'sources',side_effect=[{'input':'a'},{'input':'a'},{'input':'b'}]),\
             mock.patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            with self.assertRaisesRegex(RuntimeError,'Source files changed'): m.main()
        result=m.read(output/'refresh.json')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['steps'][0]['status'],'failed')
        self.assertFalse((output/'index.html').exists())

    def test_current_reference_issue_stops_before_blender_or_unreal(self):
        # W03-B: a dangling reference in the current source must fail before
        # any subprocess (Blender/Unreal) is ever launched.
        root=self.previous/'repo'
        data=root/'data'; visual=data/'visual'; visual.mkdir(parents=True)
        (visual/'unreal-finishes.json').write_text((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8'),encoding='utf-8')
        def write(relative,value): (root/relative).write_text(json.dumps(value),encoding='utf-8')
        write('data/house.json',dict(rooms=[dict(id='room-a',level='1F',label='A',polygon=[[0,0]],status='estimated',note='')]))
        write('data/furniture.json',dict(items=[dict(id='fur-1',type='chair',room='room-a',label='Chair',level='1F',
            x=0,z=0,rotation=0,elevation=0,status='estimated',note='')]))
        write('data/furniture-catalog.json',dict(categories=[],types=[dict(type='chair',label='Chair',category='seating',
            shape='box',rotationConvention='n',width=0.5,depth=0.5,height=0.5,clearance=0,note='')]))
        write('data/visual/guest-ldk-study.json',dict(roomId='room-a'))
        write('data/visual/asset-bindings.json',dict(bindings=[]))
        write('data/visual/guest-decor.json',dict(roomId='room-a',items=[dict(id='decor-1',kind='rug',
            furnitureId='fur-MISSING',width=1,depth=1,status='estimated',note='')]))
        write('data/openings.json',dict(items=[]))
        engine=root/'engine'; (engine/'Engine/Binaries/Win64').mkdir(parents=True)
        (engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe').touch()
        blender=root/'blender.exe'; blender.touch()
        (self.previous/'SourcePackage').mkdir()
        self.write('SourcePackage/manifest.json',dict(sourceHashes={}))
        output=root/'build/result'
        argv=['refresh','--previous',str(self.previous),'--output',str(output),'--engine',str(engine),
              '--blender',str(blender),'--cache',str(self.previous/'cache')]
        with mock.patch.object(m,'ROOT',root),mock.patch.object(m.source_changes,'ROOT',root),\
             mock.patch.object(m.sys,'argv',argv),\
             mock.patch.object(m,'retained_inputs',return_value={'state':self.previous/'study-state.json'}),\
             mock.patch.object(m.shutil,'which',return_value='node'),\
             mock.patch.object(m,'sources',return_value={'input':'a'}),\
             mock.patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            with self.assertRaisesRegex(RuntimeError,'reference issues'): m.main()
            # 01-source-check (node --check) is a real subprocess step that must
            # still run; the point is that Blender/Unreal (02-blender onward)
            # never get a chance to launch. That first call is 'node ... --check'.
            self.assertEqual(run.call_count,1)
            self.assertIn('build-web-data.mjs',str(run.call_args))
        result=m.read(output/'refresh.json')
        self.assertEqual(result['status'],'failed')
        self.assertTrue(any('fur-MISSING' in i['message'] for i in m.read(output/'source-changes.json')['issues']))
        self.assertFalse((output/'index.html').exists())

    def test_unresolved_surface_registry_stops_before_blender_or_unreal(self):
        # W03-C: an unresolved registered surface must also fail before any
        # subprocess (Blender/Unreal) is launched, same as a reference issue.
        root=self.previous/'repo'
        data=root/'data'; visual=data/'visual'; visual.mkdir(parents=True)
        (visual/'unreal-finishes.json').write_text((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8'),encoding='utf-8')
        def write(relative,value): (root/relative).write_text(json.dumps(value),encoding='utf-8')
        write('data/house.json',dict(rooms=[dict(id='room-a',level='1F',label='A',polygon=[[0,0],[2,0],[2,2],[0,2]],status='estimated',note='')]))
        write('data/furniture.json',dict(items=[]))
        write('data/furniture-catalog.json',dict(categories=[],types=[]))
        write('data/visual/guest-ldk-study.json',dict(roomId='room-a'))
        write('data/visual/asset-bindings.json',dict(bindings=[]))
        write('data/visual/guest-decor.json',dict(roomId='room-a',items=[]))
        write('data/openings.json',dict(items=[]))
        # References a wall edge that does not exist in room-a's polygon above.
        write('data/visual/surface-registry.json',dict(schemaVersion='1.0.0',surfaces=[
            dict(id='surf-x',roomId='room-a',kind='wall',label='X',note='',edge=[[9,9],[9,10]])]))
        engine=root/'engine'; (engine/'Engine/Binaries/Win64').mkdir(parents=True)
        (engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe').touch()
        blender=root/'blender.exe'; blender.touch()
        (self.previous/'SourcePackage').mkdir()
        self.write('SourcePackage/manifest.json',dict(sourceHashes={}))
        output=root/'build/result'
        argv=['refresh','--previous',str(self.previous),'--output',str(output),'--engine',str(engine),
              '--blender',str(blender),'--cache',str(self.previous/'cache')]
        with mock.patch.object(m,'ROOT',root),mock.patch.object(m.source_changes,'ROOT',root),\
             mock.patch.object(m.surface_registry,'ROOT',root),\
             mock.patch.object(m.sys,'argv',argv),\
             mock.patch.object(m,'retained_inputs',return_value={'state':self.previous/'study-state.json'}),\
             mock.patch.object(m.shutil,'which',return_value='node'),\
             mock.patch.object(m,'sources',return_value={'input':'a'}),\
             mock.patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            with self.assertRaisesRegex(RuntimeError,'surface registry'): m.main()
            self.assertEqual(run.call_count,1)  # only 01-source-check; Blender/Unreal never launched
        result=m.read(output/'refresh.json')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(m.read(output/'surface-resolution.json')['issues'][0]['id'],'surf-x')
        self.assertFalse((output/'index.html').exists())


if __name__=='__main__': unittest.main()
