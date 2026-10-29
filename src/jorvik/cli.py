"""Classify launch documents without importing Qt or executing geometry."""
from pathlib import Path
from .cad_import import FORMATS
from .project import PROJECT_EXTENSIONS


def launch_document(filename):
    path = Path(filename).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'File does not exist or is not a regular file: {path}')
    if path.suffix.lower() in PROJECT_EXTENSIONS:
        return 'project', path
    if path.suffix.lower() in FORMATS:
        return 'geometry', path
    raise ValueError('Unsupported file. Choose a Jorvik .jorvik (or legacy .gsproj), Gmsh .geo, STEP, '
                     'Open CASCADE BREP or IGES file.')
