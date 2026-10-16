"""User-defined boundary metadata, independent of sampling, Qt and rendering."""
from copy import deepcopy
import re
from uuid import uuid4


def validate_regions(regions, geometry):
    if not isinstance(regions, list):
        raise ValueError('Invalid boundary regions.')
    available = {(e['dimension'], e['tag']) for e in geometry['entities']}
    ids, labels = set(), set()
    for region in regions:
        if not isinstance(region, dict):
            raise ValueError('Invalid boundary region.')
        identity, label = region.get('id'), region.get('label')
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError('Boundary region identifiers must be unique.')
        if not isinstance(label, str) or not label.strip() or label != label.strip() or label in labels:
            raise ValueError('Boundary region labels must be non-empty and unique.')
        ids.add(identity); labels.add(label)
        if (region.get('source_hash') != geometry['source_hash']
                or region.get('document') != geometry['document']
                or region.get('source_format') != geometry.get('source_format', 'geo')):
            raise ValueError('Boundary region belongs to different or changed geometry. Reassign its entities.')
        if not isinstance(region.get('colour'), str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', region['colour']):
            raise ValueError('Choose a valid boundary region colour.')
        members = region.get('entities')
        if not isinstance(members, list) or not members:
            raise ValueError('Choose at least one face or edge for a boundary region.')
        keys = set()
        for member in members:
            if (not isinstance(member, list) or len(member) != 2
                    or any(type(v) is not int for v in member)
                    or member[0] not in (1, 2) or tuple(member) not in available):
                raise ValueError('Boundary region references a missing face or edge.')
            keys.add(tuple(member))
        if len(keys) != len(members) or len({d for d, _ in keys}) != 1:
            raise ValueError('A boundary region must contain distinct faces or distinct edges.')


def put_region(regions, geometry, label, entities, colour, identity=None):
    """Return a new list; regions may overlap, and existing lists stay untouched."""
    validate_regions(regions, geometry)
    if identity is not None and not any(r['id'] == identity for r in regions):
        raise ValueError('This boundary region no longer exists.')
    record = {'id': identity or uuid4().hex, 'label': label.strip(),
              'entities': sorted([list(e) for e in entities]), 'colour': colour,
              'source_hash': geometry['source_hash'], 'document': geometry['document'],
              'source_format': geometry.get('source_format', 'geo')}
    result = deepcopy(regions)
    if identity is None:
        result.append(record)
    else:
        result[next(i for i, r in enumerate(result) if r['id'] == identity)] = record
    validate_regions(result, geometry)
    return result


def region_snapshot(regions, geometry, identity):
    """Snapshot memberships at generation time; later edits cannot relabel samples."""
    validate_regions(regions, geometry)
    record = next((r for r in regions if r['id'] == identity), None)
    if record is None:
        raise ValueError('The selected boundary region no longer exists.')
    return deepcopy(record)
