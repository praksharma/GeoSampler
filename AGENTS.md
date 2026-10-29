# Repository Instructions

## Git Commits

Every Git commit created or amended by Codex in this repository must include
this exact trailer in the commit message, separated from the body by a blank line:

```text
Co-authored-by: Codex <codex@openai.com>
```

Apply this rule to documentation-only commits as well as code commits. Do not
rewrite existing commit history unless the user explicitly requests it.

## Documentation

- Keep `README.md` short: project overview, logo, quick start, and useful links.
- Maintain detailed workflows, engineering limitations, architecture, and test
  instructions in `GUIDE.md`.
- Update `TODO.md` as features are implemented or new work is identified.
- Commit completed, verified changes in coherent groups with their tests.

## Jorvik scope

- Build a geometry-aware sampling desktop application for PINNs and scientific ML.
- CAD models already contain the separate edges/faces needed for boundary regions.
  Do not add CAD editing or face/edge partitioning unless explicitly requested.
- Labels are arbitrary metadata; multiple entities may share a label.
- Keep physics, structural analysis, solvers, and prescribed BC values out of the app.
- Primary dataset interface: xarray, persisted as NetCDF. Alternative: NumPy NPZ.
  Do not add Parquet.
- Preserve the offline viewport and third-party licences/attribution.
- Keep geometry/sampling logic independent of Qt and the rendering layer.
- Distinguish implemented features from future plans in documentation and UI.
