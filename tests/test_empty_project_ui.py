"""Empty workspace replacement and importing into an existing project document."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from jorvik.app import MainWindow
from jorvik.project import create_empty_project, load_project
from test_project import FIXTURE
import test_shell


class EmptyProjectUiTest(unittest.TestCase):
    setUpClass = classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for = test_shell.ShellTest.wait_for
    javascript = test_shell.ShellTest.javascript

    def test_empty_import_save_and_workspace_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = create_empty_project(Path(directory) / 'from-another-app.gsproj')
            window = MainWindow(QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat))
            window.show()
            try:
                self.wait_for(lambda: window.view.is_ready)
                self.assertTrue(window.load_project_file(path))
                self.assertIsNone(window.geometry)
                self.assertEqual(window.project_path, path)
                self.assertFalse(window.has_unsaved_changes())
                self.assertFalse(window.sampling.generate.isEnabled())
                self.assertTrue(window.save_project_action.isEnabled())
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName') as dialog:
                    self.assertTrue(window.save_project())
                    dialog.assert_not_called()
                self.assertIsNone(load_project(path)[0]['geometry'])
                window.load_geometry(FIXTURE)
                self.wait_for(lambda: window.import_process is None)
                self.assertIsNotNone(window.geometry)
                self.assertEqual(window.project_path, path)
                self.assertTrue(window.has_unsaved_changes())
                # Closing after import must still offer to save the document.
                with patch('jorvik.project_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Cancel) as question:
                    self.assertFalse(window.confirm_unsaved_changes())
                    question.assert_called_once()
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName') as dialog:
                    self.assertTrue(window.save_project())
                    dialog.assert_not_called()
                self.assertFalse(window.has_unsaved_changes())
                self.assertEqual(load_project(path)[0]['geometry']['source_hash'], window.geometry['source_hash'])
                self.assertTrue(window.load_project_file(path))
                self.assertIsNotNone(window.geometry)
                window.pick_entity(2, 1, False)
                window.sampling.count.setValue(8); window.sampling.start()
                self.wait_for(lambda: window.sampling.process is None)
                self.assertTrue(window.sampling.batches)
                self.assertTrue(window.save_project())
                other = create_empty_project(Path(directory) / 'other.gsproj')
                self.assertTrue(window.load_project_file(other))
                self.assertIsNone(window.geometry)
                self.assertIsNone(window.view.geometry)
                self.assertEqual(window.sampling.batches, [])
                self.assertEqual(window.boundary_regions, [])
                self.assertEqual(window.selection, set())
                self.assertEqual(window.tree.topLevelItemCount(), 0)
                self.assertEqual(window.sampled_areas.areas, {})
                self.wait_for(lambda: self.javascript(window, 'window.geoViewer.diagnostics().sampleCount') == 0)
                self.assertEqual(self.javascript(window, 'window.geoViewer.diagnostics().visibleFaces'), 0)
                self.assertEqual(self.javascript(window, 'Object.keys(window.geoViewer.diagnostics().entityColours).length'), 0)
                self.assertFalse(window.sampling.generate.isEnabled())
                # Failed imports retain the empty document and its bytes.
                before = other.read_bytes()
                with patch('jorvik.app.QMessageBox.warning') as warning:
                    window.load_geometry(Path(directory) / 'missing.geo')
                    self.wait_for(lambda: window.import_process is None)
                    warning.assert_called_once()
                self.assertEqual(window.project_path, other)
                self.assertEqual(other.read_bytes(), before)
                self.assertTrue(window.save_project())
            finally:
                with patch('jorvik.project_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Discard):
                    window.close()

    def test_save_initial_empty_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow(QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat))
            try:
                path = Path(directory) / 'created.gsproj'
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName', return_value=(str(path), '')):
                    self.assertTrue(window.save_project())
                self.assertEqual(window.project_path, path)
                self.assertIsNone(load_project(path)[0]['geometry'])
            finally: window.close()
