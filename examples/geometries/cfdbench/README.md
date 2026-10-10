# CFDBench geometry fixtures

Two unmodified Gmsh `.geo` definitions by **Ricardo Costa**, from
[CFDBench](https://github.com/ricardodpcosta/CFDBench/tree/4d8553ce5e7e6ef3eaf8373e1d565cc06301b34f/Gmsh/repository).
Pinned revision: `4d8553ce5e7e6ef3eaf8373e1d565cc06301b34f`.
Source URLs and SHA-256 checksums are recorded in provenance.json. Downloaded
bytes were checked against the upstream Git blob hashes.

| File | Geometry defined by source | Intended checks |
| --- | --- | --- |
| annulus_unstructured.geo | 2D annulus centred at the origin, radii 0.5 and 1 | Separate inner/outer boundary labels, grouping four arcs per boundary, exclusion of the central hole |
| sphere_unstructured.geo | 3D unit sphere centred at the origin, eight surface patches | Curved-face selection, grouping faces, boundary normals, surface and volume sampling |

The annulus has physical curve groups 1 (inner) and 2 (outer), plus surface
100. The sphere has physical surface group 1 (all eight patches) and volume
100. These identifiers describe geometry groups, not prescribed BC values.

These are geometry/meshing scripts, not STEP files or pre-generated meshes.
Backend checks passed with Gmsh 4.15.2 on 2026-10-10. Every face and edge
can be addressed and isolated independently, with nonempty per-entity display
tessellation. The annulus has 8 edges and 1 face; the sphere has 12 edges and
8 faces. Existing physical groups survive loading. Sphere surface mesh nodes
lie on the unit sphere within 1e-8; annulus surface mesh nodes lie between
radii 0.5 and 1 within 1e-8. These node checks do not certify full domain
containment, normals, mesh quality, or sampling distributions.

Full results: entity-check.json. Reproduce from the repository root:

```sh
uv run --with gmsh==4.15.2 python scripts/check_geo_entities.py
```

GeoSampler's current shell still has no importer or mouse-picking interface.
When implementing it, preserve `(dimension, tag)` for every rendered entity:
triangle hits map to faces, line-segment hits map to edges. Physical groups
combine entities without removing their individual identities. Tags identify
entities in the loaded model; do not assume they survive arbitrary CAD edits.

## Upstream licence and credit

The exact upstream LICENSE is included here. Its title is **MIT License with
Author(s) Credit and Citation Requirement**; it contains additional credit and
academic citation requirements. Preserve it with these fixtures and credit
Ricardo Costa / CFDBench in public use. For academic works, research publications
or presentations, follow its requirement to cite the original work referenced
in the applicable upstream case README. No case-specific citation is supplied
in these standalone geometry scripts; do not invent one.

These third-party fixtures retain their own licence, separately from
GeoSampler's application code.
