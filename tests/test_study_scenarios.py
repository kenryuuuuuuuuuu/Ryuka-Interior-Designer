"""W03-A: save/list/reapply named comparison scenarios. Representative normal
paths and a few simple failure paths, per docs/tasks/W03-A-saved-scenarios.md's
'lightweight acceptance' scope -- not exhaustive fault injection."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name.replace('_','-')+'.py'))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

save_scenario=load('save_study_scenario')
list_scenarios=load('list_study_scenarios')
import refresh_inputs


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)/'project'; self.project.mkdir()
        self.state=dict(schemaVersion='1.0.0',roomId='room-1f-06',variant='warm',
                        azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None)
        self.write('study-state.json',self.state)
        self.write('import-verification.json',dict(unrealImportVerified=True,siteContext=None))
        (self.project/'SourcePackage').mkdir()
        self.write('SourcePackage/manifest.json',dict(sourceCommit='abc123',sourceHashes={'data/house.json':'deadbeef'}))
        # save-study-scenario.py requires --output under ROOT/build/; fake a
        # minimal ROOT (mocked only for that check, not for reading real repo
        # fixtures like data/visual/guest-ldk-study.json, which refresh_inputs
        # reads via its own independent ROOT and stays real on purpose).
        self.fake_root=Path(self.temp.name)/'repo'; (self.fake_root/'build').mkdir(parents=True)
        self.scenarios_root=self.fake_root/'build/scenarios'

    def write(self,relative,value):
        path=self.project/relative; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value),encoding='utf-8')

    def run_save(self,name,note='',output=None):
        output=output or self.scenarios_root/name.replace(' ','-')
        argv=['save-study-scenario','--project',str(self.project),'--name',name,'--note',note,'--output',str(output)]
        # The build/-relative-path check now lives in refresh_inputs.save_scenario_package()
        # (also called directly, in-process, by the UE editor's own menu action -- see that
        # module's docstring). It checks SCENARIO_ROOT specifically (not ROOT, which
        # retained_inputs() uses to read real repo fixtures and must stay real here).
        with mock.patch.object(sys,'argv',argv), mock.patch.object(refresh_inputs,'SCENARIO_ROOT',self.fake_root):
            save_scenario.main()
        return output

    # --- save: happy path -------------------------------------------------

    def test_save_two_named_scenarios_independent_and_listed(self):
        out_a=self.run_save('ゲストLDK・木部案A','午前の検討')
        self.write('study-state.json',dict(self.state,variant='reference'))  # changed after saving A
        out_b=self.run_save('ゲストLDK・石調案B')
        scenario_a=json.loads((out_a/'scenario.json').read_text(encoding='utf-8'))
        scenario_b=json.loads((out_b/'scenario.json').read_text(encoding='utf-8'))
        self.assertEqual(scenario_a['schemaVersion'],'1.0.0')
        self.assertNotEqual(scenario_a['id'],scenario_b['id'])
        self.assertEqual(scenario_a['name'],'ゲストLDK・木部案A')
        self.assertEqual(scenario_a['note'],'午前の検討')
        self.assertEqual(scenario_a['roomId'],'room-1f-06')
        self.assertEqual(scenario_a['origin']['sourceCommit'],'abc123')
        self.assertEqual(scenario_a['origin']['sourceHashes'],{'data/house.json':'deadbeef'})
        self.assertEqual(scenario_a['origin']['stateSource'],'editor')
        recorded_hash=scenario_a['files']['study-state.json']['sha256']
        self.assertEqual(recorded_hash,refresh_inputs.sha(out_a/'study-state.json'))
        # A's saved variant must be unaffected by B changing the project's live state afterwards.
        saved_a=json.loads((out_a/'study-state.json').read_text(encoding='utf-8'))
        self.assertEqual(saved_a['variant'],'warm')
        saved_b=json.loads((out_b/'study-state.json').read_text(encoding='utf-8'))
        self.assertEqual(saved_b['variant'],'reference')

        out=io.StringIO()
        with redirect_stdout(out):
            with mock.patch.object(sys,'argv',['list-study-scenarios','--root',str(self.scenarios_root)]):
                list_scenarios.main()
        listing=out.getvalue()
        self.assertIn('ゲストLDK・木部案A',listing)
        self.assertIn('ゲストLDK・石調案B',listing)
        self.assertIn('warm',listing); self.assertIn('reference',listing)

    def test_save_prefers_newer_runtime_state_and_records_stateSource(self):
        import os
        self.write('Saved/walkthrough-state.json',dict(self.state,variant='natural'))
        os.utime(self.project/'study-state.json',(100,100))
        os.utime(self.project/'Saved/walkthrough-state.json',(200,200))
        output=self.run_save('内覧で保存した案')
        scenario=json.loads((output/'scenario.json').read_text(encoding='utf-8'))
        self.assertEqual(scenario['origin']['stateSource'],'runtime')
        self.assertEqual(json.loads((output/'study-state.json').read_text(encoding='utf-8'))['variant'],'natural')

    # --- save: simple failure paths ---------------------------------------

    def test_save_rejects_blank_and_overlong_name(self):
        with self.assertRaises(SystemExit): self.run_save('   ',output=self.scenarios_root/'x')
        with self.assertRaises(SystemExit): self.run_save('a'*121,output=self.scenarios_root/'y')

    def test_save_rejects_existing_output(self):
        output=self.run_save('最初の案')
        with self.assertRaises(SystemExit): self.run_save('別の名前',output=output)

    def test_save_refuses_mid_recovery_runtime_state(self):
        # No current runtime save, only its backup: the disk signature W02's
        # RecoverSaveIfNeeded() leaves after a failed replace+restore. Must
        # abort, not silently fall back to study-state.json. save-study-scenario.py's
        # main() turns save_scenario_package()'s ValueError into a clean SystemExit
        # (parser.error); refresh_inputs.save_scenario_package() itself (called
        # in-process by the UE editor's own menu action, study_controls.save_scenario())
        # still raises the raw ValueError there.
        self.write('Saved/walkthrough-state.json.bak',dict(self.state,variant='natural'))
        with self.assertRaises(SystemExit):
            self.run_save('復旧待ち中の保存')

    def test_save_rejects_invalid_state(self):
        self.write('study-state.json',dict(marker='not a real state'))
        with self.assertRaises(SystemExit):
            self.run_save('壊れた状態')

    # --- list: an invalid scenario does not block the others --------------

    def test_list_invalid_scenario_reported_without_hiding_valid_ones(self):
        good=self.run_save('有効な案')
        bad=self.scenarios_root/'bad'; bad.mkdir()
        scenario=json.loads((good/'scenario.json').read_text(encoding='utf-8'))
        (bad/'scenario.json').write_text(json.dumps(scenario),encoding='utf-8')
        # study-state.json deliberately left missing: an incomplete/corrupted
        # scenario directory, which list must report without hiding 'good'.
        out=io.StringIO()
        with redirect_stdout(out):
            with mock.patch.object(sys,'argv',['list-study-scenarios','--root',str(self.scenarios_root)]):
                list_scenarios.main()
        listing=out.getvalue()
        self.assertIn('有効な案',listing)
        self.assertIn('[invalid]',listing)

    # --- refresh --scenario: reapplication input selection -----------------

    def test_scenario_inputs_reads_only_the_package(self):
        output=self.run_save('再適用対象の案')
        paths,scenario=refresh_inputs.scenario_inputs(output)
        self.assertEqual(paths['state'],output/'study-state.json')
        self.assertEqual(scenario['name'],'再適用対象の案')

    def test_scenario_bundles_site_and_rejects_stale_cases(self):
        # W05: site.local.json is picked up by the same generic retained-files
        # loop save_scenario_package() already had -- no special-casing needed
        # there -- but scenario_inputs() must still check it against any
        # bundled sun-cases.json.
        from solar_position import make_case
        site=dict(schemaVersion='1.0.0',latitudeDeg=35,longitudeDeg=135,planNorthAzimuthDeg=0,
            locationStatus='estimated',northStatus='estimated',note='Synthetic test site.')
        self.write('site.local.json',site)
        output=self.run_save('敷地付きの案')
        self.assertTrue((output/'site.local.json').is_file())
        paths,_=refresh_inputs.scenario_inputs(output)
        self.assertEqual(paths['site'],output/'site.local.json')
        # Now bundle a sun-cases.json computed under a DIFFERENT site into
        # the same package (simulating a hand-edited/stale package) and
        # re-sign scenario.json so only the site/cases mismatch is being
        # tested, not the file-hash check.
        stale_cases=dict(schemaVersion='1.0.0',siteDaylightCalibrated=False,
            cases=[make_case(dict(site,latitudeDeg=36),'2026-06-21T12:00:00+09:00')])
        (output/'sun-cases.json').write_text(json.dumps(stale_cases),encoding='utf-8')
        scenario=json.loads((output/'scenario.json').read_text(encoding='utf-8'))
        scenario['files']['sun-cases.json']=dict(sha256=refresh_inputs.sha(output/'sun-cases.json'))
        (output/'scenario.json').write_text(json.dumps(scenario),encoding='utf-8')
        with self.assertRaises(ValueError):
            refresh_inputs.scenario_inputs(output)

    def test_scenario_inputs_rejects_hash_mismatch(self):
        output=self.run_save('改ざん検知対象の案')
        (output/'study-state.json').write_text(json.dumps(dict(self.state,variant='reference')),encoding='utf-8')
        with self.assertRaises(ValueError):
            refresh_inputs.scenario_inputs(output)

    def test_scenario_inputs_rejects_other_room(self):
        self.write('study-state.json',dict(self.state,roomId='room-1f-06'))
        output=self.run_save('部屋ID差し替え前の案')
        scenario=json.loads((output/'scenario.json').read_text(encoding='utf-8'))
        state=json.loads((output/'study-state.json').read_text(encoding='utf-8'))
        state['roomId']='room-1f-99'
        (output/'study-state.json').write_text(json.dumps(state),encoding='utf-8')
        scenario['files']['study-state.json']['sha256']=refresh_inputs.sha(output/'study-state.json')
        (output/'scenario.json').write_text(json.dumps(scenario),encoding='utf-8')
        with self.assertRaises(ValueError):
            refresh_inputs.scenario_inputs(output)


if __name__=='__main__': unittest.main()
