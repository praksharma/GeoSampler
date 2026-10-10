# GeoSampler

Geometry-aware point sampling for PINNs and scientific machine learning.

**Current status:** import Gmsh `.geo` geometry, inspect it in the offline 3D
viewport, and select original faces or edges using separate tools. Includes
synchronized tree selection, multi-selection, imported group information,
dockable panes and light/dark themes. Generate labelled datasets with seven
sampling methods, preview interior or boundary coordinates, and export labelled
xarray/NetCDF or NumPy NPZ arrays. Region editing is planned.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run geosampler
```

Use **File → Open Geometry** (Ctrl+O), then **Select faces** (F) or
**Select edges** (E). Ctrl/Shift-click toggles additional entities; Esc clears.
Drag to orbit, right-drag to pan, and scroll to zoom.

Open the **Sampling** tab on the right. Choose selected faces/edges, an imported
group, or the domain interior; set the method, count, seed, and dataset label;
then click **Generate samples**. Multiple datasets can be previewed together.
Use **Export samples** in the Sampling pane or File menu to save all datasets
as NetCDF (default) or NPZ. Each label is an independent coordinate array.
Methods: random, regular grid, LHS, Sobol, Halton, Hammersley, and stratified.
See the guide for numerical geometry accuracy and grid-count behaviour.

Try the included fixture directly:

```sh
uv run geosampler examples/geometries/cfdbench/sphere_unstructured.geo
```

Normal launches use automatic graphics selection, including the NVIDIA/Wayland
configuration. **Help → Graphics information** shows the actual renderer.
For graphics compatibility, try `uv run geosampler --software-rendering`.

## Intended workflow

Import prepared CAD → label existing edges/faces → sample regions and interior →
export xarray/NetCDF or NumPy NPZ datasets. CAD already contains the required
boundary partitions. GeoSampler does not prescribe boundary values or solve PDEs.

See [GUIDE.md](GUIDE.md), [TODO.md](TODO.md), and the original [roadmap](roadmap.txt).
Application shell adapted from PyniteGUI: [attribution](THIRD_PARTY.md).
Licensed under [GNU AGPL v3](LICENSE).
