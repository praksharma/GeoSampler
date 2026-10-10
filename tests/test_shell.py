"""Integration checks against the real offline WebEngine renderer."""
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from geosampler.app import MainWindow
from geosampler.theme import configure_theme
from geosampler.graphics import configure_graphics


class ShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics("software")
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        configure_theme(cls.app, 'light')

    def wait_for(self, predicate, seconds=25):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        self.fail('Timed out waiting for the viewport')

    def javascript(self, window, expression):
        values = []
        window.view.web.page().runJavaScript(expression, values.append)
        self.wait_for(lambda: bool(values))
        return values[0]

    def test_renderer_controls_and_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory)/'settings.ini'), QSettings.Format.IniFormat)
            window = MainWindow(settings)
            window.show()
            try:
                self.wait_for(lambda: window.view.is_ready or not window.view.error.isHidden())
                self.assertTrue(window.view.is_ready, window.view.error.text())
                self.assertTrue(window.results_dock.isHidden())
                self.assertTrue(window.geometry_dock.isVisible())
                self.assertTrue(window.properties_dock.isVisible())
                self.assertTrue(self.javascript(window, 'window.geoFailure === null'))
                self.assertEqual(self.javascript(window, 'document.querySelectorAll("canvas").length'), 1)
                window.view.call('orient', 3)
                self.wait_for(lambda: window.orientation.currentIndex() == 3)
                window.set_theme('dark')
                self.assertEqual(settings.value('theme'), 'dark')
                window.set_visibility('show_grid', False)
                window.set_visibility('show_axes', False)
                self.assertFalse(window.view.show_grid)
                window.results_dock.show()
                window.close()
                self.assertTrue(settings.contains('layout'))
                reopened = MainWindow(settings)
                reopened.show()
                try:
                    self.assertTrue(reopened.results_dock.isVisible())
                    reopened.reset_layout()
                    self.assertTrue(reopened.results_dock.isHidden())
                finally:
                    reopened.close()
            finally:
                window.close()
