"""GeoSampler desktop shell, adapted from PyniteGUI's Qt layout."""
import argparse
import sys
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QLabel,
    QMainWindow, QMessageBox, QToolBar, QTreeWidget, QTreeWidgetItem)
from . import __version__
from .theme import configure_theme
from .viewport import Viewport
from .graphics import configure_graphics
from .window_controls import install_window_controls


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("GeoSampler", "GeoSampler")
        self.setWindowTitle("GeoSampler — Untitled")
        self.resize(1280, 820)
        self.setMinimumSize(820, 560)
        self.view = Viewport(self)
        self.setCentralWidget(self.view)
        self.statusBar().showMessage("Starting 3D viewport…")
        self.view.status.connect(self.statusBar().showMessage)
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")
        self.view_menu = self.menuBar().addMenu("&View")
        self.toolbar = QToolBar("Viewport", self)
        self.toolbar.setObjectName("viewport_toolbar")
        self.addToolBar(self.toolbar)
        self.orientation = QComboBox()
        self.orientation.addItems(["Isometric", "Front XY", "Top XZ", "Right YZ", "Back XY", "Bottom XZ", "Left YZ", "Orbit"])
        self.orientation.model().item(7).setEnabled(False)
        self.orientation.setToolTip("Camera orientation")
        self.orientation.activated.connect(lambda index: self.view.call("orient", index))
        self.view.oriented.connect(self.orientation.setCurrentIndex)
        self.toolbar.addWidget(self.orientation)
        self.toolbar.addAction("Reset view", lambda: self.view.call("reset"))
        for label, attribute in (("Grid", "show_grid"), ("Axes", "show_axes")):
            action = self.toolbar.addAction(label)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(lambda checked, attr=attribute: self.set_visibility(attr, checked))
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.addTopLevelItems([QTreeWidgetItem(["Geometry"]), QTreeWidgetItem(["Regions"])])
        self.geometry_dock = self.dock("Geometry and Regions", "geometry", tree, Qt.DockWidgetArea.LeftDockWidgetArea)
        properties = QLabel("No geometry selected.")
        properties.setMargin(16)
        properties.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.properties_dock = self.dock("Properties", "properties", properties, Qt.DockWidgetArea.RightDockWidgetArea)
        results = QLabel("No samples generated.")
        results.setMargin(16)
        self.results_dock = self.dock("Results", "results", results, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.results_dock.hide()
        self.view_menu.addAction(self.toolbar.toggleViewAction())
        self.view_menu.addSeparator()
        self.view_menu.addAction("Reset layout", self.reset_layout)
        appearance = self.view_menu.addMenu("Appearance")
        self.theme_group = QActionGroup(self)
        saved_theme = self.settings.value("theme", "light")
        for name in ("light", "dark"):
            action = appearance.addAction(name.title())
            action.setCheckable(True)
            action.setChecked(name == saved_theme)
            action.triggered.connect(lambda checked=False, name=name: self.set_theme(name))
            self.theme_group.addAction(action)
        self.menuBar().addMenu("&Help").addAction("About GeoSampler", self.about)
        self.resizeDocks([self.geometry_dock, self.properties_dock], [240, 260], Qt.Orientation.Horizontal)
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("layout"):
            self.restoreState(self.settings.value("layout"))

    def dock(self, title, name, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())
        return dock

    def set_visibility(self, attribute, checked):
        setattr(self.view, attribute, checked)
        self.view.apply_theme()

    def reset_layout(self):
        for dock, area in ((self.geometry_dock, Qt.DockWidgetArea.LeftDockWidgetArea),
                           (self.properties_dock, Qt.DockWidgetArea.RightDockWidgetArea),
                           (self.results_dock, Qt.DockWidgetArea.BottomDockWidgetArea)):
            dock.setFloating(False)
            self.addDockWidget(area, dock)
            dock.setVisible(dock is not self.results_dock)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.toolbar.show()
        self.resizeDocks([self.geometry_dock, self.properties_dock], [240, 260], Qt.Orientation.Horizontal)

    def set_theme(self, name):
        configure_theme(QApplication.instance(), name)
        self.settings.setValue("theme", name)

    def apply_theme(self):
        self.view.apply_theme()

    def about(self):
        QMessageBox.about(self, "About GeoSampler", f"GeoSampler {__version__}\nGeometry-aware sampling for PINNs.\n\nDesktop foundation: CAD import and sampling are planned.\nAdapted from PyniteGUI; licensed under AGPL-3.0-only.\nThree.js is distributed under its MIT licence.")

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("layout", self.saveState())
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="GeoSampler desktop application")
    parser.add_argument("--version", action="version", version=f"GeoSampler {__version__}")
    parser.add_argument("--software-rendering", action="store_true", help="Use software rendering for the 3D viewport")
    args = parser.parse_args()
    configure_graphics("software" if args.software_rendering else "auto")
    application = QApplication([sys.argv[0]])
    application.setApplicationName("GeoSampler")
    application.setOrganizationName("GeoSampler")
    settings = QSettings("GeoSampler", "GeoSampler")
    configure_theme(application, settings.value("theme", "light"))
    install_window_controls(application)
    window = MainWindow(settings)
    window.show()
    sys.exit(application.exec())
