"""An open 3D shell must never silently become a 2D interior dataset."""
from pathlib import Path
import tempfile
import unittest
from jorvik.geometry import load_geometry
from jorvik.sampling import sample_geometry

FIXTURES=Path(__file__).resolve().parents[1]/'examples/geometries/cfdbench'


def interior(geometry):
    request={k:geometry[k] for k in ('source','source_hash','document')}
    request.update(label='interior',target='interior',entities=[],method='sobol',count=16,seed=42,resolution=16)
    return sample_geometry(request)


class DomainsTest(unittest.TestCase):
    def test_open_sphere_rejected_but_boundary_sampling_remains_available(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'open.geo'
            source.write_text((FIXTURES/'sphere_unstructured.geo').read_text().replace('Volume(1)={1};','').replace('Physical Volume(100)={1};',''))
            geometry=load_geometry(source)
            self.assertEqual(geometry['interior_domain'],'open_or_nonplanar')
            self.assertEqual(geometry['dimension'],3)
            with self.assertRaisesRegex(ValueError,'closed solid'):interior(geometry)
            request={k:geometry[k] for k in ('source','source_hash','document')}
            request.update(label='boundary',target='selection',entities=[[2,1]],method='sobol',count=16,seed=42,resolution=16)
            batch=sample_geometry(request)
            self.assertEqual(batch['count'],16)
            self.assertEqual(batch['normal_status'],'unavailable')

    def test_planar_annulus_and_declared_solid_keep_their_dimensions(self):
        annulus=load_geometry(FIXTURES/'annulus_unstructured.geo')
        self.assertEqual(annulus['interior_domain'],'planar')
        self.assertEqual(interior(annulus)['entity_dimension'],2)
        sphere=load_geometry(FIXTURES/'sphere_unstructured.geo')
        self.assertEqual(sphere['interior_domain'],'solid')
        self.assertEqual(interior(sphere)['entity_dimension'],3)

    def test_disconnected_planes_at_different_heights_are_not_one_2d_domain(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'planes.geo'
            source.write_text('SetFactory("OpenCASCADE");\nRectangle(1)={0,0,0,1,1};\nRectangle(2)={0,0,1,1,1};\n')
            geometry=load_geometry(source)
            self.assertEqual(geometry['interior_domain'],'open_or_nonplanar')
            with self.assertRaisesRegex(ValueError,'closed solid'):interior(geometry)
