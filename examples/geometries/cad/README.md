# Downloaded CAD exchange fixtures

Unmodified models from [Gmsh's official repository](https://github.com/gmsh-project/gmsh),
pinned at revision `e2e2839e27d6269eada13d0b862673b4d267b32d`.
Downloaded bytes were checked against upstream Git blob hashes. URLs, Git blob
IDs and SHA-256 checksums are recorded in provenance.json.

| File | Upstream location | Observed import with Gmsh 4.15.2 | Purpose |
| --- | --- | --- | --- |
| t20_data.step | tutorials/t20_data.step | One solid | STEP tutorial part; face/edge and interior sampling |
| cube_filet.stp | benchmarks/step/cube_filet.stp | 25 faces, 74 edges, no solid | Filleted cube surfaces, including eight zero-length topology edges |
| cylinder.brep | benchmarks/brep/cylinder.brep | One solid, 3 faces, 3 edges | Curved OCC BREP boundary and volume sampling |
| cube1000.igs | benchmarks/iges/cube1000.igs | 6 faces, 24 edges, no solid | IGES boundary-only workflow; do not infer closure from appearance |

Open any file with File → Open Geometry or pass its path to `uv run geosampler`.
Select faces/edges and generate samples normally. Interior sampling is available
only when solid volumes exist. Zero-length CAD edges remain in the tree for
inspection, but cannot supply points. These files are downloaded originals,
not generated or converted versions of the existing `.geo` examples.

## Licence and attribution

Credit the Gmsh project and preserve included LICENSE.txt and provenance.json.
The upstream licence is GPL version 2 or later with the Gmsh linking exception;
these fixtures retain that licence separately from GeoSampler's application code.
The complete unmodified upstream models are included here as their source.
No CAD exporter-specific face-name or unit preservation guarantee is implied.
