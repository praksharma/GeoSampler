# GeoSampler guide

## Desktop foundation

Drag with the left mouse button to orbit; right-drag to pan; scroll to zoom.
Use the camera selector or the bottom-right orientation gizmo for standard views.
The reference grid is hidden by default. Use Grid to show it in the XY plane
when needed. Grid and axes can be toggled independently.
Reset view returns to the default isometric camera; it fits the loaded geometry.

Left: Geometry and Regions. Right: Properties. Bottom: optional Results pane.
Properties, Sampling and Results scroll within their panes when content grows;
the geometry tree also has scrollbars. Selecting many entities keeps neighbouring
panes available. Properties and Results text can be selected and copied.
Use View to show/hide panes; drag their titles to rearrange or detach them.
View → Reset layout restores the initial layout. Window geometry, panel layout,
and theme persist between launches. The Results pane starts hidden on first launch.

## Architecture

`geometry.py` runs Gmsh in a separate process, returning entity identities,
physical groups and per-entity display tessellation. Only `.geo` input is
currently enabled. Geometry is retained in the source file; display triangles
are not a substitute for exact geometry in future sampling.

`src/geosampler/app.py` owns the Qt window, menus, docks and settings.
`viewport.py` embeds Qt WebEngine and exposes a small QWebChannel bridge.
`viewport3d/` contains local Three.js assets, OrbitControls and the orientation gizmo.
No CDN is required. Structural models, solvers, supports, loads and force diagrams
from PyniteGUI are excluded. Keep future CAD and sampling services independent of Qt.

## Agreed product scope

- CAD contains the faces/edges needed to distinguish boundary-condition regions.
- Users label one or more existing entities per region; labels are metadata.
- No CAD editing, boundary partitioning, BC-value assignment, or PDE solver.
- Sample interiors and individual boundary regions; include normals where applicable.
- Primary Python interface: xarray Dataset, persisted as NetCDF. Alternative: named
  NumPy arrays in NPZ. No Parquet. Final dataset schema remains to be implemented.
- Preserve seeds, geometry references and sampling settings for reproducibility.
- Validate containment, surface distributions, normals, and labels before release.

## Development validation

```sh
uv run python -m unittest discover -s tests -v
uv build
```

The smoke test uses the real WebEngine viewport, checks renderer readiness,
camera changes, theme updates, dock persistence, and graphics errors. Run with a
desktop display; the test selects software rendering. Headless backend support
depends on the host graphics stack.
Check an interactive launch for orbit, zoom, pan, gizmo clicks and dock dragging.

## Provenance

See THIRD_PARTY.md for the source revision and retained licences. roadmap.txt is
the original planning reference; README, this guide and TODO describe current scope.

## Foundation validation record

Validated on 2026-10-10 with Python 3.12 and PySide6 6.12: real WebEngine
startup, camera/bridge response, pane visibility and persistence, and theme
settings passed on Wayland using software rendering. The initial window was
visually inspected. Source and wheel distributions built successfully. This host
emits graphics-driver warnings; its offscreen and X11 paths were not usable.
Interactive mouse gestures and other operating systems still need manual checks.

## Geometry import and selection

Open a `.geo` file with File → Open Geometry, or pass its path on the command
line. Import runs outside the UI process; a failed import retains the previous
model. Closing the window stops an active import. File replacement clears old
selections. Face and edge IDs are scoped to the loaded document.

Select faces (F) uses a crosshair cursor; Select edges (E) uses a cell cursor.
Switching modes clears selection. Click selects one entity; Ctrl/Shift-click
toggles additional entities; clicking empty space or Esc clears selection.
Dragging orbits without selecting. The geometry tree can also select entities
and automatically switches to their face/edge mode. Properties shows IDs,
geometry types and imported physical group IDs. Imported groups are read-only.

Hover is teal; selection is orange. Edge hover uses a 4-pixel stroke and
selected edges use a 6-pixel stroke, maintaining their screen width while
zooming. Ordinary edges remain thin. Surface triangles map to original faces;
only original geometry edges participate in edge selection. Edges hidden behind
nearer faces are filtered using a depth tolerance. Edge picking uses an approximate
six-pixel tolerance at camera target depth. Region editing and hide/isolate tools
are not implemented yet. Sampling is available through the Sampling tab; its numerical mesh is separate
from the display tessellation.

Display tessellation follows the source geometry's surface meshing settings;
coarse inputs may look faceted. It is not a sampling accuracy guarantee.

Validation includes asynchronous import of both reference files, face clicks,
annulus hole rejection, edge clicks and multi-selection, tree synchronization,
file replacement, import failure preservation, and drag suppression. The real
Qt WebEngine renderer and QWebChannel bridge are exercised on Wayland.

## NVIDIA rendering on Linux/Wayland

Normal launches automatically apply the NVIDIA workaround inherited from
PyniteGUI when one NVIDIA GPU drives the connected display: Qt Vulkan backend,
NVIDIA EGL/Vulkan driver selection, and exclusion of Mesa Vulkan layers. These
settings apply only to this application process and respect existing graphics
environment overrides. Do not pass `--software-rendering` for GPU rendering.

PySide6 is pinned to 6.11.2, matching PyniteGUI. On this host, Qt 6.12 stalled
with the automatic NVIDIA setup, while 6.11.2 successfully reported
`ANGLE (NVIDIA Corporation, Quadro RTX 4000/PCIe/SSE2, OpenGL ES 3.2)` through
the actual WebGL context. Check Help → Graphics information for the observed
renderer. The software fallback remains available for other machines.

## Sampling

The right dock contains Properties and Sampling tabs. Choose a target:
selected faces/edges (Ctrl/Shift-click for multiple entities), Domain interior,
or an imported physical face/edge group. Point count is the total across that
target, not a count per constituent entity. Each dataset has a unique label.
After successful generation, the label field automatically suggests the next
available numbered name: `boundary`, `boundary_1`, `boundary_2`, and so on.
Existing names are skipped; manually reusing a name also selects an available
numbered variant. You can enter a different base name at any time. Failed or
cancelled generation does not advance the suggested name. Each generation adds
a separate dataset and preserves earlier coordinates and entity tags. Results
lists the generated datasets with their source entities.

Methods implemented:

| Method | Candidate design |
| --- | --- |
| Uniform random | Independent pseudorandom unit-cube coordinates |
| Regular grid | Complete Cartesian lattices or evenly spaced curve positions |
| LHS | SciPy Latin hypercube |
| Sobol | Scrambled SciPy Sobol, generated in power-of-two blocks |
| Halton | Scrambled SciPy Halton |
| Hammersley | Finite Hammersley set with a seeded random shift |
| Stratified | One random point per recursively partitioned equal-volume stratum |

The seed reproduces the candidate design for a fixed source, method, accuracy
and software version. Regular grid is deterministic and does not use the seed.
Sobol is strongest at power-of-two counts; truncation, geometric transformation
and rejection can change its balance properties. Likewise, final samples on an
irregular domain do not necessarily retain Cartesian LHS or stratification.
These coverage properties apply to the candidate space. See the
[SciPy QMC documentation](https://docs.scipy.org/doc/scipy/reference/stats.qmc.html).

### Geometry and accuracy

Curve coordinates are evaluated on the original Gmsh curves. Numerical
arc-length inversion distributes samples by length across the selected edges.
Surface coordinates are evaluated on the original Gmsh surfaces, with derivative
Jacobian weighting and rejection to account for varying area in parameter space.
The trimmed parameter domain is represented by a separate surface tessellation;
curved trim boundaries consequently have numerical tolerance. Planar face
candidates are also checked using Gmsh containment, including the annulus hole.
The Jacobian rejection envelope is estimated numerically with a safety margin;
generation fails if a candidate exceeds it. This is not a certified global bound.

3D interiors use a separate tetrahedral mesh and volume-weighted barycentric
sampling. Curved-domain approximation depends on mesh accuracy; this is not an
exact CAD solid containment guarantee for arbitrary concave shapes. Standard
and Fine cap the sampling mesh size at the geometry's largest bounding-box
extent divided by 32 and 64 respectively. This is independent of viewport
triangles. Compare accuracy levels before using unfamiliar curved domains for
scientific training. Surface parameter grids have regular parameter spacing,
not necessarily constant spacing measured on the curved surface.

Regular grid clips a complete grid to the target; actual counts can be lower
than the budget. Multi-face grids divide the budget equally between faces.
Other methods return the requested count. Curves use a length-weighted entity
allocation; random surface and volume sampling are area/volume weighted.

### Previews and generation lifecycle

Points use circular markers with dark outlines, starting with warm white for
visibility against selected orange faces and under Night Light. Further datasets
use contrasting colours. The Point size slider changes the marker diameter
(3–16 screen pixels, default 7) immediately without regenerating coordinates;
its value is remembered between sessions. The Sampling pane scrolls when space
is limited so controls retain their natural height. Show sample points toggles the
preview; Show points through geometry reveals interior samples. Clear generated
datasets removes all in-memory datasets. Samples are generated in a separate
process, with cancellation; errors retain previous datasets. Geometry replacement
clears datasets. If the source `.geo` file changes, reopen it before sampling.
Metadata includes source SHA-256, target entities, method, seed, requested/actual
counts, accuracy and approximation notes. Export saves the current datasets;
saved application configurations and normals remain future work.

Validation covers all methods on curves, 2D and 3D interiors; reproducibility;
unit-design properties; annulus containment and area coverage; sphere surface
membership, face membership and area coverage; changed-source rejection; and
GUI generation, preview clearing and cancellation.


## Exporting samples

Use **Export samples…** in Sampling, or **File → Export samples…**
(Ctrl+Shift+S). It exports all generated datasets, including hidden point previews.
NetCDF (`.nc`) is the default; NumPy archive (`.npz`) is the alternative.
The controls become available after generation and are disabled while sampling.
Cancelling the save dialog leaves datasets untouched. Writes use a temporary file
in the destination folder and replace the destination only after a complete write;
a failed save preserves an existing file.

### Schema version 1

Each label is one float64 coordinate array of shape `(N, 3)`, in `x, y, z` order.
Different labels have independent point dimensions (`_gs_points_0`, etc.), so
unequal point counts never produce padding or NaNs. Entity tags are int32 arrays
with one tag per point. Coordinates retain source geometry units; the importer
does not currently identify or convert those units. Normals are not yet generated
or exported. Export is a data snapshot, not a saved editable application project.

Common identifier labels such as `boundary`, `boundary_1`, and `interior` are
array names in both formats. Labels containing spaces, punctuation or Unicode,
reserved names (`xyz`, `file`, `allow_pickle`, `like`), and names starting `_gs_`
use internal `_gs_region_N` names. Original labels are preserved in metadata.
The `_gs_` prefix is reserved for dimensions, entity-tag arrays and metadata.
No user label is silently lost or changed in the metadata.

The xarray interface is `geosampler.export.to_xarray(batches)`. NetCDF is written
through xarray's SciPy engine as NetCDF3 64-bit offset, using the existing SciPy
dependency. The Dataset has only coordinate arrays as data variables; `xyz` and
`_gs_entity_tags_N` are coordinates. Per-variable attributes include `label`,
`method`, `seed`, `entity_dimension`, `entity_tags_coordinate`, and
`metadata_json`. The latter preserves all generation metadata, including target
entities, source path/SHA-256, document identity, requested/actual counts,
accuracy and approximation notes. Global `metadata_json` contains the ordered
label-to-array map, schema/app versions and source-unit description.

```python
import json
import xarray as xr

with xr.open_dataset('samples.nc', engine='scipy') as ds:
    points = ds['boundary'].values  # (N, 3)
    tags = ds['boundary'].coords[ds['boundary'].attrs['entity_tags_coordinate']].values
    metadata = json.loads(ds['boundary'].attrs['metadata_json'])
```

NPZ uses the same coordinate array names, plus `xyz`, `_gs_entity_tags_N`, and
`_gs_metadata` (a Unicode scalar containing JSON). It contains no Python objects
and loads with `allow_pickle=False`. Its manifest maps each original label to
its coordinate and entity-tag array names and retains generation metadata.

```python
import json
import numpy as np

with np.load('samples.npz', allow_pickle=False) as data:
    points = data['boundary']  # (N, 3)
    manifest = json.loads(data['_gs_metadata'].item())
    by_label = {item['label']: item for item in manifest['datasets']}
    tags = data[by_label['boundary']['entity_tags']]
```

Validation covers unequal array lengths, exact coordinate/tag round trips,
Unicode/reserved labels, invalid data, preservation of existing files on save
failure, and both export options from the actual sampled-face UI workflow.
