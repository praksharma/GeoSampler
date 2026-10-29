"""Save/Discard/Cancel protect workspace content through replacement and closing."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from jorvik.app import MainWindow
from jorvik.regions import put_region
import test_shell

FIXTURES=Path(__file__).resolve().parents[1]/'examples/geometries/cfdbench'


class UnsavedUiTest(unittest.TestCase):
    setUpClass=classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for=test_shell.ShellTest.wait_for
    javascript=test_shell.ShellTest.javascript

    def test_cancel_failed_save_and_successful_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat))
            window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                window.load_geometry(FIXTURES/'annulus_unstructured.geo')
                self.wait_for(lambda:window.import_process is None)
                self.assertFalse(window.has_unsaved_changes())
                window.pick_entity(2,1,False)
                self.assertFalse(window.has_unsaved_changes())
                window.boundary_regions=put_region([],window.geometry,'wall',[[1,1],[1,2]],'#abcdef')
                window.refresh_boundary_regions()
                self.assertTrue(window.has_unsaved_changes())
                document=window.geometry['document']; regions=deepcopy(window.boundary_regions)
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):
                    window.load_geometry(FIXTURES/'sphere_unstructured.geo')
                    self.wait_for(lambda:window.import_process is None)
                    self.assertEqual(window.geometry['document'],document)
                    self.assertEqual(window.boundary_regions,regions)
                    self.assertFalse(window.close())
                    self.assertTrue(window.isVisible())
                # Cancelling Save As also cancels the original close request.
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Save), patch(
                    'jorvik.project_ui.QFileDialog.getSaveFileName',return_value=('','')):
                    self.assertFalse(window.close())
                    self.assertTrue(window.has_unsaved_changes())
                path=Path(directory)/'saved.jorvik'
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName',return_value=(str(path),'Jorvik project (*.jorvik)')):
                    self.assertTrue(window.save_project())
                self.assertFalse(window.has_unsaved_changes())
                before=path.read_bytes()
                window.sampling.seed.setValue(77)
                self.assertTrue(window.has_unsaved_changes())
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Save), patch(
                    'jorvik.project_ui.save_project',side_effect=OSError('Disk full')), patch(
                    'jorvik.project_ui.QMessageBox.warning') as warning:
                    self.assertFalse(window.close());warning.assert_called_once()
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(window.geometry['document'],document)
                self.assertTrue(window.has_unsaved_changes())
                # A valid candidate is held until the prior workspace is saved.
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Save):
                    window.load_geometry(FIXTURES/'sphere_unstructured.geo')
                    self.wait_for(lambda:window.import_process is None and window.geometry['document']!=document)
                self.assertEqual(window.boundary_regions,[])
                self.assertFalse(window.has_unsaved_changes())
                window.load_project_file(path)
                self.assertEqual(window.boundary_regions,regions)
                self.assertEqual(window.sampling.seed.value(),77)
                self.assertFalse(window.has_unsaved_changes())
                window.sampling.count.setValue(45)
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Save):
                    window.load_project_file(path)
                self.assertEqual(window.sampling.count.value(),45)
                self.assertFalse(window.has_unsaved_changes())
                window.sampling.count.setValue(99)
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):
                    window.load_project_file(path)
                self.assertEqual(window.sampling.count.value(),99)
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):
                    window.load_project_file(path)
                self.assertNotEqual(window.sampling.count.value(),99)
                self.assertFalse(window.has_unsaved_changes())
            finally:window.close()
