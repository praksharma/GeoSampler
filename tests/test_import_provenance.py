"""Trace actual loader settings through sampling, exports and portable projects."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
import xarray as xr

from jorvik.geometry import load_geometry
from jorvik.sampling import sample_geometry
from jorvik.export import export_samples, to_xarray
from jorvik.project import save_project, load_project
from test_project import FIXTURE, state


class ImportProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.geometry = load_geometry(FIXTURE)
        self.request = {key: self.geometry[key] for key in
                        ('source', 'source_hash', 'source_format', 'document', 'import_options')}
        self.request.update(label='wall', target='selection', entities=[[1, 1]],
                            method='sobol', count=8, seed=42)

    def test_round_trip_exports_and_project(self):
        batch = sample_geometry(self.request)
        options = self.geometry['import_options']
        self.assertEqual(options['loader'], 'open')
        self.assertFalse(options['read_config_files'])
        self.assertEqual(batch['import_options'], options)
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ('nc', 'npz'):
                path = export_samples([batch], Path(directory) / ('samples.' + suffix))
                if suffix == 'nc':
                    with xr.open_dataset(path, engine='scipy') as dataset:
                        metadata = json.loads(dataset.wall.attrs['metadata_json'])
                else:
                    with np.load(path, allow_pickle=False) as arrays:
                        metadata = json.loads(arrays['_gs_metadata'].item())['datasets'][0]['metadata']
                self.assertEqual(metadata['import_options'], options)
                self.assertEqual(metadata['source_hash'], self.geometry['source_hash'])
                self.assertEqual(metadata['source_format'], 'geo')
            path = Path(directory) / 'saved.gsproj'
            save_project(path, self.geometry, [(batch, 'Generated', True)], state())
            manifest, _ = load_project(path)
            self.assertEqual(manifest['geometry']['import_options'], options)
            self.assertEqual(manifest['areas'][0]['area']['import_options'], options)
            before = path.read_bytes()
            changed = deepcopy(batch)
            changed['import_options']['backend_version'] = 'other'
            with self.assertRaisesRegex(ValueError, 'differs'):
                save_project(path, self.geometry, [(changed, 'Generated', True)], state())
            self.assertEqual(path.read_bytes(), before)
            # Pending recipes retain the same metadata without point arrays.
            save_project(path, self.geometry, [(self.request, 'Not generated', True)], state())
            pending, _ = load_project(path)
            self.assertEqual(pending['areas'][0]['area']['import_options'], options)
            save_project(path, self.geometry, [(batch, 'Generated', True)], state())
            # Settings from an older importer must not be silently reused.
            with zipfile.ZipFile(path) as archive:
                members = {name: archive.read(name) for name in archive.namelist()}
            metadata = json.loads(members['manifest.json'])
            metadata['areas'][0]['area']['import_options']['backend_version'] = 'other'
            members['manifest.json'] = json.dumps(metadata).encode()
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in members.items(): archive.writestr(name, data)
            with self.assertRaisesRegex(ValueError, 'differs'):
                load_project(path)
            # Historical projects remain readable without invented settings.
            del metadata['geometry']['import_options']
            del metadata['areas'][0]['area']['import_options']
            members['manifest.json'] = json.dumps(metadata).encode()
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in members.items(): archive.writestr(name, data)
            manifest, _ = load_project(path)
            self.assertNotIn('import_options', manifest['geometry'])

    def test_changed_import_settings_and_source_rejected(self):
        changed = deepcopy(self.request)
        changed['import_options']['backend_version'] = 'other'
        with self.assertRaisesRegex(ValueError, 'import settings changed'):
            sample_geometry(changed)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'changed.geo'
            source.write_bytes(FIXTURE.read_bytes() + b'\n// modified')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                sample_geometry(dict(self.request, source=str(source)))

    def test_invalid_export_provenance(self):
        batch = sample_geometry(self.request)
        for field, value in [('source_format', 'stl'), ('import_options', []),
                             ('import_options', {'backend': 'other'})]:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    to_xarray([dict(batch, **{field: value})])
