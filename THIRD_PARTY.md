# Third-party code and provenance

## PyniteGUI

Source: https://github.com/praksharma/PyniteGUI
Local source revision: c421ec091b467da7e3955925622988bba36153a7
Author attribution: Prakhar (as recorded by the source package).
Licence: AGPL-3.0-only; full text retained in LICENSE.

Jorvik adapts the Qt dock layout and application shell, theme palette,
WebEngine/QWebChannel setup, and Three.js camera/render loop. The orientation
gizmo, graphics-backend helper and window-controls helper are copied from PyniteGUI. Structural-analysis
code and application-specific solver dependencies have been removed. Jorvik's
shell and bridge have been simplified for an empty geometry workspace.

## Three.js 0.180.0

The files under src/jorvik/viewport3d/vendor are copied unchanged from
PyniteGUI's vendored official Three.js distribution, including OrbitControls and
ViewHelper. Their MIT licence and copyright notices are retained in vendor/LICENSE.

## CFDBench geometry fixtures

`examples/geometries/cfdbench/` contains two unmodified Gmsh definitions by
Ricardo Costa. See that directory's README, provenance.json and LICENSE for
source revision, checksums, and the upstream credit/citation requirements.
These fixtures retain their upstream licence separately from application code.

## Gmsh runtime dependency

Jorvik uses Gmsh 4.15.2 through its Python API for `.geo`, STEP, OCC BREP and IGES import and
per-entity display tessellation. Gmsh is installed as a dependency; its source
and licence information are available at https://gmsh.info/.

The thick-line modules in `viewport3d/vendor/lines/` are copied unchanged from
the official Three.js r180 `examples/jsm/lines/` directory (LineSegments2,
LineSegmentsGeometry, LineMaterial), under the same retained MIT licence.

## Gmsh CAD fixtures

`examples/geometries/cad/` contains unmodified STEP, Open CASCADE BREP and IGES
models from the official `gmsh-project/gmsh` repository. That folder retains
upstream LICENSE.txt (GPL-2.0-or-later with the Gmsh linking exception), source
revision, paths and byte checksums. See its README and provenance.json. These
third-party fixtures retain their upstream licence separately from application code.
