"""Qt-independent, reversible translation of original sampled datasets."""
from copy import deepcopy
import json
import numpy as np

SCHEMA_VERSION = 1


def validate_setup(setup, batches=None):
    if setup.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Unsupported parametrisation setup version.')
    if setup.get('scope') not in ('domain', 'regions'):
        raise ValueError('Choose whole domain or selected regions.')
    values = np.asarray(setup.get('translation'), dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all():
        raise ValueError('Translation needs three finite values.')
    labels = setup.get('regions', [])
    if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels):
        raise ValueError('Invalid region labels.')
    if setup['scope'] == 'regions' and not labels:
        raise ValueError('Select at least one sampled region.')
    if batches is not None:
        if not batches:
            raise ValueError('Generate samples before processing configurations.')
        if setup.get('source_hash') != batches[0]['source_hash']:
            raise ValueError('This setup belongs to a different geometry. Create a new setup for this model.')
        if setup['scope'] == 'regions' and set(labels) - {b['label'] for b in batches}:
            raise ValueError('Some setup regions are missing or renamed. Select the regions again.')
    return values


def transform_batches(batches, setup):
    """Translate from originals, preserving counts, tags, metadata and normals."""
    offset = validate_setup(setup, batches)
    result = []
    for batch in batches:
        record = deepcopy(batch)
        affected = setup['scope'] == 'domain' or batch['label'] in setup['regions']
        points = np.asarray(batch['coordinates'], dtype=float)
        transformed = points + offset if affected else points.copy()
        if not np.isfinite(transformed).all():
            raise ValueError('Translation produced non-finite coordinates.')
        record['coordinates'] = transformed.tolist()
        record['parametrisation'] = {
            'schema_version': SCHEMA_VERSION, 'operation': 'translation',
            'scope': setup['scope'], 'affected': affected,
            'parameters': dict(zip(('translation_x', 'translation_y', 'translation_z'), offset.tolist())),
            'regions': list(setup['regions']),
            'domain_consistency': 'consistent translation' if setup['scope'] == 'domain' else 'unverified',
        }
        result.append(record)
    return result


def save_setup(setup, path):
    validate_setup(setup)
    # Setup contains references and parameters, never point-cloud output.
    from .export import atomic_write
    atomic_write(path, lambda temporary: temporary.write_text(json.dumps(setup, indent=2, allow_nan=False) + '\n'))


def load_setup(path):
    from pathlib import Path
    setup = json.loads(Path(path).read_text())
    if not isinstance(setup, dict):
        raise ValueError('Invalid parametrisation setup.')
    validate_setup(setup)
    return setup


def export_configuration(batches, setup, path):
    """Export one configuration with named parameter values and region metadata."""
    from pathlib import Path
    import xarray as xr
    from .export import to_xarray, atomic_write
    path = Path(path)
    if path.suffix.lower() not in ('.nc', '.npz'):
        raise ValueError('Choose a NetCDF (.nc) or NumPy (.npz) file.')
    records = transform_batches(batches, setup)
    dataset = to_xarray(records)
    dataset.coords['_gs_translation'] = xr.DataArray(
        setup['translation'], dims='_gs_parameter',
        coords={'_gs_parameter': ['translation_x', 'translation_y', 'translation_z']})
    manifest = json.loads(dataset.attrs['metadata_json'])
    manifest['parametrisation'] = setup
    manifest['configuration_count'] = 1
    dataset.attrs['metadata_json'] = json.dumps(manifest, allow_nan=False)
    try:
        def write(temporary):
            if path.suffix.lower() == '.nc':
                dataset.to_netcdf(temporary, engine='scipy', format='NETCDF3_64BIT')
            else:
                arrays = {name: array.values for name, array in dataset.variables.items()}
                arrays['_gs_metadata'] = np.asarray(dataset.attrs['metadata_json'])
                with temporary.open('wb') as stream:
                    np.savez_compressed(stream, allow_pickle=False, **arrays)
        atomic_write(path, write)
    finally:
        dataset.close()
    return path
