"""Real archive work stays off Qt's UI thread while rendering/events continue."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings, QThread, QTimer
from jorvik.app import MainWindow
from jorvik.project import save_project, load_project
import test_shell

FIXTURE=Path(__file__).resolve().parents[1]/'examples/geometries/cfdbench/annulus_unstructured.geo'


class ProjectWorkerUiTest(unittest.TestCase):
    setUpClass=classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for=test_shell.ShellTest.wait_for
    javascript=test_shell.ShellTest.javascript

    def test_worker_ownership_events_errors_and_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat));window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                window.load_geometry(FIXTURE);self.wait_for(lambda:window.import_process is None)
                path=Path(directory)/'saved.jorvik'; window.project_path=path
                ticks=[];states=[]
                timer=QTimer(window);timer.setInterval(5)
                timer.timeout.connect(lambda:(ticks.append(True),states.append((window.sampling.isEnabled(),window.open_action.isEnabled())) if window.project_io is not None else None))
                timer.start()
                def slow_save(*args):
                    self.assertIsNot(QThread.currentThread(),self.app.thread())
                    time.sleep(.12)
                    return save_project(*args)
                with patch('jorvik.project_ui.save_project',side_effect=slow_save):
                    self.assertTrue(window.save_project())
                timer.stop()
                self.assertGreater(len(ticks),5)
                self.assertTrue(all(not sample and not opening for sample,opening in states))
                self.assertTrue(window.sampling.isEnabled());self.assertIsNone(window.project_io)
                ticks.clear();states.clear();timer.start()
                def slow_load(*args):
                    self.assertIsNot(QThread.currentThread(),self.app.thread())
                    time.sleep(.12)
                    return load_project(*args)
                with patch('jorvik.project_ui.load_project',side_effect=slow_load):
                    window.load_project_file(path)
                timer.stop();self.assertGreater(len(ticks),5)
                self.assertIsNone(window.project_io)
                self.assertTrue(window.open_action.isEnabled())
                before=path.read_bytes()
                with patch('jorvik.project_ui.save_project',side_effect=OSError('Disk full')),patch('jorvik.project_ui.QMessageBox.warning') as warning:
                    self.assertFalse(window.save_project());warning.assert_called_once()
                self.assertEqual(path.read_bytes(),before)
                self.assertTrue(window.sampling.isEnabled());self.assertIsNone(window.project_io)
                self.assertFalse(window.saving_project)
            finally:window.close()
