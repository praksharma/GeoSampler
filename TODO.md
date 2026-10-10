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
- [ ] Display face shading and optional geometry edges; support 2D and 3D cases.
- [x] Keep display tessellation separate from future sampling data and geometric
      evaluation; rendered triangles are not the authoritative curved geometry.

## 3. Face and edge selection — first usable milestone

- [x] Add explicit face-selection and edge-selection modes.
- [x] Add hover highlighting and click selection mapped to original entity IDs.
- [x] Make edge hover and selection clearly visible with thick screen-space strokes.
- [x] Support multi-selection, deselection and clearing the current selection.
- [x] Synchronize selections between the geometry tree and viewport.
- [x] Show entity type, ID, group membership and relevant details in Properties.
- [ ] Support hide, isolate and show-all controls.
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
- [ ] Saved per-region sampling configurations.
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
- [ ] Save/load full sampling configurations and regenerate datasets.
- [ ] Installation validation, examples and release documentation.

## 6. Broader CAD import

- [ ] Add STEP (`.step`, `.stp`) via Gmsh's Open CASCADE support, followed by
      IGES (`.iges`, `.igs`) and Open CASCADE BREP.
- [ ] Test actual SolidWorks and Ansys geometry exports, including prepared BC
      face partitions, units, multiple bodies and assemblies.
- [ ] Check which names/groups survive neutral-format export; do not assume
      analysis BC labels or CAD entity IDs transfer unchanged.
- [ ] Evaluate direct OCP access if geometry queries or metadata requirements
      outgrow the Gmsh adapter.
- [ ] Keep `.geo` support through Gmsh; do not assume built-in-kernel scripts
      can be loaded directly by OCP or losslessly converted to STEP.

STL import is excluded. Native SolidWorks/Ansys project files, Parasolid and ACIS
readers are outside the initial scope and require separate evaluation.

## Later

- [ ] Additional sampling strategies and local density refinement.
- [ ] Parametric geometry families and stable region tracking.
- [x] Profile generation and add multicore Gmsh/HXT meshing with CPU-core control,
      reproducible fallback, lazy scientific imports and vectorized volume setup.
- [ ] Cache/reuse geometry preparation and support batch generation.
- [ ] Evaluate GPU/JIT acceleration if candidate mapping or clipping becomes
      the measured bottleneck.
