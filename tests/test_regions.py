"""Boundary metadata supports overlaps, stable identities and stale-source rejection."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from jorvik.regions import put_region, validate_regions, region_snapshot
from jorvik.geometry import load_geometry
from jorvik.project import save_project, load_project
from test_project import state

FIXTURE = Path(__file__).resolve().parents[1] / 'examples/geometries/cfdbench/annulus_unstructured.geo'


class RegionsTest(unittest.TestCase):
    def test_assign_rename_overlap_and_snapshot(self):
        geometry = load_geometry(FIXTURE)
        regions = put_region([], geometry, 'wall / 壁', [[1, 1], [1, 2]], '#ffc857')
        original = deepcopy(regions)
        snapshot = region_snapshot(regions, geometry, regions[0]['id'])
        regions = put_region(regions, geometry, 'shared', [[1, 2], [1, 3]], '#123456')
        renamed = put_region(regions, geometry, 'new name', [[1, 1], [1, 4]], '#abcdef', regions[0]['id'])
        self.assertEqual(renamed[0]['id'], original[0]['id'])
        self.assertEqual(snapshot, original[0])
        self.assertEqual(regions[0], original[0])
        for label, entities, colour in [('', [[1,1]], '#abcdef'), ('shared', [[1,1]], '#abcdef'),
                                       ('mixed', [[1,1],[2,1]], '#abcdef'), ('missing', [[1,99]], '#abcdef'),
                                       ('empty', [], '#abcdef'), ('colour', [[1,1]], 'bad')]:
            with self.subTest(label=label), self.assertRaises(ValueError):
                put_region(regions, geometry, label, entities, colour)
        changed = dict(geometry, source_hash='different')
        with self.assertRaisesRegex(ValueError, 'changed geometry'):
            region_snapshot(regions, changed, regions[0]['id'])
        with self.assertRaisesRegex(ValueError, 'no longer exists'):
            region_snapshot(regions, geometry, 'removed')
        self.assertEqual(regions[0], original[0])

    def test_project_region_references_and_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'annulus.geo'; source.write_bytes(FIXTURE.read_bytes())
            geometry = load_geometry(source)
            regions = put_region([], geometry, 'wall', [[1,1],[1,2]], '#abcdef')
            saved = state(); saved['selected_area'] = None; saved['boundary_regions'] = regions
            saved['controls']['target'] = {'region_id': regions[0]['id']}
            project = Path(directory) / 'regions.gsproj'
            save_project(project, geometry, [], saved)
            manifest, _ = load_project(project)
            self.assertEqual(manifest['state']['boundary_regions'], regions)
            before = project.read_bytes()
            source.write_text(source.read_text() + '\n// changed source')
            with self.assertRaisesRegex(ValueError, 'changed'):
                save_project(project, geometry, [], saved)
            self.assertEqual(project.read_bytes(), before)
            source.write_bytes(FIXTURE.read_bytes())
            bad = deepcopy(saved); bad['boundary_regions'][0]['entities'] = [[1,999]]
            with self.assertRaisesRegex(ValueError, 'missing'):
                save_project(project, geometry, [], bad)
            bad = deepcopy(saved); bad['controls']['target'] = {'region_id': 'removed'}
            save_project(project, geometry, [], bad)
            with self.assertRaisesRegex(ValueError, 'missing boundary region'):
                load_project(project)
