"""Real process exit on terminal signals, plus deferred close during project I/O."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QMessageBox
from jorvik.app import MainWindow
import test_shell

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'examples/geometries/cfdbench/annulus_unstructured.geo'


@unittest.skipUnless(sys.platform.startswith('linux'),'Desktop process signal test uses Linux')
class ShutdownProcessTest(unittest.TestCase):
    def test_terminal_signals_and_window_close_exit(self):
        for mode in ('SIGINT','SIGTERM','groupSIGINT','startup','close'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                marker=Path(directory)/'ready'
                code='''import sys,signal
from pathlib import Path
from PySide6.QtCore import QTimer
from jorvik import app
marker,mode=sys.argv[1:3]
sys.argv=[sys.argv[0],'--software-rendering']
if mode=='startup':
    original_application=app.QApplication
    class InterruptedApplication(original_application):
        def __init__(self,args):
            signal.raise_signal(signal.SIGINT)
            super().__init__(args)
    app.QApplication=InterruptedApplication
original_show=app.MainWindow.show
def show(window):
    original_show(window)
    if mode=='startup':Path(marker).write_text('ready')
    else:QTimer.singleShot(100,lambda:Path(marker).write_text('ready'))
    if mode=='close':QTimer.singleShot(350,window.close)
app.MainWindow.show=show
app.main()
'''
                environment=dict(os.environ,XDG_CONFIG_HOME=directory,XDG_CACHE_HOME=directory,XDG_DATA_HOME=directory)
                process=subprocess.Popen([sys.executable,'-c',code,str(marker),mode],cwd=ROOT,
                    env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    deadline=time.monotonic()+15
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                    self.assertTrue(marker.exists(),'Application did not reach its Qt event loop')
                    if mode in ('SIGINT','SIGTERM'):process.send_signal(getattr(signal,mode))
                    elif mode=='groupSIGINT':os.killpg(process.pid,signal.SIGINT)
                    output=process.communicate(timeout=8)[0].decode(errors='replace')
                    self.assertEqual(process.returncode,0,output[-2000:])
                    self.assertNotIn('KeyboardInterrupt',output)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid,signal.SIGKILL)
                        process.communicate()


class DeferredCloseTest(unittest.TestCase):
    setUpClass=classmethod(test_shell.ShellTest.setUpClass.__func__)
    wait_for=test_shell.ShellTest.wait_for
    javascript=test_shell.ShellTest.javascript

    def test_close_waits_for_io_and_respects_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat));window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                QTimer.singleShot(10,window.close)
                window.project_io_call(lambda:time.sleep(.12))
                self.wait_for(lambda:not window.isVisible())
                self.assertFalse(window._close_requested)
                # A queued close still offers Save/Discard/Cancel once work finishes.
                window.show();window.load_geometry(FIXTURE)
                self.wait_for(lambda:window.import_process is None)
                window.sampling.seed.setValue(77)
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel) as question:
                    QTimer.singleShot(10,window.close)
                    window.project_io_call(lambda:time.sleep(.12))
                    self.wait_for(lambda:question.called)
                    self.assertTrue(window.isVisible())
                    self.assertFalse(window._close_requested)
                    question.assert_called_once()
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):
                    window.close()
            finally:
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):window.close()

    def test_close_during_save_runs_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            window=MainWindow(QSettings(str(Path(directory)/'settings.ini'),QSettings.Format.IniFormat));window.show()
            try:
                self.wait_for(lambda:window.view.is_ready)
                window.load_geometry(FIXTURE);self.wait_for(lambda:window.import_process is None)
                window.sampling.seed.setValue(17)
                window.project_path=Path(directory)/'saved.gsproj'
                from jorvik.project import save_project
                def slow_save(*args):time.sleep(.12);return save_project(*args)
                with patch('jorvik.project_ui.save_project',side_effect=slow_save):
                    QTimer.singleShot(30,window.close)
                    self.assertTrue(window.save_project())
                self.wait_for(lambda:not window.isVisible())
                self.assertTrue(window.project_path.is_file())
                self.assertFalse(window._close_requested)
            finally:
                with patch('jorvik.project_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):window.close()
