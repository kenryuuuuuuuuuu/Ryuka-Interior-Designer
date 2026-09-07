import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from finish_settings import details_for_variant,validate_finishes


class SurfaceFinishes(unittest.TestCase):
    def setUp(self):
        self.source=json.loads((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8'))

    def test_existing_roles_preserved_and_reference_overrides(self):
        for variant in ('natural','warm'):
            self.assertEqual(details_for_variant(self.source,variant),self.source['roles'])
        reference=details_for_variant(self.source,'reference')
        self.assertEqual(reference['floor']['pattern']['widthCm'],60)
        self.assertEqual(reference['ceiling']['pattern']['widthCm'],10)
        for role in ('wall','wood','cabinet','fabric'):
            self.assertEqual(reference[role],self.source['roles'][role])

    def test_invalid_dimensions_and_provenance(self):
        for key,value in [('widthCm',0),('lengthCm',float('inf')),('seamCm',True),('rotationDeg',-1),('kind','unknown')]:
            doc=copy.deepcopy(self.source)
            doc['variantOverrides']['reference']['floor']['pattern'][key]=value
            with self.assertRaises(ValueError):validate_finishes(doc)
        doc=copy.deepcopy(self.source);doc['variantOverrides']['reference']['ceiling']['note']=''
        with self.assertRaises(ValueError):validate_finishes(doc)
