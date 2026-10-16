"""Reproducible boundary/interior datasets, normals and xarray/NPZ loading.

Run from a checkout: uv run python examples/sample_annulus.py --output-dir <dir>
The entity assignments below apply specifically to the attributed annulus fixture.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import xarray as xr
from geosampler.geometry import load_geometry
from geosampler.regions import put_region, region_snapshot
from geosampler.sampling import sample_geometry
from geosampler.export import export_samples


def run(output_dir, count=128):
    geometry = load_geometry(Path(__file__).parent / 'geometries/cfdbench/annulus_unstructured.geo')
    regions = []
    for label, tags, colour in [('inner', range(1,5), '#ffc857'), ('outer', range(5,9), '#41c4b8')]:
        regions = put_region(regions, geometry, label, [[1,t] for t in tags], colour)
    batches = []
    for region in [*regions, None]:
        request = {key: geometry[key] for key in ('source', 'source_hash', 'document')}
        request.update(label=region['label'] if region else 'interior',
                       target='region' if region else 'interior',
                       entities=region['entities'] if region else [], method='sobol',
                       seed=42, count=count, resolution=32, compute_mode='reproducible', cpu_threads=1)
        if region:
            request['boundary_region'] = region_snapshot(regions, geometry, region['id'])
        batches.append(sample_geometry(request))
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    nc = export_samples(batches, output_dir / 'annulus.nc')
    npz = export_samples(batches, output_dir / 'annulus.npz')
    # Separate boundary/interior arrays are ready to feed a downstream ML pipeline.
    with xr.open_dataset(nc, engine='scipy') as dataset:
        training = {label: dataset[label].values.copy() for label in ('inner', 'outer', 'interior')}
        for label in ('inner', 'outer'):
            normal_key = dataset[label].attrs['normals_coordinate']
            training[label + '_normals'] = dataset[normal_key].values.copy()
            np.testing.assert_allclose(np.linalg.norm(training[label + '_normals'], axis=1), 1)
    with np.load(npz, allow_pickle=False) as arrays:
        manifest = json.loads(arrays['_gs_metadata'].item())
        for record in manifest['datasets']:
            np.testing.assert_array_equal(arrays[record['array']], training[record['label']])
            if 'normals' in record:
                np.testing.assert_array_equal(arrays[record['normals']], training[record['label'] + '_normals'])
    return {'netcdf': str(nc), 'npz': str(npz), 'shapes': {key: list(value.shape) for key,value in training.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('annulus-output'))
    parser.add_argument('--count', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.count), indent=2))
