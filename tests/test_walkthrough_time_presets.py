import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'unreal'))
from walkthrough_time_presets import build_presets


class WalkthroughTimePresetsTest(unittest.TestCase):
    def test_four_seasons_six_hours_and_date_extension(self):
        config = json.loads((ROOT / 'data/visual/walkthrough-time-presets.json').read_text(encoding='utf-8'))
        doc = build_presets(config['previewSite'], config['seasonDates'], config['hours'],
                            config['utcOffset'], synthetic=True)
        self.assertEqual(len(doc['presets']), 24)
        self.assertEqual([row['hour'] for row in doc['presets'][:6]], [9, 12, 15, 18, 21, 24])
        self.assertTrue(doc['synthetic'])
        self.assertEqual(len(doc['siteSHA256']), 64)
        self.assertEqual(doc['presets'][5]['localTimestamp'][:10], '2026-03-22')
        self.assertEqual(doc['presets'][5]['mode'], 'night')
        self.assertLess(doc['presets'][0]['elevationDeg'], doc['presets'][1]['elevationDeg'])
        custom = build_presets(config['previewSite'],
                               [{'id': 'custom', 'label': '指定日', 'date': '2027-02-14'}], [9, 24],
                               config['utcOffset'], synthetic=True)
        self.assertEqual(len(custom['presets']), 2)
        self.assertEqual(custom['presets'][0]['localTimestamp'][:10], '2027-02-14')


if __name__ == '__main__':
    unittest.main()
