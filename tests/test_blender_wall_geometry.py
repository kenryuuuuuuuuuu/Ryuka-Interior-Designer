"""Regression checks for phantom zone walls and clipped/cross-zone openings."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from wall_geometry import exterior_wall_panels, opening_plane, wall_segments


class WallGeometryTests(unittest.TestCase):
    def test_subtraction_and_clipping(self):
        self.assertEqual(wall_segments(0, 10, 0, 3, [(3, 7, 0, 3)]),
                         [(0, 3, 0, 3), (7, 10, 0, 3)])
        self.assertEqual(wall_segments(0, 10, 0.707, 2.4,
                                       [(-2, 20, -1, 4)]), [])
        self.assertEqual(wall_segments(0, 10, 0, 3, [(11, 12, 0, 3)]),
                         [(0, 10, 0, 3)])

    def test_cross_zone_window_cuts_both_segments(self):
        data = dict(footprints=[dict(level=1, x0=0, x1=5, z0=0, z1=3),
                                dict(level=1, x0=5, x1=10, z0=0, z1=3)],
                    exteriorWalls=[dict(id=str(i), level=1, orientation='H',
                                        x0=a, x1=b, z0=3, z1=3)
                                   for i, (a, b) in enumerate([(0, 5), (5, 10)])],
                    openings=[dict(level=1, face='S', offset=4, width=2, sill=1, height=1)],
                    levels=dict(fl1=0.707), defaults=dict(ceilingHeight=3))
        panels = exterior_wall_panels(data)
        area = sum((p['end']-p['start'])*(p['top']-p['bottom']) for p in panels)
        self.assertAlmostEqual(area, 28)
        for x in (4.5, 5.5):
            self.assertFalse(any(p['start'] < x < p['end'] and
                                 p['bottom'] < 2.207 < p['top'] for p in panels))

    def test_repository_external_walls_and_second_floor(self):
        read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))
        data = read('data/house.json')
        data['exteriorWalls'] = read('generated/exterior-walls.json')['walls']
        catalogs = read('data/door-catalog.json')['types'] + read('data/window-catalog.json')['types']
        by_type = {t['type']: t for t in catalogs}
        data['openings'] = []
        for item in read('data/openings.json')['items']:
            resolved = dict(item)
            for field in ('width', 'height', 'sill'):
                resolved[field] = item.get(field + 'Override', by_type[item['type']][field])
            data['openings'].append(resolved)
        panels = exterior_wall_panels(data)
        # A1/A2 share x=9.1 south of z=.91: this must never become an exterior wall.
        self.assertFalse(any(p['wall']['level'] == 1 and p['wall']['orientation'] == 'V'
                             and abs(p['at']-9.1) < 1e-6 and p['end'] > .91 + 1e-6
                             for p in panels))
        # Each real opening's in-wall portion must be absent in every matching panel.
        for o in data['openings']:
            orientation, at = opening_plane(data, o)
            for p in panels:
                if p['wall']['level'] != o['level'] or p['wall']['orientation'] != orientation or abs(p['at']-at) > 1e-6:
                    continue
                base = data['levels'][f"fl{o['level']}"]
                dx = min(p['end'], o['offset']+o['width']) - max(p['start'], o['offset'])
                dy = min(p['top'], base+o['sill']+o['height']) - max(p['bottom'], base+o['sill'])
                self.assertFalse(dx > 1e-6 and dy > 1e-6, o['id'])
        west = [o for o in data['openings'] if o['level'] == 2 and o['face'] == 'W']
        self.assertTrue(west)
        for o in west:
            self.assertEqual(opening_plane(data, o), ('V', 12.74))


if __name__ == '__main__':
    unittest.main()
