import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('furniture_validator', ROOT/'tests/validate_furniture.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ElevationValidation(unittest.TestCase):
    def test_invalid_values_rejected_and_legacy_accepted(self):
        original = json.loads((ROOT/'data/furniture.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'furniture.json'
            for value in [-0.01, True, '1.0', None, float('inf'), float('nan'), 0, 1.2]:
                with self.subTest(value=value):
                    data = json.loads(json.dumps(original))
                    data['items'][0]['elevation'] = value
                    path.write_text(json.dumps(data), encoding='utf-8')
                    with patch.object(validator, 'FURNITURE', path), contextlib.redirect_stdout(io.StringIO()):
                        if type(value) in (int, float) and value in (0, 1.2):
                            validator.main()
                        else:
                            with self.assertRaises(AssertionError): validator.main()
            for item in original['items']: item.pop('elevation', None)
            path.write_text(json.dumps(original), encoding='utf-8')
            with patch.object(validator, 'FURNITURE', path), contextlib.redirect_stdout(io.StringIO()):
                validator.main()
