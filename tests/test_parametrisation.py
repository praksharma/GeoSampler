"""Translation, independent regions, reproducible setup and export round trips."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import xarray as xr
from test_export import batch
from jorvik.parametrisation import (transform_batches, validate_setup, save_setup,
                                        load_setup, export_configuration)


def setup(scope='domain', regions=None):
    return {'schema_version': 1, 'scope': scope, 'regions': regions or [],
            'translation': [2., -3., .5], 'source_hash': 'abc123'}


class ParametrisationTest(unittest.TestCase):
    def test_translation_from_originals_and_region_scope(self):
        batches = [batch(), batch('interior', 7, 1)]
        batches[0]['normals'] = [[0., 0., 1.]] * 3
        originals = deepcopy(batches)
        for _ in range(2):
            transformed = transform_batches(batches, setup())
            for old, new in zip(batches, transformed):
                np.testing.assert_array_equal(new['coordinates'], np.asarray(old['coordinates']) + [2,-3,.5])
                self.assertEqual(new['entity_tags'],old['entity_tags'])
        self.assertEqual(transformed[0]['normals'],batches[0]['normals'])
        transformed = transform_batches(batches, setup('regions',['boundary']))
        self.assertEqual(transformed[1]['coordinates'],batches[1]['coordinates'])
        self.assertEqual(transformed[0]['parametrisation']['domain_consistency'],'unverified')
        self.assertEqual(batches, originals)

    def test_validation_and_setup_round_trip(self):
        invalid = [dict(setup(), translation=[float('nan'),0,0]),
                   dict(setup(), translation=[1,2]), dict(setup(), scope='bad'),
                   setup('regions'), setup('regions',['missing']),
                   dict(setup(), source_hash='different'), dict(setup(), schema_version=2)]
        for config in invalid:
            with self.assertRaises(ValueError): validate_setup(config,[batch()])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'setup.json'
            save_setup(setup('regions',['boundary']),path)
            self.assertEqual(load_setup(path),setup('regions',['boundary']))
            self.assertNotIn('coordinates',path.read_text())
            before=path.read_bytes()
            with patch('pathlib.Path.write_text',side_effect=OSError('Disk full')):
                with self.assertRaises(OSError):save_setup(setup(),path)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_configuration_exports(self):
        batches=[batch('wall / arbitrary'), batch('interior',7,1)]
        config=setup('regions',['wall / arbitrary'])
        expected=transform_batches(batches,config)
        with tempfile.TemporaryDirectory() as directory:
            for extension in ('nc','npz'):
                path=Path(directory)/f'translated.{extension}'
                export_configuration(batches,config,path)
                if extension=='nc':
                    with xr.open_dataset(path,engine='scipy') as data:
                        manifest=json.loads(data.attrs['metadata_json'])
                        np.testing.assert_array_equal(data['_gs_translation'],config['translation'])
                        self.assertEqual(data['_gs_parameter'].values.tolist(),['translation_x','translation_y','translation_z'])
                        for record, original in zip(manifest['datasets'],expected):
                            np.testing.assert_array_equal(data[record['array']],original['coordinates'])
                else:
                    with np.load(path,allow_pickle=False) as data:
                        manifest=json.loads(data['_gs_metadata'].item())
                        np.testing.assert_array_equal(data['_gs_translation'],config['translation'])
                        for record, original in zip(manifest['datasets'],expected):
                            np.testing.assert_array_equal(data[record['array']],original['coordinates'])
                self.assertEqual(manifest['parametrisation'],config)
                before=path.read_bytes()
                writer='xarray.Dataset.to_netcdf' if extension=='nc' else 'numpy.savez_compressed'
                with patch(writer,side_effect=OSError('Disk full')):
                    with self.assertRaises(OSError):export_configuration(batches,config,path)
                self.assertEqual(before,path.read_bytes())
