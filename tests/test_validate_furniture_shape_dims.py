"""W08-H regression: tests/validate_furniture.py used to only range-check
STORAGE_SHAPES overrides (closetSingle/closetDouble/closetShelves/...). A
wall-plank-shelf (ENTRY_SHAPES) placed through the Web editor with
depthOverride=0.15 (below wallPlankShelf's 0.22-0.4m range) slipped past this
validator -- and past the guest launcher's import, which calls the same
validate() -- and only failed much later, as an UNCAUGHT exception inside
Three.js's unguarded furniture-build loop, blanking the whole viewer.

This asserts the validator now catches an out-of-range override for a
LAUNDRY_SHAPES and an ENTRY_SHAPES type, exactly like it already did for
STORAGE_SHAPES, so a bad import is rejected at the door instead of crashing
the viewer downstream.
"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('furniture_validator', ROOT/'tests/validate_furniture.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ShapeDimensionValidation(unittest.TestCase):
    def _run_with(self, mutate):
        original = json.loads((ROOT/'data/furniture.json').read_text(encoding='utf-8'))
        catalog = json.loads((ROOT/'data/furniture-catalog.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'furniture.json'
            data = json.loads(json.dumps(original))
            mutate(data, catalog)
            path.write_text(json.dumps(data), encoding='utf-8')
            with patch.object(validator, 'FURNITURE', path), contextlib.redirect_stdout(io.StringIO()):
                validator.main()

    def test_entry_shape_out_of_range_depth_is_rejected(self):
        def mutate(data, catalog):
            hook_type = next(t for t in catalog['types'] if t['shape'] == 'wallPlankShelf')
            data['items'].append(dict(id='test-bad-plank-shelf', type=hook_type['type'],
                room='room-1f-12', level=1, x=15.89, z=1.3, rotation=270,
                depthOverride=0.15, status='estimated'))
        with self.assertRaises(AssertionError) as ctx:
            self._run_with(mutate)
        self.assertIn('対応範囲外', str(ctx.exception))

    def test_laundry_shape_out_of_range_width_is_rejected(self):
        def mutate(data, catalog):
            counter_type = next(t for t in catalog['types'] if t['shape'] == 'laundryCounter')
            data['items'].append(dict(id='test-bad-laundry-counter', type=counter_type['type'],
                room='room-1f-16', level=1, x=16.0, z=5.0, rotation=0,
                widthOverride=3.5, status='estimated'))
        with self.assertRaises(AssertionError) as ctx:
            self._run_with(mutate)
        self.assertIn('対応範囲外', str(ctx.exception))

    def test_valid_entry_and_laundry_overrides_pass(self):
        def mutate(data, catalog):
            pass  # the live repo data must already validate on its own
        self._run_with(mutate)  # must not raise


if __name__ == '__main__':
    unittest.main()
