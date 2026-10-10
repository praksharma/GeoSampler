"""Gmsh import adapter. Run in a separate process to isolate kernel state."""
import hashlib
import json
import math
import sys
from pathlib import Path
from uuid import uuid4


def load_geometry(filename):
    import gmsh
    path = Path(filename).resolve()
    if path.suffix.lower() != ".geo":
        raise ValueError("Choose a Gmsh .geo geometry file.")
    if not path.is_file():
        raise ValueError("Geometry file does not exist.")
    gmsh.initialize(["geosampler"], readConfigFiles=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        faces = gmsh.model.getEntities(2)
        edges = gmsh.model.getEntities(1)
        if not faces:
            raise ValueError("This geometry has no faces to display.")
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(1)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        positions = {int(tag): [float(v) for v in coords[3*i:3*i+3]] for i, tag in enumerate(tags)}
        if any(not math.isfinite(v) for p in positions.values() for v in p):
            raise ValueError("Geometry contains non-finite coordinates.")
        groups = [{"dimension": d, "tag": t, "name": gmsh.model.getPhysicalName(d, t),
                   "entities": list(map(int, gmsh.model.getEntitiesForPhysicalGroup(d, t)))}
                  for d, t in gmsh.model.getPhysicalGroups()]
        entities = []
        for dim, tag in [*faces, *edges]:
            vertices = []
            types, _, blocks = gmsh.model.mesh.getElements(dim, tag)
            for kind, block in zip(types, blocks):
                name, _, order, count, _, primary = gmsh.model.mesh.getElementProperties(kind)
                if (dim == 1 and primary != 2) or (dim == 2 and primary not in (3, 4)):
                    raise ValueError(f"Unsupported display element: {name}")
                for offset in range(0, len(block), count):
                    indices = [0, 1] if dim == 1 else ([0, 1, 2] if primary == 3 else [0, 1, 2, 0, 2, 3])
                    for i in indices:
                        vertices.extend(positions[int(block[offset+i])])
            if not vertices:
                raise ValueError(f"Entity ({dim}, {tag}) has no display elements.")
            entities.append({"dimension": dim, "tag": tag, "type": gmsh.model.getType(dim, tag),
                             "boundary": [list(e) for e in gmsh.model.getBoundary([(dim, tag)], oriented=False)],
                             "groups": [g["tag"] for g in groups if g["dimension"] == dim and tag in g["entities"]],
                             "positions": vertices})
        return {"document": uuid4().hex, "source": str(path), "name": path.name,
                "dimension": 3 if gmsh.model.getEntities(3) else 2,
                "source_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "entities": entities, "groups": groups}
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    try:
        print(json.dumps(load_geometry(sys.argv[1]), allow_nan=False))
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
