"""Candidate checks must happen before replacing the building source."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.guest_launcher import source_import


class SourceImportTests(unittest.TestCase):
    def candidate(self, kind, mutate):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/(kind+'.json')
            doc=json.loads((ROOT/'data'/(kind+'.json')).read_text(encoding='utf-8'))
            mutate(doc)
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
            return source_import.build_report(kind,path)

    def test_all_three_current_sources_validate_as_no_change(self):
        for kind in source_import.KINDS:
            report=source_import.build_report(kind,ROOT/'data'/(kind+'.json'))
            self.assertTrue(report.ok,report.error)
            self.assertEqual(report.changes,[])

    def test_opening_deletion_referenced_by_decor_is_rejected(self):
        decor=json.loads((ROOT/'data/visual/guest-decor.json').read_text(encoding='utf-8'))
        referenced={i['openingId'] for i in decor['items'] if 'openingId' in i}
        self.assertTrue(referenced)
        report=self.candidate('openings',lambda d:d['items'].__setitem__(slice(None),
            [i for i in d['items'] if i['id'] not in referenced]))
        self.assertFalse(report.ok)
        self.assertIn('装飾',report.error)

    def test_electrical_deletion_referenced_by_lighting_group_is_rejected(self):
        group=json.loads((ROOT/'data/visual/lighting-settings.json').read_text(encoding='utf-8'))['groups'][0]
        target=group['fixtureIds'][0]
        report=self.candidate('electrical',lambda d:d['items'].__setitem__(slice(None),
            [i for i in d['items'] if i['id']!=target]))
        self.assertFalse(report.ok)
        self.assertIn('照明グループ',report.error)

    def test_wrong_export_kind_is_rejected_before_write(self):
        report=source_import.build_report('electrical',ROOT/'data/openings.json')
        self.assertFalse(report.ok)

    def test_changed_candidate_after_preview_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'interior-doors.json'
            doc=json.loads((ROOT/'data/interior-doors.json').read_text(encoding='utf-8'))
            doc['items'][0]['label']='preview label'
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
            report=source_import.build_report('interior-doors',path)
            self.assertTrue(report.ok,report.error)
            doc['items'][0]['label']='changed after preview'
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'差分確認後'):
                source_import.apply(report)


if __name__=='__main__':
    unittest.main()
