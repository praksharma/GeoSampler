# Development roadmap

## Agreed direction

Start with **Gmsh** as the geometry backend. The first milestone is opening the
existing `.geo` fixtures and reliably selecting their original faces and edges
in GeoSampler. Sampling comes after that workflow is verified.

Keep the geometry interface independent of Qt, Three.js and Gmsh-specific objects
so a direct Open CASCADE/OCP backend can be evaluated later. Prepared CAD already
contains the boundary partitions; GeoSampler does not create or edit them.

## Completed foundation

- [x] Initialise package and Git repository.
- [x] Reuse PyniteGUI's offline renderer, orientation gizmo and Qt appearance.
- [x] 3D viewport with dockable left/right panes and a Sampled Areas tree.
- [x] Menus, camera controls, grid/axes toggles, themes and layout persistence.
- [x] Hide the reference grid by default to keep geometry unobstructed.
- [x] Grouped icon toolbar with tooltips, layered geometry/sample visibility,
      and reversible region isolation with optional geometry context.
- [x] Scrollable Properties alongside Sampling and the geometry tree.
- [x] Replace the Results dock with a Sampled Areas tree, per-dataset visibility,
      generation status and region details in Properties.
- [x] Remove structural-analysis tools and dependencies.
- [x] Add source-attributed CFDBench annulus and sphere geometry fixtures.
- [x] Verify face/edge identity, physical groups and display tessellation with Gmsh.
- [x] Choose Gmsh for the first implementation.

## 1. Geometry import

- [x] Add and lock the Gmsh dependency; verify installation on the development host.
- [x] Define a backend-neutral geometry model: source file, dimension, entities,
      entity identifiers, adjacency, existing groups and bounds.
- [x] Implement a Gmsh adapter that opens `.geo` files and extracts that model.
- [x] Retain `(dimension, tag)` identities within each loaded Gmsh model; scope
      selections to the current document and clear them on replacement.
- [x] Preserve upstream physical groups and names when present; unnamed entities
      remain valid. Do not interpret group names as physical BC values.
- [x] Add File → Open Geometry and show the loaded geometry in the left pane.
- [x] Handle loading errors without losing the previously opened geometry.
- [x] Keep loading responsive and manage Gmsh initialization/cleanup explicitly.

## 2. Display geometry with original entity identities

- [x] Generate display triangles per face and line segments per original edge.
- [x] Map every display primitive to its source entity. Triangulation edges must
      not become selectable CAD edges.
- [x] Send only serializable display data to the existing offline Three.js viewport.
- [x] Fit the camera and scale reference aids to the geometry bounds.
- [x] Display face shading and optional geometry edges; support 2D and 3D cases.
- [x] Keep display tessellation separate from future sampling data and geometric
      evaluation; rendered triangles are not the authoritative curved geometry.

## 3. Face and edge selection — first usable milestone

- [x] Add explicit face-selection and edge-selection modes.
- [x] Add hover highlighting and click selection mapped to original entity IDs.
- [x] Make edge hover and selection clearly visible with thick screen-space strokes.
- [x] Support multi-selection, deselection and clearing the current selection.
- [x] Synchronize selections between the geometry tree and viewport.
- [x] Show entity type, ID, group membership and relevant details in Properties.
- [x] Support hide, isolate and show-all controls.
- [x] Prevent orbit drags from being interpreted as selection clicks.
- [ ] Apply a consistent visible-entity picking policy; test edges at different
      zoom levels and faces partly obscured by other geometry.

Acceptance checks:

- Annulus: select all 8 arcs independently and the single domain face; its
  central hole remains visually open and does not produce a face hit.
- Sphere: select all 8 surface patches and all 12 original edges independently.
- A face remains one selectable entity regardless of its display triangle count.
- Tree selection and viewport clicks resolve to the same entity.
- Switching files clears stale selections; failed imports preserve the old model.
- Existing camera, gizmo, theme and panel controls continue to work.

## 4. User-defined boundary regions

- [ ] Create, rename and delete arbitrary region labels.
- [ ] Assign multiple selected faces or edges to a region.
- [ ] Colour regions and inspect their constituent entities.
- [ ] Keep unlabelled entities available for selection and sampling.
- [ ] Define and document overlapping-region membership behaviour.
- [ ] Save/reopen geometry references and region assignments; detect changed
      source geometry instead of silently trusting old entity tags.

## 5. First end-to-end sampling release

- [x] Seven roadmap sampling methods with seeds and target point counts.
- [x] Selected entities, imported groups and interior targets with labelled datasets.
- [x] Automatically numbered unique dataset labels, retaining each dataset’s entity associations.
- [x] Background generation, cancellation and simultaneous point previews.
- [x] Save per-region recipes in projects and edit/regenerate existing areas.
- [x] Sampling previews.
- [x] Live point-size slider, outlined high-contrast markers and scrollable sampling controls.
- [ ] Outward normals where applicable.
- [x] Reference-fixture boundary membership, coverage and interior checks.
- [ ] Validate arbitrary CAD trimming/containment and normal orientation; add
      certified surface sampling bounds and mesh-convergence checks.
- [x] Primary xarray Dataset interface with NetCDF export; alternative named
      arrays in NPZ. No Parquet.
- [x] Versioned export schema for coordinates, dataset labels, per-point entity
      tags and reproducibility metadata; round-trip NetCDF and NPZ checks.
- [ ] Add applicable normals to exports after normal generation is implemented.
- [x] Save/load full sampling configurations and regenerate datasets.
- [ ] Installation validation, examples and release documentation.

## 6. Broader CAD import — next priority

Release target: **Gmsh .geo + STEP + Open CASCADE BREP + IGES**. All four are now
implemented and tested on small fixtures; broader CAD compatibility and metadata
checks remain below. Prioritise topology-preserving CAD exchange, with
original faces/edges and valid solids rather than triangle-only meshes.

Current backend is the Gmsh Python API, not PythonOCC/OCP. `.geo` scripts can use
Gmsh's built-in kernel or Open CASCADE; do not assume every current model is OCC.
Gmsh documents STEP/IGES import through Open CASCADE and
[`gmsh.model.occ.importShapes`](https://gmsh.info/doc/texinfo/#gmsh_002fmodel_002focc_002fimportShapes)
for BREP, STEP and IGES. Start there without introducing a second geometry backend.

### Format order and implementation

- [x] **1. STEP (`.step`, `.stp`)**: first neutral-format implementation; retain
      analytic/curved geometry, original topology and closed-solid definitions.
      A surface STEP and a solid STEP fixture are covered.
- [ ] Evaluate AP203/AP214/AP242 and richer product metadata; do not promise
      face-level labels will survive every exporter/importer combination.
- [x] **2. Open CASCADE BREP (`.brep`)**: support OCC's native topology format;
      document the accepted BREP dialect rather than treating all B-Rep files alike.
- [x] **3. IGES (`.iges`, `.igs`)**: accept surface-only and solid models;
      disconnected/unsewn surfaces remain usable for boundary sampling, while
      interior sampling requires a validated closed domain.
- [x] Share format detection and geometry loading between the display importer
      and sampling workers, so a file can both render and generate valid samples.
- [x] Update file filters, CLI help, errors and documentation with actual supported
      extensions; validate contents and handle malformed/unsupported files clearly.
- [ ] Keep `.geo` and both Gmsh kernels working; do not require conversion to OCC
      or assume built-in-kernel scripts can be converted losslessly to STEP.
- [ ] Expose vertices, edges, faces, solids and adjacency consistently in the
      backend model; keep tessellation separate from authoritative CAD geometry.
- [ ] Detect source units and coordinate scale where available; retain original
      units/metadata and explicitly record any requested conversion.
- [ ] Support multiple bodies and assembly placements; distinguish disconnected
      solids, open shells and non-manifold geometry before interior sampling.
- [ ] Evaluate optional healing/sewing with explicit reporting of modifications,
      tolerance and entity remapping; never silently change prepared BC partitions.

### Names, metadata and region assignment

- [ ] Import available CAD entity names, colours and assembly/body names separately
      from Gmsh physical groups; expose what actually survived translation.
- [ ] Preserve supplied boundary partitions without claiming topology preservation
      guarantees face names, simulation BC labels or persistent numeric IDs.
- [ ] Let users assign region labels to multiple faces/edges when CAD names are
      absent; separate these assignments from generated dataset labels.
- [ ] Track source hash, format and import options in saved projects and exports;
      invalidate/remap region references explicitly after reimport or healing.
- [ ] Evaluate direct OCP access only if Gmsh metadata/topology queries become
      insufficient; keep the backend-independent application interface.

### Validation and release checks

- [x] Download and verify pinned Gmsh STEP/BREP/IGES fixtures with provenance
      and licence; test topology, face/edge sampling, solid interior sampling,
      surface-only rejection, degenerate edges, GUI visibility and exports.

- [ ] Add small, attributable STEP/BREP/IGES fixtures: curved solid with a hole,
      prepared boundary patches, open surface, multiple bodies and assembly placement.
- [ ] Verify face/edge selection, hide/isolate, names, point membership, interior
      containment, cancellation and export round trips on every supported format.
- [ ] Test real exports from SolidWorks and Ansys SpaceClaim first; expand the
      interoperability matrix to NX, CATIA, Creo, Inventor, Fusion, Onshape,
      FreeCAD and Rhino as accessible fixtures allow. Record exporter version,
      settings and units rather than assuming every product exports every format.
- [ ] Preserve the current model/datasets after failed imports and ensure import
      and sampling errors identify open domains or invalid topology clearly.

### Later translators and exclusions

- [ ] **4. Parasolid (`.x_t`, `.x_b`)**: evaluate translator availability, licence,
      distribution terms, cost and topology/metadata fidelity before committing
      to direct import. STEP conversion is the initial workflow.
- [ ] Evaluate ACIS (`.sat`, `.sab`) and Rhino `.3dm` only when demand and a suitable
      licensed reader justify them; they are not implied by OCC exchange support.

STL remains excluded. Native SolidWorks, CATIA, NX, Creo and Ansys project readers
are outside the initial release; use the verified neutral export formats instead.

## Later

- [ ] Additional sampling strategies and local density refinement.
- [ ] Parametric geometry families and stable region tracking.
- [x] Profile generation and add multicore Gmsh/HXT meshing with CPU-core control,
      reproducible fallback, lazy scientific imports and vectorized volume setup.
- [ ] Cache/reuse geometry preparation and support batch generation.
- [ ] Evaluate GPU/JIT acceleration if candidate mapping or clipping becomes
      the measured bottleneck.

## Region inspection controls

- [x] Geometry tree context menu: hide selected faces, isolate selected faces, show all faces.
- [x] Sampled Areas context menu: rename, change colour, visibility and isolation.
- [x] Preserve coordinates and visibility across renaming; export new labels and colour metadata.

## Parametrisation workspace

### Implemented first slice

- [x] Separate workspace accessible below Sampled Areas, with four tabs.
- [x] Single translation configuration: whole domain or selected-region augmentation.
- [x] Explicit reversible preview from originals; preserve coordinates, visibility and colours.
- [x] NetCDF/NPZ export with named parameter values and transformation provenance.
- [x] Save/load lightweight setup; validate source geometry and region references.

### Parameters and transformation engine

- [ ] Add multiple named parameters with units, reference/default values, ranges,
      explicit value lists or counts, and unambiguous mapping to transformations.
- [ ] Add rotation with axis, angle units and pivot; add positive uniform and
      non-uniform scaling with explicit origin/pivot.
- [ ] Define transformation composition order and coordinate frame (world/local);
      persist the order and frame and always evaluate from original coordinates.
- [ ] Retain whole-domain transformations as the default consistent-domain mode;
      label independent region transformations as augmentation with unverified
      consistency until domain-aware validation is available.
- [ ] Allow explicit parameter-to-region bindings and multiple transformations on
      a region; define overlapping-region behaviour and shared-boundary consistency.
- [ ] Reject non-finite values, singular transforms and non-positive scaling;
      keep reflections out of the initial supported transform set.
- [ ] Generate applicable boundary normals first, with orientation validation;
      rotate/scale normals with the normalized inverse transpose, preserving
      translation invariance. Never silently invent outward normals for open shells.
- [ ] Document sampling-density changes after non-uniform scaling, and evaluate
      surface/volume Jacobian weights where requested for downstream integration.

### Configuration generation and constraints

- [ ] Cartesian products, paired explicit configurations, seeded random, LHS and
      Sobol designs; distinguish per-parameter value counts from total design size.
- [ ] Generate parameter-space designs independently of spatial sampling settings;
      record design algorithm, seed, bounds and actual parameter values.
- [ ] Show configuration count, points per region/configuration, estimated output
      size and memory needs before starting; avoid allocating huge Cartesian grids.
- [ ] Implement explicit parameter constraints and model validity checks; report
      rejected configurations and reasons without silently changing their values.
- [ ] Record effects of filtering on LHS/Sobol coverage; define rejection/replacement
      behaviour reproducibly and keep configuration identifiers stable.
- [ ] Support configuration table/filter/selection and preview exactly one chosen
      configuration without generating or rendering the entire sweep.

### Preview and execution

- [ ] Extend reversible preview to rotation/scaling and regenerated geometry;
      keep original CAD, datasets, region assignments and visibility intact.
- [ ] Keep parameter edits lightweight: mark stale previews/results and require
      explicit Preview or Process configurations; never auto-run complete sweeps.
- [ ] Three modes: Preview one configuration; Batch process all configurations
      without changing the viewport; Export-only stream results to disk.
- [ ] Background workers with bounded queues/chunks and configurable concurrency;
      avoid keeping all clouds in RAM or multiplying memory across workers.
- [ ] Progress bar, elapsed time, completed/total counts, warnings/failures and Cancel.
- [ ] Define fail-fast versus continue-on-error behaviour, partial-output marking,
      cleanup, cancellation checkpoints and optional resume/retry of a manifest.
- [ ] Retain separate methods, seeds, point counts and geometry accuracy for each
      region; include unchanged regions where needed for consistent domain datasets.
- [ ] Geometry-aware membership checks against the intended transformed/regenerated
      domain; clearly distinguish outside points, invalid geometry and unverified
      checks. Moving just a wall must not imply the interior remains valid.

### CAD dimensional regeneration — later stage

- [ ] Store sampling recipes independently of generated output: entity/region
      references, target, method, count, seed, accuracy and compute settings.
- [ ] Define an explicit CAD parameter source (e.g. supported `.geo` variables or
      a geometry-generation adapter); imported STEP/BREP need not contain editable
      design history or named dimensions.
- [ ] Regenerate models for radius, width, length and thickness changes and rerun
      recipes for every valid configuration; keep this separate from point mapping.
- [ ] Track entities/regions across regeneration and topology changes; reject
      missing, split, merged or ambiguous boundaries until explicitly remapped.
- [ ] Validate regenerated closed domains, holes and material regions, then
      recompute interior points and applicable normals rather than moving only
      boundary points for a dimension change.
- [ ] Cache reusable preparation keyed by source/configuration/recipe and preserve
      deterministic configuration ordering and provenance across worker counts.

### Parametric exports and persistence

- [ ] Version the parametric schema independently of ordinary dataset exports.
- [ ] NetCDF4 backend and xarray DataTree: shared parameter values indexed by
      configuration, one group per region with coordinates `(configuration, point,
      xyz)`, entity tags, applicable normals and complete recipe/transform metadata.
- [ ] Use stable safe group/key identifiers plus an original-label map; arbitrary
      labels, slashes and reserved names must round-trip without collisions.
- [ ] Write parameter values once; expose `(x,y,z,mu...)` training-array construction
      without requiring repeated parameter columns in persistent storage.
- [ ] Incremental/chunked disk writes, compression and configurable precision;
      do not assume xarray append mode automatically extends configuration arrays.
- [ ] Handle varying point counts explicitly through ragged representations or
      separate configuration groups; never silently pad, truncate or duplicate points.
- [ ] NPZ configuration shards plus manifest for large runs; document filenames,
      safe keys, loading without pickle and reconstruction of region/parameter data.
- [ ] Preserve source hashes, units, original recipes, algorithms/seeds, parameter
      configurations, transform order/pivots, warnings and completed/failed status.
- [ ] Keep final outputs atomic or clearly mark incomplete streaming runs; preserve
      existing destinations on failure and define safe resume behaviour.
- [ ] Extend setup JSON to multiple parameters, designs, constraints, bindings and
      recipes; version/migrate it independently of generated output.
- [x] Full project persistence for geometry, regions, recipes, generated points and
      translation setup; embed the main CAD source and validate source hashes.
- [ ] Optional point-cloud omission and full `.geo` dependency bundling/checksums.
- [x] Retain setup changes when reopening the workspace and include them in projects;
      remap region renames and clear bindings when datasets/model are cleared.
- [ ] Explicit new/reset parametrisation setup action.

### Acceptance checks

- [ ] Rotation/pivot and transform-order cases; inverse-transpose normals under
      non-uniform scaling; zero-motion and identity configurations.
- [ ] Repeated preview, scope changes, Restore, Close and Escape never accumulate
      transforms or overwrite original geometry, samples or region visibility.
- [ ] Whole-domain boundary/interior consistency and explicit warnings for unsafe
      independent region changes; invalid/missing constraints and source changes.
- [ ] Reproducible Cartesian/LHS/Sobol/random configurations and stable provenance;
      verify coverage limitations after constraint filtering.
- [ ] Unequal region counts and varying configuration counts round-trip through
      DataTree/NetCDF4 and NPZ shards with labels, parameters, tags and normals.
- [ ] Cancellation, partial failures, disk-full, resume/retry, changed setup versions
      and multi-million-point runs with bounded memory and responsive UI.
- [ ] End-to-end PINN example loading parameter-conditioned coordinates and separate
      boundary/interior datasets, plus regeneration with topology-change rejection.

## Project persistence and sampled-area editing

- [x] File menu save/open/save-as `.gsproj` archives with CAD and numeric arrays.
- [x] Restore cached topology and samples without regeneration, including moved sources.
- [x] Preserve recipes, colours, visibility, selection, camera, layout and translation setup.
- [x] Right-click Edit: label, target entities, method, count, seed, accuracy and CPU settings.
- [x] Replace edited area only after success; preserve originals on cancellation/failure.
- [x] Versioned validation, checksums, no pickle, atomic writes and failed-load preservation.
- [ ] Background project I/O and measured large-project memory/performance checks.
- [ ] Autosave/recovery and unsaved-change prompts before destructive workspace replacement.
