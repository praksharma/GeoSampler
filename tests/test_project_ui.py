"""Save/reopen a moved project, then edit and regenerate its existing region."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings,Qt
from jorvik.app import MainWindow
from jorvik.area_editor import AreaEditor
import test_shell

FIXTURE=Path(__file__).resolve().parents[1]/'examples/geometries/cad/cylinder.brep'


class ProjectUiTest(unittest.TestCase):
    setUpClass=classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for=test_shell.ShellTest.wait_for
    javascript=test_shell.ShellTest.javascript

    def test_save_restore_and_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'cylinder.brep';source.write_bytes(FIXTURE.read_bytes())
            project=Path(directory)/'structure.gsproj'
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat));window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                window.load_geometry(source);self.wait_for(lambda:window.import_process is None)
                window.pick_entity(2,1,False)
                window.sampling.count.setValue(32);window.sampling.label.setText('wall');window.sampling.start()
                self.wait_for(lambda:window.sampling.process is None)
                original=json.loads(json.dumps(window.sampling.batches[0]))
                window.sampled_areas.items['wall'].setCheckState(0,Qt.CheckState.Unchecked)
                window.sampling.point_size.setValue(9);window.sampling.through.setChecked(False)
                window.hide_faces([2]);window.show_sampled_area('wall')
                window.parametrisation_setup={'schema_version':1,'source_hash':window.geometry['source_hash'],'scope':'regions','regions':['wall'],'translation':[1.,0.,0.]}
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName',return_value=(str(project),'Jorvik project (*.gsproj)')):
                    window.save_project_action.trigger()
                    self.wait_for(project.exists)
                self.assertEqual(window.project_path,project)
                source.unlink() # Opening must use the embedded CAD, not execute or remesh it.
                window.sampling.clear_batches()
                window.load_project_file(project)
                self.assertEqual(window.sampling.batches[0]['coordinates'],original['coordinates'])
                self.assertEqual(window.selection,{(2,1)})
                self.assertEqual(window.sampled_areas.hidden_labels(),['wall'])
                self.assertEqual(window.view.geometry_visibility['hiddenFaces'],[2])
                self.assertEqual(window.sampling.point_size.value(),9)
                self.assertFalse(window.sampling.through.isChecked())
                self.assertEqual(window.parametrisation_setup['regions'],['wall'])
                self.assertTrue(Path(window.geometry['source']).is_file())
                self.wait_for(lambda: self.javascript(window,'window.geoViewer.diagnostics().sampleCount')==32)
                self.assertEqual(self.javascript(window,'window.geoViewer.diagnostics().visibleSampleCount'),0)
                # Reopening the same moved project must not delete its new source cache.
                window.load_project_file(project)
                self.assertTrue(Path(window.geometry['source']).is_file())
                before=json.dumps(window.sampling.batches)
                editor=AreaEditor(window,'wall');editor.count.setValue(99);editor.reject()
                self.assertEqual(json.dumps(window.sampling.batches),before)
                editor=AreaEditor(window,'wall');editor.label.setText('inlet');editor.method.setCurrentIndex(editor.method.findData('lhs'))
                editor.count.setValue(64);editor.seed.setValue(7);editor.target.setCurrentIndex(1)
                editor.entities.item(0).setCheckState(Qt.CheckState.Checked)
                editor.apply();self.wait_for(lambda:window.sampling.process is None)
                self.assertEqual(len(window.sampling.batches),1)
                edited=window.sampling.batches[0]
                self.assertEqual((edited['label'],edited['method'],edited['count'],edited['seed'],edited['entity_dimension']),('inlet','lhs',64,7,1))
                self.assertEqual(edited['colour'],original['colour'])
                self.assertEqual(window.sampled_areas.hidden_labels(),['inlet'])
                self.assertEqual(window.parametrisation_setup['regions'],['inlet'])
                self.assertNotIn('wall',window.sampled_areas.areas)
                # Failed regeneration must retain points, recipe and region name.
                embedded=Path(window.geometry['source']);bytes_before=embedded.read_bytes();embedded.write_bytes(bytes_before+b'\nchanged')
                before=json.dumps(window.sampling.batches)
                editor=AreaEditor(window,'inlet');editor.label.setText('failed');editor.count.setValue(256)
                with patch('jorvik.sampling_panel.QMessageBox.warning') as warning:
                    editor.apply();self.wait_for(lambda:window.sampling.process is None);warning.assert_called_once()
                self.assertEqual(json.dumps(window.sampling.batches),before)
                self.assertNotIn('failed',window.sampled_areas.areas)
                embedded.write_bytes(bytes_before)
                editor=AreaEditor(window,'inlet');editor.label.setText('cancelled_edit');editor.count.setValue(256)
                editor.apply();window.sampling.stop();self.wait_for(lambda:window.sampling.process is None)
                self.assertEqual(json.dumps(window.sampling.batches),before)
                self.assertNotIn('cancelled_edit',window.sampled_areas.areas)
                # A corrupt project must not replace the active document.
                bad=Path(directory)/'bad.gsproj';bad.write_bytes(b'invalid project')
                document=window.geometry['document']
                with patch('jorvik.project_ui.QMessageBox.warning') as warning:
                    window.load_project_file(bad);warning.assert_called_once()
                self.assertEqual(window.geometry['document'],document)
                self.assertEqual(json.dumps(window.sampling.batches),before)
                window.save_project_action.trigger();self.wait_for(lambda:project.stat().st_size>0)
                # Wait for the asynchronous camera snapshot/save callback.
                self.javascript(window,'true')
            finally:window.close()
