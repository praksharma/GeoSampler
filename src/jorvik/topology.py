"""Backend-neutral validation of original entity identities and adjacency.

Display primitives remain in geometry['entities']; geometry['topology'] contains
all original vertices, edges, faces and solids, without tessellation coordinates.
"""
import math


def validate_topology(geometry):
    """Validate optional topology; older projects can omit it without fabrication."""
    if 'topology' not in geometry:
        return
    records = geometry['topology']
    if not isinstance(records, list):
        raise ValueError('Invalid geometry topology.')
    entities = {}
    for entity in records:
        if not isinstance(entity, dict):
            raise ValueError('Invalid topology entity.')
        dim, tag = entity.get('dimension'), entity.get('tag')
        if type(dim) is not int or dim not in (0, 1, 2, 3) or type(tag) is not int or tag <= 0:
            raise ValueError('Invalid topology entity identity.')
        key = (dim, tag)
        if key in entities:
            raise ValueError('Duplicate topology entity.')
        entities[key] = entity
        if any(not isinstance(entity.get(field), list) for field in ('boundary', 'upward')):
            raise ValueError('Invalid topology adjacency.')
        bounds = entity.get('bounds')
        if (not isinstance(bounds, list) or len(bounds) != 6
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
                or any(bounds[i] > bounds[i + 3] for i in range(3))):
            raise ValueError('Invalid topology bounds.')
        if not isinstance(entity.get('type'), str) or not isinstance(entity.get('name'), str):
            raise ValueError('Invalid topology entity metadata.')
        groups = entity.get('groups')
        if not isinstance(groups, list) or any(type(t) is not int or t <= 0 for t in groups):
            raise ValueError('Invalid topology groups.')
    display = {(e['dimension'], e['tag']) for e in geometry['entities']}
    if display != {key for key in entities if key[0] in (1, 2)}:
        raise ValueError('Topology and display entity identities differ.')
    group_keys = {(g['dimension'], g['tag']): set(g['entities']) for g in geometry['groups']}
    for (dim, tag), entity in entities.items():
        expected_groups = {t for (d, t), members in group_keys.items() if d == dim and tag in members}
        if set(entity['groups']) != expected_groups:
            raise ValueError('Topology group membership differs from imported groups.')
        for field, step, reverse in (('boundary', -1, 'upward'), ('upward', 1, 'boundary')):
            refs = entity.get(field)
            if not isinstance(refs, list):
                raise ValueError('Invalid topology adjacency.')
            seen = set()
            for ref in refs:
                if (not isinstance(ref, list) or len(ref) != 2
                        or any(type(v) is not int for v in ref)):
                    raise ValueError('Invalid topology adjacency reference.')
                key = tuple(ref)
                if key in seen or ref[0] != dim + step or key not in entities:
                    raise ValueError('Missing, duplicate or wrong-dimension topology adjacency.')
                seen.add(key)
                if [dim, tag] not in entities[key].get(reverse, []):
                    raise ValueError('Topology adjacency is not reciprocal.')
    if geometry.get('solid_count', sum(k[0] == 3 for k in entities)) != sum(k[0] == 3 for k in entities):
        raise ValueError('Topology solid count differs from geometry metadata.')
