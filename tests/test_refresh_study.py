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


if __name__=='__main__': unittest.main()
