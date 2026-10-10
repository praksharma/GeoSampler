"""Import and real Three.js ray-picking integration checks."""
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings
from geosampler.app import MainWindow
import unittest
import test_shell

FIXTURES = Path(__file__).resolve().parents[1] / 'examples/geometries/cfdbench'


class GeometryTest(unittest.TestCase):
    setUpClass = classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for = test_shell.ShellTest.wait_for
    javascript = test_shell.ShellTest.javascript

    def project(self, window, point):
        size=json.loads(self.javascript(window, 'JSON.stringify([innerWidth, innerHeight])'))
        positions=[e['positions'] for e in window.geometry['entities']]
        low=[min(p[i] for p in positions for i in range(axis,len(p),3)) for axis in range(3)]
        high=[max(p[i] for p in positions for i in range(axis,len(p),3)) for axis in range(3)]
        radius=math.dist(low,high)*.6
        distance=radius/math.sin(math.radians(19))/min(1,size[0]/size[1])
        scale=size[1]/(2*distance*math.tan(math.radians(19)))
        return [size[0]/2+point[0]*scale,size[1]/2-point[1]*scale]

    def click(self, window, point, extend=False):
        x,y=self.project(window,point)
        self.javascript(window, f'''(()=>{{const c=document.querySelector('canvas');
          for(const type of ['pointerdown','pointerup'])c.dispatchEvent(new PointerEvent(type,
          {{clientX:{x},clientY:{y},button:0,pointerId:1,pointerType:'mouse',ctrlKey:{str(extend).lower()},bubbles:true}}));return true;}})()''')
        # Wait for a round trip on the independent WebChannel transport.
        import time
        until=time.monotonic()+.2
        while time.monotonic()<until:self.app.processEvents()

    def test_import_and_ray_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'ui.ini'),QSettings.Format.IniFormat))
            window.show()
            try:
                self.wait_for(lambda: window.view.is_ready)
                window.load_geometry(FIXTURES/'annulus_unstructured.geo')
                self.wait_for(lambda: window.import_process is None)
                self.assertEqual(len(window.items),9)
                self.wait_for(lambda: window.orientation.currentIndex()==1)
                self.click(window,(.75,0,0))
                self.wait_for(lambda: window.selection=={(2,1)})
                self.click(window,(0,0,0))
                self.wait_for(lambda: not window.selection)
                window.set_selection_mode('edge')
                self.click(window,(-.5/math.sqrt(2),.5/math.sqrt(2),0))
                self.wait_for(lambda: window.selection=={(1,1)})
                self.click(window,(-1/math.sqrt(2),1/math.sqrt(2),0),True)
                self.wait_for(lambda: window.selection=={(1,1),(1,5)})
                # Generate asynchronously from the selected arcs and render the dataset.
                window.sampling.method.setCurrentIndex(window.sampling.method.findData('sobol'))
                window.sampling.count.setValue(128)
                window.sampling.label.setText('inner_outer_edges')
                window.sampling.start()
                self.wait_for(lambda: window.sampling.process is None, seconds=45)
                self.assertEqual(len(window.sampling.batches),1)
                self.assertEqual(window.sampling.batches[0]['count'],128)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount')==128)
                coordinates = list(window.sampling.batches[0]['coordinates'])
                window.sampling.point_size.setValue(12)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().pointSize')==12)
                self.assertEqual(window.settings.value('sampling/point_size', type=int),12)
                window.sampling.show_points.setChecked(False)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleVisible') is False)
                self.assertEqual(self.javascript(window, 'window.geoViewer.diagnostics().sampleCount'),128)
                self.assertEqual(window.sampling.batches[0]['coordinates'],coordinates)
                window.sampling.show_points.setChecked(True)
                self.assertTrue(window.results_dock.isVisible())
                window.sampling.clear_batches()
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount')==0)
                # A drag that returns to its starting point must not select.
                before = set(window.selection)
                self.javascript(window, """(()=>{const c=document.querySelector('canvas');
                  const capture=c.setPointerCapture, release=c.releasePointerCapture;
                  c.setPointerCapture=()=>{};c.releasePointerCapture=()=>{};
                  for(const [type,x] of [['pointerdown',200],['pointermove',240],['pointerup',200]])
                    c.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:200,button:0,buttons:type==='pointerup'?0:1,pointerId:4,pointerType:'mouse',bubbles:true}));c.setPointerCapture=capture;c.releasePointerCapture=release;return true;})()""")
                self.assertEqual(window.selection,before)
                # Backend failures leave the current document and selection intact.
                previous=window.geometry['document']
                with patch('geosampler.app.QMessageBox.warning') as warning:
                    window.load_geometry(Path(directory)/'missing.geo')
                    self.wait_for(lambda: window.import_process is None)
                    warning.assert_called_once()
                self.assertEqual(previous,window.geometry['document'])
                window.load_geometry(FIXTURES/'sphere_unstructured.geo')
                self.wait_for(lambda: window.import_process is None)
                self.assertEqual(len(window.items),20)
                self.assertFalse(window.selection)
                window.set_selection_mode('face')
                window.view.call('orient',1)
                self.wait_for(lambda: window.orientation.currentIndex()==1)
                self.click(window,(.3,.3,0))
                self.wait_for(lambda: bool(window.selection))
                self.assertEqual(next(iter(window.selection))[0],2)
                # Every geometry entity can also be selected through the tree.
                for key,item in window.items.items():
                    window.tree.clearSelection()
                    window.tree.setCurrentItem(item)
                    item.setSelected(True)
                    self.assertEqual(window.selection,{key})
                    self.assertEqual(window.view.mode,'face' if key[0]==2 else 'edge')
                window.set_selection_mode('face')
                window.view.call('orient',0)
                self.wait_for(lambda: window.orientation.currentIndex()==0)
                # Wait for the next painted frame after bridge updates.
                self.javascript(window, 'window.previewFrame=false; requestAnimationFrame(()=>requestAnimationFrame(()=>window.previewFrame=true)); true')
                self.wait_for(lambda: self.javascript(window, 'window.previewFrame'))
                window.pick_entity(2,1,False)
                self.javascript(window, 'true')
                import time
                end=time.monotonic()+.3
                while time.monotonic()<end:self.app.processEvents()
                window.grab().save('/tmp/geosampler-import-preview.png')
                # Sampling successive sphere faces automatically suggests unique labels.
                window.sampling.target.setCurrentIndex(0)
                window.sampling.label.setText('boundary')
                window.sampling.count.setValue(128)
                window.sampling.method.setCurrentIndex(window.sampling.method.findData('random'))
                with patch('geosampler.sampling_panel.QMessageBox.information') as information:
                    for index,tag in enumerate((1, 6)):
                        window.pick_entity(2,tag,False)
                        window.sampling.start()
                        self.assertIsNotNone(window.sampling.process)
                        self.wait_for(lambda: window.sampling.process is None, seconds=45)
                        self.assertEqual(window.sampling.label.text(),f'boundary_{index+1}')
                    information.assert_not_called()
                self.assertEqual(len(window.sampling.batches),2)
                for index,(batch,tag) in enumerate(zip(window.sampling.batches,(1,6))):
                    self.assertEqual(batch['label'],'boundary' if index==0 else 'boundary_1')
                    self.assertEqual(batch['entities'],[[2,tag]])
                    self.assertEqual(set(batch['entity_tags']),{tag})
                    self.assertEqual(batch['count'],128)
                self.assertEqual(window.sampling.next_available_label('boundary'),'boundary_2')
                self.assertEqual(window.sampling.next_available_label('boundary_1'),'boundary_2')
                self.assertEqual(window.sampling.next_available_label('inlet'),'inlet')
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount')==256)
                self.assertIn('Face 1',window.sample_results.text())
                self.assertIn('Face 6',window.sample_results.text())
                self.assertTrue(window.export_action.isEnabled())
                self.assertTrue(window.sampling.export.isEnabled())
                # Save the actual sampled faces through both GUI export options.
                import xarray as xr
                import numpy as np
                nc_path = Path(directory)/'sphere_samples.nc'
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(nc_path),'NetCDF (*.nc)')):
                    window.export_action.trigger()
                with xr.open_dataset(nc_path, engine='scipy') as exported:
                    self.assertEqual(set(exported.data_vars),{'boundary','boundary_1'})
                    for batch in window.sampling.batches:
                        np.testing.assert_array_equal(exported[batch['label']].values,batch['coordinates'])
                npz_path = Path(directory)/'sphere_samples'
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(npz_path),'NumPy archive (*.npz)')):
                    window.sampling.export.click()
                with np.load(npz_path.with_suffix('.npz'), allow_pickle=False) as exported:
                    self.assertEqual(exported['boundary_1'].shape,(128,3))
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=('','')), patch('geosampler.export.export_samples') as exporter:
                    window.export_samples()
                    exporter.assert_not_called()
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(nc_path),'NetCDF (*.nc)')), patch('geosampler.export.export_samples',side_effect=OSError('Disk full')), patch('geosampler.app.QMessageBox.warning') as warning:
                    window.export_samples()
                    warning.assert_called_once()
                self.assertEqual(len(window.sampling.batches),2)
                window.sampling.clear_batches()
                self.assertFalse(window.export_action.isEnabled())
                self.assertFalse(window.sampling.export.isEnabled())
                window.sampling.target.setCurrentIndex(1)
                window.sampling.label.setText('interior')
                window.sampling.resolution.setCurrentIndex(0)
                window.sampling.count.setValue(128)
                window.sampling.start()
                self.wait_for(lambda: window.sampling.process is None, seconds=45)
                self.assertEqual(len(window.sampling.batches),1)
                self.assertEqual(window.sampling.batches[0]['count'],128)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount')==128)
                window.sampling.label.setText('cancelled')
                window.sampling.start()
                window.sampling.stop()
                self.wait_for(lambda: window.sampling.process is None)
                self.assertEqual(len(window.sampling.batches),1)
                self.assertEqual(window.sampling.label.text(),'cancelled')
            finally:window.close()
