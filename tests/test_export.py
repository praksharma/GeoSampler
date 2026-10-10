"""Round-trip variable lengths, geometry metadata, names and failed saves."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import xarray as xr

from geosampler.export import export_samples, to_xarray


def batch(label='boundary', count=3, tag=6):
    return {'label': label, 'count': count, 'requested_count': count,
            'coordinates': [[i / 10, i / 20, 0.] for i in range(count)],
            'entity_tags': [tag] * count, 'entity_dimension': 2,
            'entities': [[2, tag]], 'document': 'sphere-document',
            'source': '/geometry/sphere.geo', 'source_hash': 'abc123',
            'target': 'selection', 'method': 'sobol', 'seed': 42,
            'resolution': 32, 'notes': ['Numerically approximated boundary.']}


class ExportTest(unittest.TestCase):
    def test_netcdf_round_trip_without_padding(self):
        batches = [batch(), batch('boundary_1', 7, 1)]
        with tempfile.TemporaryDirectory() as directory:
            path = export_samples(batches, Path(directory) / 'samples.nc')
            with xr.open_dataset(path, engine='scipy') as dataset:
                self.assertEqual(set(dataset.data_vars), {'boundary', 'boundary_1'})
                self.assertEqual(dataset.boundary.shape, (3, 3))
                self.assertEqual(dataset.boundary_1.shape, (7, 3))
                self.assertNotEqual(dataset.boundary.dims[0], dataset.boundary_1.dims[0])
                self.assertEqual(dataset.xyz.values.tolist(), ['x', 'y', 'z'])
                for original in batches:
                    array = dataset[original['label']]
                    np.testing.assert_array_equal(array.values, original['coordinates'])
                    np.testing.assert_array_equal(array.coords[array.attrs['entity_tags_coordinate']], original['entity_tags'])
                    metadata = json.loads(array.attrs['metadata_json'])
                    self.assertEqual(metadata, {k: v for k, v in original.items() if k not in ('coordinates', 'entity_tags')})

    def test_npz_round_trip_without_pickle(self):
        batches = [batch(), batch('interior', 5, 1)]
        with tempfile.TemporaryDirectory() as directory:
            path = export_samples(batches, Path(directory) / 'samples.npz')
            with np.load(path, allow_pickle=False) as arrays:
                metadata = json.loads(arrays['_gs_metadata'].item())
                self.assertEqual(arrays['xyz'].tolist(), ['x', 'y', 'z'])
                for record, original in zip(metadata['datasets'], batches):
                    np.testing.assert_array_equal(arrays[record['array']], original['coordinates'])
                    np.testing.assert_array_equal(arrays[record['entity_tags']], original['entity_tags'])
                    self.assertEqual(record['metadata']['source_hash'], original['source_hash'])
                    self.assertFalse(arrays[record['array']].dtype.hasobject)

    def test_arbitrary_and_reserved_labels(self):
        labels = ['inlet patch', 'xyz', 'file', 'allow_pickle', '_gs_points_0', '壁/面']
        batches = [batch(label) for label in labels]
        with tempfile.TemporaryDirectory() as directory:
            for extension in ('nc', 'npz'):
                path = export_samples(batches, Path(directory) / f'labels.{extension}')
                if extension == 'nc':
                    with xr.open_dataset(path, engine='scipy') as dataset:
                        self.assertEqual([a.attrs['label'] for a in dataset.data_vars.values()], labels)
                else:
                    with np.load(path, allow_pickle=False) as arrays:
                        records = json.loads(arrays['_gs_metadata'].item())['datasets']
                        self.assertEqual([r['label'] for r in records], labels)
                        self.assertEqual(len({r['array'] for r in records}), len(labels))

    def test_invalid_data_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Generate samples'):
            to_xarray([])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            to_xarray([batch(), batch()])
        invalid = deepcopy(batch())
        invalid['coordinates'][0][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            to_xarray([invalid])
        invalid = deepcopy(batch())
        invalid['entity_tags'][0] = 99
        with self.assertRaisesRegex(ValueError, 'target entities'):
            to_xarray([invalid])
        invalid = batch('other')
        invalid['source_hash'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'same source'):
            to_xarray([batch(), invalid])

    def test_write_failure_preserves_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            for extension, writer in [('nc', 'xarray.Dataset.to_netcdf'), ('npz', 'numpy.savez_compressed')]:
                path = Path(directory) / f'samples.{extension}'
                path.write_bytes(b'existing contents')
                with patch(writer, side_effect=OSError('Disk full')):
                    with self.assertRaisesRegex(OSError, 'Disk full'):
                        export_samples([batch()], path)
                self.assertEqual(path.read_bytes(), b'existing contents')
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['samples.nc', 'samples.npz'])
