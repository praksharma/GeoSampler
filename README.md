# GeoSampler

Geometry-aware point sampling for PINNs and scientific machine learning.

**Current status:** desktop foundation with an offline 3D viewport, dockable
Geometry/Regions and Properties panes, an optional Results pane, camera controls,
and light/dark themes. CAD import, boundary labelling, sampling, and dataset export
are planned; they are not implemented yet.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run geosampler
```

For graphics compatibility, try `uv run geosampler --software-rendering`.

## Intended workflow

Import prepared CAD → label existing edges/faces → sample regions and interior →
export xarray/NetCDF or NumPy NPZ datasets. CAD already contains the required
boundary partitions. GeoSampler does not prescribe boundary values or solve PDEs.

See [GUIDE.md](GUIDE.md), [TODO.md](TODO.md), and the original [roadmap](roadmap.txt).
Application shell adapted from PyniteGUI: [attribution](THIRD_PARTY.md).
Licensed under [GNU AGPL v3](LICENSE).
