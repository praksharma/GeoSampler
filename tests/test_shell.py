"""Integration checks against the real offline WebEngine renderer."""
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QLabel, QMessageBox
from jorvik.app import MainWindow
from jorvik.theme import configure_theme
from jorvik.graphics import configure_graphics


class ShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics("software")
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        configure_theme(cls.app, 'light')
        discard = patch('jorvik.project_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Discard)
        discard.start()
        cls.addClassCleanup(discard.stop)

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
                self.assertFalse(any(d.objectName()=='results' for d in window.findChildren(QDockWidget)))
                self.assertEqual(window.sampled_areas.root.text(0),'Sampled Areas')
                self.assertEqual(window.toolbar.toolButtonStyle(),Qt.ToolButtonStyle.ToolButtonIconOnly)
                for action,name in window.icon_actions:
                    self.assertFalse(action.icon().isNull(),name)
                    self.assertTrue(action.toolTip(),name)
                self.assertTrue(window.geometry_dock.isVisible())
                self.assertTrue(window.properties_dock.isVisible())
                self.assertTrue(self.javascript(window, 'window.geoFailure === null'))
                self.assertEqual(self.javascript(window, 'document.querySelectorAll("canvas").length'), 1)
                window.view.call('orient', 3)
                self.wait_for(lambda: window.orientation.currentIndex() == 3)
                window.sampling.point_size.setValue(10)
                window.set_theme('dark')
                self.assertEqual(settings.value('theme'), 'dark')
                window.set_visibility('show_grid', False)
                window.set_visibility('show_axes', False)
                self.assertFalse(window.view.show_grid)
                # Restore a legacy saved layout that had a visible Results dock.
                legacy_results = QDockWidget('Results',window)
                legacy_results.setObjectName('results')
                legacy_results.setWidget(QLabel('Legacy results'))
                window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,legacy_results)
                legacy_results.show()
                window.close()
                self.assertTrue(settings.contains('layout'))
                reopened = MainWindow(settings)
                reopened.show()
                try:
                    self.assertEqual(reopened.sampling.point_size.value(),10)
                    self.assertFalse(any(d.objectName()=='results' for d in reopened.findChildren(QDockWidget)))
                    reopened.reset_layout()
                    self.assertTrue(reopened.geometry_dock.isVisible())
                finally:
                    reopened.close()
            finally:
                window.close()
