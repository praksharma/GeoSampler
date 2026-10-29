"""Verify installed package assets, geometry, exports and optional desktop rendering.

Run this with the Python interpreter of the installation being checked.
Use --installed to reject a source checkout/editable import; --render needs a desktop.
"""
import argparse
from importlib import metadata, resources
import json
from pathlib import Path
import sys
import tempfile
import time


def validate(installed=False, render=False):
    import jorvik
    import numpy as np
    import xarray as xr
    from jorvik.geometry import load_geometry
    from jorvik.sampling import sample_geometry
    from jorvik.export import export_samples
    package = Path(jorvik.__file__).resolve()
    if installed and (not package.is_relative_to(Path(sys.prefix).resolve()) or 'site-packages' not in package.parts):
        raise RuntimeError('This check imported a checkout instead of the isolated installation: ' + str(package))
    assets = resources.files('jorvik') / 'viewport3d'
    for name in ('index.html','viewer.js','gizmo.js','vendor/three.module.js',
                 'vendor/three.core.js','vendor/OrbitControls.js','vendor/lines/LineSegments2.js','vendor/LICENSE'):
        if not (assets / name).is_file():
            raise RuntimeError('Missing offline viewport asset: ' + name)
    with tempfile.TemporaryDirectory(prefix='jorvik-validation-') as directory:
        source = Path(directory) / 'box.geo'
        source.write_text('SetFactory("OpenCASCADE");\nBox(1)={0,0,0,1,1,1};\n')
        geometry = load_geometry(source)
        request = {key: geometry[key] for key in ('source','source_hash','document')}
        request.update(label='boundary',target='selection',entities=[[2,e['tag']] for e in geometry['entities'] if e['dimension']==2],
                       method='sobol',count=32,seed=42,resolution=16)
        boundary = sample_geometry(request)
        if boundary['normal_status'] != 'available': raise RuntimeError('Box normals are unavailable.')
        request.update(label='interior',target='interior',entities=[],count=16)
        interior = sample_geometry(request)
        batches = [boundary, interior]
        nc = export_samples(batches, Path(directory)/'samples.nc')
        npz = export_samples(batches, Path(directory)/'samples.npz')
        with xr.open_dataset(nc,engine='scipy') as dataset, np.load(npz,allow_pickle=False) as arrays:
            manifest = json.loads(dataset.attrs['metadata_json'])
            if manifest['schema_version'] != 2: raise RuntimeError('Unexpected export schema.')
            for record,batch in zip(manifest['datasets'],batches):
                np.testing.assert_array_equal(dataset[record['array']],batch['coordinates'])
                np.testing.assert_array_equal(arrays[record['array']],batch['coordinates'])
                if 'normals' in record:
                    np.testing.assert_array_equal(dataset[record['normals']],batch['normals'])
                    np.testing.assert_array_equal(arrays[record['normals']],batch['normals'])
        if render:
            from PySide6.QtCore import QSettings
            from PySide6.QtWidgets import QApplication
            from jorvik.graphics import configure_graphics
            from jorvik.app import MainWindow
            from jorvik.project import save_project, load_project
            configure_graphics('software')
            app = QApplication.instance() or QApplication([])
            app.setQuitOnLastWindowClosed(False)
            window = MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat))
            def wait_for(check):
                deadline = time.monotonic()+25
                while time.monotonic()<deadline:
                    app.processEvents()
                    if check(): return
                    time.sleep(.01)
                raise RuntimeError('Desktop viewport timed out.')
            try:
                window.show(); wait_for(lambda:window.view.is_ready or not window.view.error.isHidden())
                if not window.view.is_ready: raise RuntimeError(window.view.error.text())
                window.show_geometry(geometry)
                for batch in batches:
                    window.sampling.batches.append(batch); window.sampled_areas.set_area(batch)
                window.sampling.refresh_preview()
                # Wait one frame before inspecting the actual WebGL scene.
                values=[]
                window.view.web.page().runJavaScript('window.geoViewer.diagnostics().sampleCount',values.append)
                wait_for(lambda:bool(values))
                if values[0] != 48: raise RuntimeError('Installed viewport did not render the sample clouds.')
                areas=[(batch,'Generated',True) for batch in batches]
                project=Path(directory)/'box.gsproj'
                save_project(project,geometry,areas,window.project_state())
                restored,_=load_project(project)
                if restored['areas'][0]['area'] != boundary: raise RuntimeError('Project normal round trip failed.')
            finally:
                window.mark_project_clean(); window.close(); app.processEvents()
    return {'version':jorvik.__version__, 'python':sys.version.split()[0], 'package':str(package),
            'desktop_rendered':render,
            'dependencies':{name:metadata.version(name) for name in ('gmsh','numpy','scipy','xarray','PySide6')},
            'checks':['offline assets','CAD topology','boundary/interior sampling','outward normals','NetCDF/NPZ round trips']
                     + (['offline WebGL viewport','project normal round trip'] if render else [])}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',action='store_true')
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args()
    print(json.dumps(validate(args.installed,args.render),indent=2))
