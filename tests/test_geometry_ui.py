"""Import and real Three.js ray-picking integration checks."""
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings, Qt
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
        self.javascript(window, 'window.pickFrame=false; requestAnimationFrame(()=>requestAnimationFrame(()=>window.pickFrame=true)); true')
        self.wait_for(lambda: self.javascript(window, 'window.pickFrame'))
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
                self.assertIn('inner_outer_edges',window.sampled_areas.items)
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
                    self.assertEqual(batch['compute_mode'],'multicore')
                    self.assertEqual(batch['cpu_threads'],window.sampling.cpu_threads.value())
                self.assertEqual(window.sampling.next_available_label('boundary'),'boundary_2')
                self.assertEqual(window.sampling.next_available_label('boundary_1'),'boundary_2')
                self.assertEqual(window.sampling.next_available_label('inlet'),'inlet')
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount')==256)
                areas = window.sampled_areas
                self.assertEqual(areas.root.childCount(),2)
                first = areas.items['boundary']
                second = areas.items['boundary_1']
                self.assertEqual(first.child(0).text(0),'Entities: Face 1')
                self.assertEqual(second.child(0).text(0),'Entities: Face 6')
                self.assertEqual(second.child(1).text(0),'Points: 128')
                self.assertEqual(second.child(4).text(0),'Status: Generated')
                areas.setCurrentItem(second.child(0))
                self.assertIn('boundary_1',window.properties.text())
                self.assertIn('Face 6',window.properties.text())
                second.setCheckState(0,Qt.CheckState.Unchecked)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().visibleSampleCount')==128)
                window.sampling.show_points.setChecked(False)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().visibleSampleCount')==0)
                window.sampling.show_points.setChecked(True)
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().visibleSampleCount')==128)
                window.sampling.point_size.setValue(8)
                self.assertEqual(window.sampled_areas.hidden_labels(),['boundary_1'])
                # All visibility layers preserve CAD selection and generated data.
                before_selection = set(window.selection)
                before_batches = json.dumps(window.sampling.batches)
                document = window.geometry['document']
                window.visibility_actions['faces'].setChecked(False)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==0)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleEdges'),12)
                window.visibility_actions['edges'].setChecked(False)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleEdges')==0)
                window.visibility_actions['geometry'].setChecked(False)
                window.visibility_actions['faces'].setChecked(True)
                window.visibility_actions['edges'].setChecked(True)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleFaces'),0)
                window.visibility_actions['geometry'].setChecked(True)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==8)
                areas.setCurrentItem(first)
                window.isolate_action.setChecked(True)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==0)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleSampleCount'),128)
                window.isolate_geometry_action.setChecked(True)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==1)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleEdges'),3)
                window.region_samples_action.setChecked(False)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleSampleCount')==0)
                window.region_samples_action.setChecked(True)
                window.samples_action.setChecked(False)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleSampleCount')==0)
                self.assertFalse(window.sampling.show_points.isChecked())
                window.samples_action.setChecked(True)
                window.isolate_action.setChecked(False)
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==8)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleEdges'),12)
                self.assertEqual(window.selection,before_selection)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().selectionCount'),len(before_selection))
                self.assertEqual(window.geometry['document'],document)
                self.assertEqual(json.dumps(window.sampling.batches),before_batches)
                self.assertEqual(window.sampled_areas.hidden_labels(),['boundary_1'])
                # Individual face masks preserve CAD selection and all sample coordinates.
                window.face_menu().actions()[0].trigger()
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==7)
                self.assertEqual(window.selection,before_selection)
                window.face_menu().actions()[1].trigger()
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==1)
                window.face_menu().actions()[-1].trigger()
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().visibleFaces')==8)
                self.assertEqual(json.dumps(window.sampling.batches),before_batches)
                # A hidden, isolated region keeps its state when recoloured and renamed.
                from PySide6.QtGui import QColor
                window.show_sampled_area('boundary_1')
                window.isolate_action.setChecked(True)
                with patch('geosampler.app.QColorDialog.getColor',return_value=QColor('#ffc857')):
                    window.area_menu('boundary_1').actions()[1].trigger()
                self.wait_for(lambda: self.javascript(window,
                    "window.geoViewer.diagnostics().sampleColours.boundary_1")=='#ffc857')
                with patch('geosampler.app.QInputDialog.getText',return_value=('outlet',True)):
                    window.area_menu('boundary_1').actions()[0].trigger()
                self.assertEqual(window.selected_area,'outlet')
                self.assertEqual(window.isolated_label(),'outlet')
                self.assertEqual(window.sampled_areas.hidden_labels(),['outlet'])
                self.assertEqual(window.sampling.batches[1]['colour'],'#ffc857')
                self.assertEqual(window.sampling.batches[1]['coordinates'],json.loads(before_batches)[1]['coordinates'])
                self.wait_for(lambda: self.javascript(window,
                    "window.geoViewer.diagnostics().sampleColours.outlet")=='#ffc857')
                for answer in [('boundary',True),('',True),('ignored',False)]:
                    with patch('geosampler.app.QInputDialog.getText',return_value=answer), patch('geosampler.app.QMessageBox.warning') as warning:
                        window.rename_area('outlet')
                        self.assertEqual(warning.call_count, int(answer[1]))
                    self.assertIn('outlet',window.sampled_areas.items)
                window.isolate_action.setChecked(False)
                self.assertTrue(window.export_action.isEnabled())
                self.assertTrue(window.sampling.export.isEnabled())
                # Save the actual sampled faces through both GUI export options.
                import xarray as xr
                import numpy as np
                nc_path = Path(directory)/'sphere_samples.nc'
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(nc_path),'NetCDF (*.nc)')):
                    window.export_action.trigger()
                with xr.open_dataset(nc_path, engine='scipy') as exported:
                    self.assertEqual(set(exported.data_vars),{'boundary','outlet'})
                    for batch in window.sampling.batches:
                        np.testing.assert_array_equal(exported[batch['label']].values,batch['coordinates'])
                        self.assertEqual(json.loads(exported[batch['label']].attrs['metadata_json'])['colour'],batch['colour'])
                npz_path = Path(directory)/'sphere_samples'
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(npz_path),'NumPy archive (*.npz)')):
                    window.sampling.export.click()
                with np.load(npz_path.with_suffix('.npz'), allow_pickle=False) as exported:
                    self.assertEqual(exported['outlet'].shape,(128,3))
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=('','')), patch('geosampler.export.export_samples') as exporter:
                    window.export_samples()
                    exporter.assert_not_called()
                with patch('geosampler.app.QFileDialog.getSaveFileName', return_value=(str(nc_path),'NetCDF (*.nc)')), patch('geosampler.export.export_samples',side_effect=OSError('Disk full')), patch('geosampler.app.QMessageBox.warning') as warning:
                    window.export_samples()
                    warning.assert_called_once()
                # Explicit translation preview is reversible and never accumulates.
                window.parametrisation_button.click()
                dialog = window.parametrisation_dialog
                self.assertIsNotNone(dialog)
                self.assertFalse(window.sampling.isEnabled())
                self.assertFalse(window.open_action.isEnabled())
                self.assertTrue(window.view.isEnabled())
                originals = json.dumps(window.sampling.batches)
                for spin, value in zip(dialog.offsets, (.3, -.1, .2)): spin.setValue(value)
                dialog.preview()
                self.wait_for(lambda: json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().geometryOffset)'))==[.3,-.1,.2])
                dialog.preview()
                self.assertEqual(json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().sampleOffsets.boundary)')),[.3,-.1,.2])
                dialog.scope.setCurrentIndex(1)
                for i in range(dialog.regions.count()):
                    item = dialog.regions.item(i)
                    item.setCheckState(Qt.CheckState.Checked if item.text()=='boundary' else Qt.CheckState.Unchecked)
                dialog.preview()
                self.wait_for(lambda: json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().geometryOffset)'))==[0,0,0])
                self.assertEqual(json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().sampleOffsets.boundary)')),[.3,-.1,.2])
                self.assertEqual(json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().sampleOffsets.outlet)')),[0,0,0])
                self.assertEqual(json.dumps(window.sampling.batches),originals)
                setup_path = Path(directory)/'translation.json'
                with patch('geosampler.parametrisation_panel.QFileDialog.getSaveFileName', return_value=(str(setup_path),'JSON (*.json)')):
                    dialog.save()
                dialog.offsets[0].setValue(9)
                with patch('geosampler.parametrisation_panel.QFileDialog.getOpenFileName', return_value=(str(setup_path),'JSON (*.json)')):
                    dialog.load()
                self.assertEqual(dialog.offsets[0].value(),.3)
                self.assertIsNone(window.view.translation_preview)
                translated_path=Path(directory)/'translated.nc'
                with patch('geosampler.parametrisation_panel.QFileDialog.getSaveFileName', return_value=(str(translated_path),'NetCDF (*.nc)')):
                    dialog.export_configuration()
                with xr.open_dataset(translated_path,engine='scipy') as exported:
                    np.testing.assert_array_equal(exported.boundary.values,np.asarray(window.sampling.batches[0]['coordinates'])+[.3,-.1,.2])
                    np.testing.assert_array_equal(exported.outlet.values,window.sampling.batches[1]['coordinates'])
                    np.testing.assert_array_equal(exported['_gs_translation'],[.3,-.1,.2])
                dialog.tabs.setCurrentIndex(0)
                self.app.processEvents()
                dialog.grab().save('/tmp/geosampler-parametrisation-preview.png')
                dialog.preview()
                dialog.reject()
                self.wait_for(lambda: json.loads(self.javascript(window,'JSON.stringify(window.geoViewer.diagnostics().sampleOffsets.boundary)'))==[0,0,0])
                self.assertEqual(json.dumps(window.sampling.batches),originals)
                self.assertIsNone(window.view.translation_preview)
                self.assertIsNone(window.parametrisation_dialog)
                self.assertTrue(window.sampling.isEnabled())
                self.assertTrue(window.open_action.isEnabled())
                self.assertEqual(len(window.sampling.batches),2)
                window.sampling.clear_batches()
                self.assertFalse(window.sampled_areas.items)
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
                self.assertEqual(window.sampled_areas.items['cancelled'].child(4).text(0),'Status: Not generated (cancelled)')
            finally:window.close()
