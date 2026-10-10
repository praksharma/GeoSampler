"""Shared source loading for display and sampling; independent of Qt."""
from pathlib import Path
import os
import sys

FORMATS = {'.geo': 'geo', '.step': 'step', '.stp': 'step',
           '.brep': 'brep', '.iges': 'iges', '.igs': 'iges'}
FILE_FILTER = 'Supported geometry (*.geo *.step *.stp *.brep *.iges *.igs);;Gmsh (*.geo);;STEP (*.step *.stp);;Open CASCADE BREP (*.brep);;IGES (*.iges *.igs)'


def open_source(gmsh, filename):
    """Open scripts in their own kernel, neutral CAD explicitly through OCC."""
    path = Path(filename).resolve()
    kind = FORMATS.get(path.suffix.lower())
    if kind is None:
        raise ValueError('Choose a Gmsh .geo, STEP, Open CASCADE .brep or IGES geometry file.')
    if not path.is_file():
        raise ValueError('Geometry file does not exist.')
    if kind == 'geo':
        gmsh.open(str(path))
    else:
        gmsh.model.add(path.stem)
        # OCC can print directly to native stdout despite General.Terminal=0.
        # Workers reserve stdout for JSON: retain native diagnostics on stderr.
        sys.stdout.flush()
        saved_stdout = os.dup(1)
        try:
            os.dup2(2, 1)
            gmsh.model.occ.importShapes(str(path), highestDimOnly=False, format=kind)
        finally:
            os.dup2(saved_stdout, 1)
            os.close(saved_stdout)
        gmsh.model.occ.synchronize()
    return kind
