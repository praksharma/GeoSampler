"""Qt-independent labelled coordinates, xarray schema and atomic file export."""
import json
import os
from pathlib import Path
import re
import tempfile

import numpy as np
import xarray as xr

from . import __version__
from .normals import validate_normals

_PREFIX = '_gs_'
_RESERVED = {'xyz', 'file', 'allow_pickle', 'like'}


def to_xarray(batches):
    """One N×3 data variable per label, with independent point dimensions.

    Ordinary identifier labels are variable names. Other labels use a stable
    internal name, retaining the original label in attrs and the label map.
    """
    batches = list(batches)
    if not batches:
        raise ValueError('Generate samples before exporting.')
    variables, coordinates = {}, {'xyz': ['x', 'y', 'z']}
    labels, records = set(), []
    source_identity = None
    for index, batch in enumerate(batches):
        label = batch['label']
        if not isinstance(label, str) or not label.strip():
            raise ValueError('Each dataset must have a non-empty label.')
        if label in labels:
            raise ValueError(f'Duplicate dataset label: {label}')
        labels.add(label)
        identity = (batch['document'], batch['source_hash'])
        if source_identity is not None and identity != source_identity:
            raise ValueError('Datasets must belong to the same source geometry.')
        source_identity = identity
        points = np.asarray(batch['coordinates'], dtype=np.float64)
        tags = np.asarray(batch['entity_tags'])
        if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
            raise ValueError(f'{label}: coordinates must be a finite, non-empty N×3 array.')
        if len(points) != batch['count']:
            raise ValueError(f'{label}: point count does not match coordinates.')
        if tags.shape != (len(points),) or not np.issubdtype(tags.dtype, np.integer):
            raise ValueError(f'{label}: each point needs an integer entity tag.')
        if (tags <= 0).any() or (tags > np.iinfo(np.int32).max).any():
            raise ValueError(f'{label}: entity tags are outside the supported range.')
        dimension = batch['entity_dimension']
        if dimension not in (1, 2, 3) or not set(tags.tolist()) <= {t for d, t in batch['entities'] if d == dimension}:
            raise ValueError(f'{label}: point entity tags do not match the target entities.')
        name = label if (re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', label)
                         and not label.startswith(_PREFIX) and label not in _RESERVED) else f'{_PREFIX}region_{index}'
        point_dim = f'{_PREFIX}points_{index}'
        tag_name = f'{_PREFIX}entity_tags_{index}'
        metadata = {key: value for key, value in batch.items() if key not in ('coordinates', 'entity_tags', 'normals')}
        metadata_json = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
        variables[name] = xr.DataArray(points.copy(), dims=(point_dim, 'xyz'), attrs={
            'label': label, 'method': batch['method'], 'seed': batch['seed'],
            'entity_dimension': dimension, 'entity_tags_coordinate': tag_name,
            'metadata_json': metadata_json})
        coordinates[tag_name] = xr.DataArray(tags.astype(np.int32), dims=point_dim,
                                            attrs={'entity_dimension': dimension})
        record = {'label': label, 'array': name, 'point_dimension': point_dim,
                  'entity_tags': tag_name, 'metadata': metadata}
        normals = validate_normals(batch)
        if normals is not None:
            normal_name = f'{_PREFIX}normals_{index}'
            coordinates[normal_name] = xr.DataArray(normals.copy(), dims=(point_dim, 'xyz'))
            variables[name].attrs['normals_coordinate'] = normal_name
            record['normals'] = normal_name
        records.append(record)
    manifest = {'schema_version': 2, 'jorvik_version': __version__,
                'coordinate_units': 'Source geometry units (unspecified)', 'datasets': records}
    return xr.Dataset(variables, coords=coordinates, attrs={
        'schema_version': 2, 'jorvik_version': __version__,
        'coordinate_units': manifest['coordinate_units'],
        'metadata_json': json.dumps(manifest, ensure_ascii=False, allow_nan=False)})


def export_samples(batches, path):
    """Write .nc or .npz, replacing the destination only after a complete write."""
    path = Path(path)
    if path.suffix.lower() not in ('.nc', '.npz'):
        raise ValueError('Choose a NetCDF (.nc) or NumPy (.npz) file.')
    dataset = to_xarray(batches)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f'.{path.name}.', suffix='.tmp',
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
        if path.suffix.lower() == '.nc':
            dataset.to_netcdf(temporary, engine='scipy', format='NETCDF3_64BIT')
        else:
            arrays = {name: variable.values for name, variable in dataset.data_vars.items()}
            arrays.update({name: coord.values for name, coord in dataset.coords.items()})
            arrays[f'{_PREFIX}metadata'] = np.asarray(dataset.attrs['metadata_json'])
            with temporary.open('wb') as stream:
                np.savez_compressed(stream, allow_pickle=False, **arrays)
        os.replace(temporary, path)
        return path
    finally:
        dataset.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write(path, writer):
    """Keep an existing destination intact when writing fails."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
        writer(temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
