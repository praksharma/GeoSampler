"""Recovery copies preserve originals, survive failures and respect live sessions."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from jorvik.app import MainWindow
from jorvik.project import load_project
import test_shell

FIXTURE=Path(__file__).resolve().parents[1]/'examples/geometries/cfdbench/annulus_unstructured.geo'


class RecoveryUiTest(unittest.TestCase):
    setUpClass=classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for=test_shell.ShellTest.wait_for
    javascript=test_shell.ShellTest.javascript

    def test_recovery_lock_transfer_failed_write_and_manual_save(self):
        for suffix in ('.jorvik', '.gsproj'):
            with self.subTest(recovery_extension=suffix):
                self.check_recovery(suffix)

    def check_recovery(self, suffix):
        with tempfile.TemporaryDirectory() as directory:
            settings_path=Path(directory)/'settings.ini'
            def settings():return QSettings(str(settings_path),QSettings.Format.IniFormat)
            first=MainWindow(settings());first.show();others=[]
            try:
                self.wait_for(lambda:first.view.is_ready)
                first.load_geometry(FIXTURE);self.wait_for(lambda:first.import_process is None)
                first.project_path=Path(directory)/'original.jorvik'
                self.assertTrue(first.save_project())
                original_file=first.project_path.read_bytes()
                first.pick_entity(1,1,False)  # Face mode: no implicit mixed selection.
                first.set_selection_mode('edge');first.pick_entity(1,1,False)
                first.sampling.count.setValue(16);first.sampling.start()
                self.wait_for(lambda:first.sampling.process is None)
                original=deepcopy(first.sampling.batches)
                self.assertTrue(first.autosave())
                self.assertTrue(first.has_unsaved_changes());self.assertIsNotNone(first.project_path)
                self.assertEqual(first.recovery_path.suffix, '.jorvik')
                recovery=first.recovery_path;before=recovery.read_bytes()
                restored,_=load_project(recovery)
                self.assertEqual(restored['areas'][0]['area'],original[0])
                first.sampling.seed.setValue(77)
                with patch('jorvik.recovery.save_project',side_effect=OSError('Disk full')):
                    self.assertFalse(first.autosave())
                self.assertEqual(recovery.read_bytes(),before)
                self.assertIn('previous copy retained',first.statusBar().currentMessage())
                # Another live window must not offer or delete the first one's copy.
                second=MainWindow(settings());others.append(second);second.show()
                with patch('jorvik.recovery.QMessageBox.question') as question:
                    second.offer_recovery();question.assert_not_called()
                second.close()
                # Simulate a process interruption by releasing ownership without clean close.
                first.recovery_timer.stop();first.recovery_lock.unlock();first.recovery_lock=None
                if suffix == '.gsproj':
                    legacy = recovery.with_suffix(suffix)
                    recovery.rename(legacy)
                    recovery = legacy
                third=MainWindow(settings());others.append(third)
                with patch('jorvik.recovery.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                    third.show();third.offer_recovery()
                    self.assertIsNotNone(third.geometry)
                self.assertEqual(third.sampling.batches,original)
                self.assertTrue(third.has_unsaved_changes());self.assertIsNone(third.project_path)
                self.assertTrue(third.recovery_path.is_file())
                self.assertEqual(third.recovery_path.suffix, '.jorvik')
                self.assertFalse(recovery.exists())
                path=Path(directory)/'kept.jorvik'
                with patch('jorvik.project_ui.QFileDialog.getSaveFileName',return_value=(str(path),'Jorvik project (*.jorvik)')):
                    self.assertTrue(third.save_project())
                self.assertTrue(path.is_file());self.assertFalse(third.has_unsaved_changes())
                self.assertEqual((Path(directory)/'original.jorvik').read_bytes(),original_file)
                self.assertFalse(third.recovery_path.exists())
                third.sampling.seed.setValue(123)
                self.assertTrue(third.autosave())
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):
                    self.assertFalse(third.close())
                self.assertTrue(third.recovery_path.exists())
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):
                    self.assertTrue(third.close())
                self.assertFalse(third.recovery_path.exists())
            finally:
                for window in [*others,first]:window.close()
