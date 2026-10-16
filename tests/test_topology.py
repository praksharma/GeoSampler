"""Original CAD topology across both script kernels and portable projects."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
from geosampler.geometry import load_geometry
from geosampler.project import save_project, load_project
from geosampler.sampling import sample_geometry
from test_project import state

# Original test geometry: the same explicit construction works in both kernels.
CUBE = """
Point(1)={0,0,0,.4}; Point(2)={1,0,0,.4};
Point(3)={1,1,0,.4}; Point(4)={0,1,0,.4};
Line(1)={1,2}; Line(2)={2,3}; Line(3)={3,4}; Line(4)={4,1};
Curve Loop(1)={1,2,3,4}; Plane Surface(1)={1};
Extrude {0,0,1} { Surface{1}; }
Physical Volume("domain") = Volume{:}; Physical Surface("walls") = Surface{:};
Physical Curve("edges") = Curve{:}; Physical Point("corners") = Point{:};
"""


class TopologyTest(unittest.TestCase):
    def cube(self, directory, kernel='Built-in'):
        path = Path(directory) / 'cube.geo'
        path.write_text(f'SetFactory("{kernel}");\n' + CUBE)
        return load_geometry(path)

    def test_both_kernels_topology_sampling_and_project_round_trip(self):
        for kernel in ('Built-in', 'OpenCASCADE'):
            with self.subTest(kernel=kernel), tempfile.TemporaryDirectory() as directory:
                geometry = self.cube(directory, kernel)
                self.assertEqual(geometry['source_format'], 'geo')
                self.assertEqual(geometry['solid_count'], 1)
                topology = {(e['dimension'], e['tag']): e for e in geometry['topology']}
                self.assertEqual([sum(d == dim for d, _ in topology) for dim in range(4)], [8, 12, 6, 1])
                for (dim, tag), entity in topology.items():
                    self.assertNotIn('positions', entity)
                    self.assertEqual(len(entity['boundary']), (0, 2, 4, 6)[dim])
                    self.assertEqual(len(entity['upward']), (3, 2, 1, 0)[dim])
                    self.assertEqual(len(entity['groups']), 1)
                    for ref in entity['boundary']:
                        self.assertIn([dim, tag], topology[tuple(ref)]['upward'])
                    for ref in entity['upward']:
                        self.assertIn([dim, tag], topology[tuple(ref)]['boundary'])
                    bounds = np.asarray(entity['bounds'])
                    self.assertTrue(np.isfinite(bounds).all())
                    self.assertTrue((bounds[:3] <= bounds[3:]).all())
                self.assertEqual(len(geometry['entities']), 18)
                # Original faces and edges remain sampling targets in both kernels.
                for dim in (1, 2, 3):
                    tag = next(tag for d, tag in topology if d == dim)
                    request = {k: geometry[k] for k in ('source', 'source_hash', 'document')}
                    request.update(target='interior' if dim == 3 else 'selection', entities=[[dim, tag]],
                                   label='test', method='sobol', count=16, seed=7, resolution=16)
                    sampled = sample_geometry(request)
                    self.assertEqual(sampled['count'], 16)
                    self.assertEqual(sampled['entity_dimension'], dim)
                    self.assertEqual(set(sampled['entity_tags']), {tag})
                    points = np.asarray(sampled['coordinates'])
                    self.assertTrue((points >= -1e-6).all() and (points <= 1 + 1e-6).all())
                    if dim < 3:
                        self.assertTrue(np.any(np.isclose(points, 0) | np.isclose(points, 1), axis=1).all())
                project_state = state()
                project_state['selected_area'] = None
                path = Path(directory) / 'cube.gsproj'
                save_project(path, geometry, [], project_state)
                restored, _ = load_project(path)
                self.assertEqual(restored['geometry'], geometry)
                # Legacy projects stay readable; no invented topology is added.
                legacy = deepcopy(geometry)
                del legacy['topology']
                save_project(path, legacy, [], project_state)
                restored, _ = load_project(path)
                self.assertEqual(restored['geometry'], legacy)
                self.assertNotIn('topology', restored['geometry'])

    def test_construction_vertices_and_open_surface(self):
        fixture = Path(__file__).resolve().parents[1] / 'examples/geometries/cfdbench/annulus_unstructured.geo'
        geometry = load_geometry(fixture)
        topology = {(e['dimension'], e['tag']): e for e in geometry['topology']}
        self.assertEqual([sum(d == dim for d, _ in topology) for dim in range(4)], [10, 8, 1, 0])
        # Circle centres are original construction entities, not edge endpoints.
        self.assertEqual(topology[(0, 5)]['upward'], [])
        self.assertEqual(topology[(0, 10)]['upward'], [])
        self.assertEqual(topology[(2, 1)]['upward'], [])
        self.assertEqual(topology[(2, 1)]['boundary'], [[1, tag] for tag in range(1, 9)])

    def test_corrupt_project_topology_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            geometry = self.cube(directory)
            project_state = state()
            project_state['selected_area'] = None
            path = Path(directory) / 'cube.gsproj'
            save_project(path, geometry, [], project_state)
            with zipfile.ZipFile(path) as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            original = json.loads(files['manifest.json'])
            cases = ('missing reference', 'nonreciprocal', 'duplicate', 'bounds', 'display', 'solid count')
            for case in cases:
                with self.subTest(case=case):
                    manifest = deepcopy(original)
                    model = manifest['geometry']
                    records = model['topology']
                    if case == 'missing reference':
                        records[0]['upward'].append([1, 999999])
                    elif case == 'nonreciprocal':
                        records[0]['upward'] = []
                    elif case == 'duplicate':
                        records.append(deepcopy(records[0]))
                    elif case == 'bounds':
                        records[0]['bounds'] = [1, 0, 0, -1, 0, 0]
                    elif case == 'display':
                        records[:] = [e for e in records if e['dimension'] != 2]
                    else:
                        model['solid_count'] = 99
                    with zipfile.ZipFile(path, 'w') as archive:
                        for name, data in files.items():
                            archive.writestr(name, json.dumps(manifest) if name == 'manifest.json' else data)
                    with self.assertRaisesRegex(ValueError, '[Tt]opology'):
                        load_project(path)
