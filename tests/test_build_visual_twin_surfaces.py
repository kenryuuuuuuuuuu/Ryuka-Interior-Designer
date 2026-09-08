"""W03-C: build-visual-twin.py's --interior preflight for the surface
registry, and that surface-registry.json is included in the package's input
hashing/copy (SourcePackage/inputs/) alongside the rest of data/."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_visual_twin',ROOT/'scripts/build-visual-twin.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class BuildVisualTwinSurfaceTests(unittest.TestCase):
    def test_inputs_includes_surface_registry(self):
        before=m.inputs()
        self.assertIn('data/visual/surface-registry.json',before)

    def test_interior_stops_before_blender_when_surfaces_unresolved(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        output=Path(temp.name)/'package'
        blender=Path(temp.name)/'blender.exe'; blender.touch()
        argv=['build-visual-twin','--blender',str(blender),'--output',str(output),'--interior']
        with mock.patch.object(m.sys,'argv',argv),\
             mock.patch.object(m.shutil,'which',return_value='node'),\
             mock.patch.object(m,'run',return_value='ok') as run,\
             mock.patch.object(m,'resolve_surfaces',return_value=dict(issues=[dict(id='surf-x',reason='moved',guidance='update it')])) as resolve:
            with self.assertRaises(SystemExit):
                m.main()
        resolve.assert_called_once()
        self.assertEqual(run.call_count,7)  # the 7 pre-checks (node + 6 validators) still ran; Blender staging never started
        self.assertFalse(output.exists())

    def test_non_interior_build_never_checks_surfaces(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        output=Path(temp.name)/'package'
        blender=Path(temp.name)/'blender.exe'; blender.touch()
        argv=['build-visual-twin','--blender',str(blender),'--output',str(output)]
        with mock.patch.object(m.sys,'argv',argv),\
             mock.patch.object(m.shutil,'which',return_value='node'),\
             mock.patch.object(m,'run',return_value='ok'),\
             mock.patch.object(m,'resolve_surfaces',side_effect=AssertionError('must not be called')) as resolve,\
             mock.patch.object(m.subprocess,'run',return_value=type('R',(),{'stdout':'v1.0'})()),\
             mock.patch.object(m,'inputs',return_value={'x':'a'}):
            try: m.main()
            except Exception: pass  # staging will fail on the fake blender.exe; irrelevant here
        resolve.assert_not_called()


if __name__=='__main__': unittest.main()
