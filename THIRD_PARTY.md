# Third-party code and provenance

## PyniteGUI

Source: https://github.com/praksharma/PyniteGUI
Local source revision: c421ec091b467da7e3955925622988bba36153a7
Author attribution: Prakhar (as recorded by the source package).
Licence: AGPL-3.0-only; full text retained in LICENSE.

GeoSampler adapts the Qt dock layout and application shell, theme palette,
WebEngine/QWebChannel setup, and Three.js camera/render loop. The orientation
gizmo, graphics-backend helper and window-controls helper are copied from PyniteGUI. Structural-analysis
code and application-specific solver dependencies have been removed. GeoSampler's
shell and bridge have been simplified for an empty geometry workspace.

## Three.js 0.180.0

The files under src/geosampler/viewport3d/vendor are copied unchanged from
PyniteGUI's vendored official Three.js distribution, including OrbitControls and
ViewHelper. Their MIT licence and copyright notices are retained in vendor/LICENSE.
