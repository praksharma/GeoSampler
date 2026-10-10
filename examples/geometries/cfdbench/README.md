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
They have been source-inspected and download-verified, but not executed or
geometrically validated with Gmsh. GeoSampler's current shell has no importer yet.
Future validation should check the annulus's loop ordering and resulting domain,
as well as curved-surface construction and normal orientation, before sampling.

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
