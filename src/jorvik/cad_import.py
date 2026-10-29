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


def import_options(gmsh, source_format):
    """Record Jorvik's loader arguments, not inferred CAD exporter settings."""
    options = {'backend': 'gmsh', 'backend_version': gmsh.__version__,
               'read_config_files': False,
               'loader': 'open' if source_format == 'geo' else 'occ.importShapes'}
    if source_format != 'geo':
        options.update(highest_dim_only=False, format=source_format)
    return options


def validate_import_metadata(record):
    """Older records may omit provenance; never invent their import settings."""
    kind = record.get('source_format')
    if kind is not None and (not isinstance(kind, str) or kind not in FORMATS.values()):
        raise ValueError('Invalid source format metadata.')
    if 'import_options' not in record:
        return
    options = record['import_options']
    if (not isinstance(options, dict) or kind is None
            or options.get('backend') != 'gmsh'
            or not isinstance(options.get('backend_version'), str)
            or not options['backend_version'].strip()
            or options.get('read_config_files') is not False
            or options.get('loader') != ('open' if kind == 'geo' else 'occ.importShapes')):
        raise ValueError('Invalid geometry import options.')
    if kind != 'geo' and (options.get('highest_dim_only') is not False or options.get('format') != kind):
        raise ValueError('Invalid CAD import options.')
