# Development roadmap

## Foundation
- [x] Initialise package and Git repository.
- [x] Reuse PyniteGUI's offline renderer, orientation gizmo and Qt appearance.
- [x] Empty 3D viewport with dockable left/right panes and optional Results pane.
- [x] Menus, camera controls, grid/axes toggles, themes and layout persistence.
- [x] Remove structural-analysis tools and dependencies.

## First end-to-end sampling release
- [ ] Choose CAD backend and import prepared 2D/3D geometry.
- [ ] Face/edge selection, highlighting and visibility.
- [ ] Create/rename/delete labelled regions containing multiple entities.
- [ ] Interior and boundary sampling with seeds and per-region point counts.
- [ ] Sampling previews, normals and geometric validation.
- [ ] xarray/NetCDF and NPZ export; no Parquet.
- [ ] Save/load reproducible sampling projects.
- [ ] Example geometries, installation validation and release documentation.

## Later
- [ ] Additional sampling strategies and local density refinement.
- [ ] Parametric geometry families and stable region tracking.
- [ ] Batch generation and performance optimisation.
