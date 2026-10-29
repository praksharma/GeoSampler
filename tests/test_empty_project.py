"""Geometry-free documents, exclusive creation, legacy formats and validation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from jorvik.project import create_empty_project, save_project, load_project
from jorvik.geometry import load_geometry
from test_project import FIXTURE, state


def rewrite_manifest(path, change):
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(members['manifest.json'])
    change(manifest)
    members['manifest.json'] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in members.items(): archive.writestr(name, data)


class EmptyProjectTest(unittest.TestCase):
    def test_empty_round_trip_and_exclusive_creation_without_qt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'empty.gsproj'
            code = """import sys
from jorvik.project import create_empty_project
create_empty_project(sys.argv[1])
assert not any(name.startswith(('PySide6', 'PyQt')) for name in sys.modules)
"""
            result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest, source = load_project(path)
            self.assertEqual(manifest, {'schema_version': 3, 'geometry': None, 'areas': [],
                                        'state': {}, 'source_extension': None})
            self.assertIsNone(source)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): create_empty_project(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])
            self.assertEqual(create_empty_project(path, overwrite=True), path)
            save_project(path, None, [], {})
            self.assertEqual(load_project(path)[0], manifest)
            with self.assertRaisesRegex(ValueError, '.gsproj'):
                create_empty_project(Path(directory) / 'wrong.nc')

    def test_empty_documents_reject_geometry_references(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'empty.gsproj'
            for field, value in [('areas', [{}]), ('state', {'selection': [[2, 1]]}),
                                 ('source_extension', '.geo'), ('geometry', {})]:
                with self.subTest(field=field):
                    create_empty_project(path, overwrite=True)
                    rewrite_manifest(path, lambda m: m.update({field: value}))
                    with self.assertRaises((ValueError, KeyError)): load_project(path)
            create_empty_project(path, overwrite=True)
            before = path.read_bytes()
            for areas, saved_state in [([{}], {}), ([], {'selection': [[2, 1]]})]:
                with self.assertRaises(ValueError): save_project(path, None, areas, saved_state)
                self.assertEqual(path.read_bytes(), before)
            with zipfile.ZipFile(path, 'a') as archive: archive.writestr('source/model.geo', 'Box(1) = {};')
            with self.assertRaisesRegex(ValueError, 'empty project'): load_project(path)

    def test_existing_versions_and_populated_validation(self):
        geometry = load_geometry(FIXTURE)
        saved_state = state(); saved_state['selected_area'] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'populated.gsproj'
            for version in (1, 2):
                save_project(path, geometry, [], saved_state)
                rewrite_manifest(path, lambda m: m.update(schema_version=version))
                manifest, source = load_project(path)
                self.assertEqual(manifest['geometry'], geometry)
                self.assertEqual(source, FIXTURE.read_bytes())
            rewrite_manifest(path, lambda m: m['geometry'].update(source_hash='corrupt'))
            with self.assertRaisesRegex(ValueError, 'checksum'): load_project(path)
