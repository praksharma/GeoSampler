# Geometry to training data

Jorvik turns prepared CAD into reproducible, labelled point datasets for
PINNs and scientific machine learning. Keep the relationship between each point
and its original face, edge or interior region, then bring the data into your own
training code.

**Development preview · 0.1.0.dev0**

[Start with your first dataset](guide/getting-started.md){ .md-button .md-button--primary }
[Explore the export schema](reference/exports.md){ .md-button }

## One workflow, from CAD to arrays

1. **Open geometry.** Import Gmsh `.geo`, STEP, Open CASCADE BREP or IGES.
2. **Name boundaries.** Assign existing faces or edges to arbitrary regions.
3. **Generate samples.** Choose a method, point count, seed and geometry accuracy.
4. **Inspect and keep.** Preview several datasets, save the workspace and export
   independent coordinate arrays with entity tags and applicable outward normals.

CAD already contains the boundary partitions. Jorvik labels and samples them;
physics, prescribed boundary values and solvers belong in downstream tools.

## Find what you need

| Task | Read |
| --- | --- |
| Import CAD and select the right entity | [Geometry and selection](guide/geometry.md) |
| Label several faces or edges together | [Boundary regions](guide/regions.md) |
| Choose a sampling method and accuracy | [Sampling and accuracy](guide/sampling.md) |
| Understand outward directions and unavailable normals | [Boundary normals](guide/normals.md) |
| Save work or recover an interrupted session | [Projects and recovery](guide/projects.md) |
| Load training arrays in Python | [NetCDF, NPZ and xarray](reference/exports.md) |
| Run a complete annulus example | [Release checks and example](development/release.md) |
| Contribute or verify a change | [Architecture](development/architecture.md) · [Testing](development/testing.md) |

## Know the current limits

Surface trims and solid interiors use numerical geometry checks. Units are
currently unspecified, and arbitrary industrial CAD still needs validation.
Normals are omitted when outward orientation cannot be verified. Parametrisation
currently supports one explicit translation; rotation, scaling and sweeps are
future work.

The installed preview has been checked on macOS arm64 with Python 3.12. Broader
CAD compatibility, Windows/Linux checks and large-project memory improvements
remain on the [roadmap](development/roadmap.md). See the detailed
[release record](development/release.md) before relying on a new workflow.
