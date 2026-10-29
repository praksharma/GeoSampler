"""Online CAD fixtures: topology, boundary/volume sampling and exported provenance."""
from pathlib import Path
import json
import hashlib
import tempfile
import unittest
import numpy as np
import xarray as xr
from jorvik.geometry import load_geometry
from jorvik.sampling import sample_geometry
from jorvik.export import export_samples
from jorvik.cad_import import open_source

FIXTURES=Path(__file__).resolve().parents[1]/'examples/geometries/cad'


class CadImportTest(unittest.TestCase):
    def test_downloaded_files_and_cad_workflow(self):
        manifest=json.loads((FIXTURES/'provenance.json').read_text())
        for record in manifest['files']:
            self.assertEqual(hashlib.sha256((FIXTURES/record['file']).read_bytes()).hexdigest(),record['sha256'])
        for name,kind,solid_count in [('t20_data.step','step',1),('cube_filet.stp','step',0),('cylinder.brep','brep',1),('cube1000.igs','iges',0)]:
            with self.subTest(name=name):
                geometry=load_geometry(FIXTURES/name)
                self.assertEqual(geometry['source_format'],kind)
                self.assertEqual(geometry['import_options']['loader'], 'occ.importShapes')
                self.assertEqual(geometry['import_options']['format'], kind)
                self.assertIs(geometry['import_options']['highest_dim_only'], False)
                self.assertEqual(geometry['solid_count'],solid_count)
                self.assertTrue(any(e['dimension']==2 for e in geometry['entities']))
                topology = {(e['dimension'], e['tag']): e for e in geometry['topology']}
                self.assertEqual(sum(d == 3 for d, _ in topology), solid_count)
                self.assertTrue(any(d == 0 for d, _ in topology))
                for entity in geometry['entities']:
                    original = topology[(entity['dimension'], entity['tag'])]
                    self.assertEqual(original['type'], entity['type'])
                    self.assertEqual(original['name'], entity['name'])
                    self.assertEqual(original['groups'], entity['groups'])
                    for ref in original['boundary']:
                        self.assertIn([entity['dimension'], entity['tag']], topology[tuple(ref)]['upward'])
                batches=[]
                for dimension in (2,1):
                    entity=next(e for e in geometry['entities'] if e['dimension']==dimension and not e['degenerate'])
                    request={k:geometry[k] for k in ('source','source_hash','document')}
                    request.update(target='selection', entities=[[dimension,entity['tag']]], method='sobol',count=32,seed=42,label=f'region_{dimension}',resolution=16,compute_mode='multicore',cpu_threads=2)
                    sampled=sample_geometry(request)
                    self.assertEqual(sampled['count'],32)
                    self.assertEqual(set(sampled['entity_tags']),{entity['tag']})
                    self.assertTrue(np.isfinite(sampled['coordinates']).all())
                    self.assertEqual(sampled['source_format'],kind)
                    self.assertEqual(sampled['import_options'], geometry['import_options'])
                    batches.append(sampled)
                request.update(target='interior',entities=[],label='interior')
                if solid_count:
                    interior=sample_geometry(request)
                    self.assertEqual(interior['entity_dimension'],3)
                    batches.append(interior)
                else:
                    with self.assertRaisesRegex(ValueError,'solid volumes'):
                        sample_geometry(request)
                with tempfile.TemporaryDirectory() as directory:
                    path=export_samples(batches,Path(directory)/'cad.nc')
                    with xr.open_dataset(path,engine='scipy') as exported:
                        for batch in batches:
                            np.testing.assert_array_equal(exported[batch['label']],batch['coordinates'])
                            self.assertEqual(json.loads(exported[batch['label']].attrs['metadata_json'])['source_format'],kind)
                degenerate=next((e for e in geometry['entities'] if e['degenerate']),None)
                if degenerate:
                    request.update(target='selection',entities=[[1,degenerate['tag']]])
                    with self.assertRaisesRegex(ValueError,'degenerate CAD edge'):
                        sample_geometry(request)

    def test_unsupported_and_malformed_sources(self):
        with self.assertRaisesRegex(ValueError,'Choose a Gmsh'):
            open_source(None,'model.stl')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.step';path.write_text('not a CAD model')
            with self.assertRaises(Exception):load_geometry(path)
