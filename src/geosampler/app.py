"""GeoSampler desktop shell, adapted from PyniteGUI's Qt layout."""
import argparse
import sys
from pathlib import Path
import json
from PySide6.QtCore import QProcess, QSettings, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QLabel,
    QMainWindow, QMessageBox, QToolBar, QTreeWidget, QTreeWidgetItem, QFileDialog, QAbstractItemView)
from . import __version__
from .theme import configure_theme
from .viewport import Viewport
from .graphics import configure_graphics
from .window_controls import install_window_controls
from .sampling_panel import SamplingPanel


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("GeoSampler", "GeoSampler")
        self.geometry = None
        self.import_process = None
        self.selection = set()
        self.items = {}
        self.setWindowTitle("GeoSampler — Untitled")
        self.resize(1280, 820)
        self.setMinimumSize(820, 560)
        self.view = Viewport(self)
        self.setCentralWidget(self.view)
        self.statusBar().showMessage("Starting 3D viewport…")
        self.view.status.connect(self.statusBar().showMessage)
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = file_menu.addAction("&Open Geometry…", self.open_geometry, "Ctrl+O")
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
        self.toolbar.addSeparator()
        self.selection_tools = QActionGroup(self)
        self.selection_actions = {}
        for mode, label, shortcut in (("face", "Select faces", "F"), ("edge", "Select edges", "E")):
            action = self.toolbar.addAction(label)
            action.setCheckable(True)
            action.setChecked(mode == "face")
            action.setShortcut(shortcut)
            action.setToolTip(label + " — click to select; Ctrl/Shift-click to add; drag to orbit")
            action.triggered.connect(lambda checked=False, mode=mode: self.set_selection_mode(mode))
            self.selection_tools.addAction(action)
            self.selection_actions[mode] = action
        self.toolbar.addAction("Clear selection", self.clear_selection).setShortcut("Esc")
        self.view.picked.connect(self.pick_entity)
        tree = QTreeWidget()
        self.tree = tree
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.itemSelectionChanged.connect(self.tree_selection_changed)
        tree.setHeaderHidden(True)
        tree.addTopLevelItems([QTreeWidgetItem(["Geometry"]), QTreeWidgetItem(["Regions"])])
        self.geometry_dock = self.dock("Geometry and Regions", "geometry", tree, Qt.DockWidgetArea.LeftDockWidgetArea)
        properties = QLabel("No geometry selected.")
        self.properties = properties
        properties.setWordWrap(True)
        properties.setTextFormat(Qt.TextFormat.PlainText)
        properties.setMargin(16)
        properties.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.properties_dock = self.dock("Properties", "properties", properties, Qt.DockWidgetArea.RightDockWidgetArea)
        results = QLabel("No samples generated.")
        self.sample_results = results
        results.setWordWrap(True)
        results.setTextFormat(Qt.TextFormat.PlainText)
        results.setMargin(16)
        self.results_dock = self.dock("Results", "results", results, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.results_dock.hide()
        self.sampling = SamplingPanel(self)
        self.sampling_dock = self.dock("Sampling", "sampling", self.sampling, Qt.DockWidgetArea.RightDockWidgetArea)
        self.tabifyDockWidget(self.properties_dock, self.sampling_dock)
        self.sampling_dock.raise_()
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
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Graphics information", self.graphics_information)
        help_menu.addAction("About GeoSampler", self.about)
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
        self.sampling_dock.setFloating(False)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sampling_dock)
        self.tabifyDockWidget(self.properties_dock, self.sampling_dock)
        self.sampling_dock.show()
        self.sampling_dock.raise_()
        self.resizeDocks([self.geometry_dock, self.properties_dock], [240, 260], Qt.Orientation.Horizontal)

    def set_theme(self, name):
        configure_theme(QApplication.instance(), name)
        self.settings.setValue("theme", name)

    def apply_theme(self):
        self.view.apply_theme()

    def graphics_information(self):
        if not self.view.is_ready:
            QMessageBox.information(self, "Graphics information", "The 3D renderer is not ready.")
            return
        def received(value):
            try:
                info = json.loads(value)
                text = f"Renderer: {info['renderer']}\n\nVendor: {info['vendor']}\n\n{info['version']}"
                if info['lost']:
                    text += "\n\nGraphics context lost."
            except (TypeError, ValueError, KeyError):
                text = "Renderer information is unavailable."
            QMessageBox.information(self, "Graphics information", text)
        self.view.web.page().runJavaScript("JSON.stringify(window.geoViewer.diagnostics())", received)

    def about(self):
        QMessageBox.about(self, "About GeoSampler", f"GeoSampler {__version__}\nGeometry-aware sampling for PINNs.\n\nGmsh geometry import with face and edge selection. Seven sampling methods with boundary/interior previews.\nAdapted from PyniteGUI; licensed under AGPL-3.0-only.\nThree.js is distributed under its MIT licence.")

    def open_geometry(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open geometry", "", "Gmsh geometry (*.geo)")
        if path:
            self.load_geometry(path)

    def load_geometry(self, path):
        if self.import_process is not None or self.sampling.process is not None:
            return
        process = QProcess(self)
        self.import_process = process
        self.open_action.setEnabled(False)
        self.sampling.generate.setEnabled(False)
        self.statusBar().showMessage("Opening " + Path(path).name + "…")
        process.finished.connect(lambda code, status: self.import_finished(process, code))
        process.errorOccurred.connect(lambda error: self.import_failed_start(process) if error == QProcess.ProcessError.FailedToStart else None)
        process.start(sys.executable, ["-m", "geosampler.geometry", str(path)])

    def import_failed_start(self, process):
        if self.import_process is process:
            self.import_finished(process, -1)

    def import_finished(self, process, code):
        if self.import_process is not process:
            return
        self.import_process = None
        self.open_action.setEnabled(True)
        self.sampling.generate.setEnabled(self.geometry is not None)
        try:
            if code:
                raise ValueError(bytes(process.readAllStandardError()).decode(errors="replace")[-2000:] or "Geometry loader could not start.")
            geometry = json.loads(bytes(process.readAllStandardOutput()))
            self.show_geometry(geometry)
        except (ValueError, KeyError) as error:
            self.statusBar().showMessage("Import failed — previous geometry retained")
            QMessageBox.warning(self, "Could not open geometry", str(error))
        finally:
            process.deleteLater()

    def show_geometry(self, geometry):
        self.geometry = geometry
        self.selection.clear()
        self.items.clear()
        self.tree.blockSignals(True)
        self.tree.clear()
        parent = QTreeWidgetItem(self.tree, [geometry["name"]])
        for dimension, label in ((2, "Faces"), (1, "Edges")):
            group = QTreeWidgetItem(parent, [label])
            for entity in geometry["entities"]:
                if entity["dimension"] != dimension:
                    continue
                key = (dimension, entity["tag"])
                item = QTreeWidgetItem(group, [f"{label[:-1]} {key[1]} · {entity['type']}"])
                item.setData(0, Qt.ItemDataRole.UserRole, key)
                self.items[key] = item
        regions = QTreeWidgetItem(self.tree, ["Imported groups"])
        for group in geometry["groups"]:
            if group["dimension"] in (1, 2):
                label = group["name"] or f"Group {group['tag']}"
                item = QTreeWidgetItem(regions, [f"{label} · {'edges' if group['dimension'] == 1 else 'faces'}"])
                item.setToolTip(0, "Entities: " + ", ".join(map(str, group["entities"])))
        parent.setExpanded(True)
        self.tree.blockSignals(False)
        self.view.set_geometry(geometry)
        self.sampling.geometry_loaded()
        self.setWindowTitle("GeoSampler — " + geometry["name"])
        self.update_selection()
        faces = sum(e["dimension"] == 2 for e in geometry["entities"])
        edges = sum(e["dimension"] == 1 for e in geometry["entities"])
        self.statusBar().showMessage(f"{geometry['name']} | {faces} faces · {edges} edges | {self.view.mode.title()} selection")

    def set_selection_mode(self, mode):
        self.view.set_mode(mode)
        self.selection_actions[mode].setChecked(True)
        self.clear_selection()
        self.statusBar().showMessage(f"Select {mode}s | Click to select · Ctrl/Shift-click to add · Drag to orbit")

    def pick_entity(self, dimension, tag, extend):
        key = (dimension, tag)
        if key not in self.items:
            if not extend:
                self.clear_selection()
            return
        if dimension != (2 if self.view.mode == "face" else 1):
            return
        if extend:
            self.selection.symmetric_difference_update({key})
        else:
            self.selection = {key}
        self.update_selection()

    def clear_selection(self):
        self.selection.clear()
        self.update_selection()

    def tree_selection_changed(self):
        keys = {tuple(item.data(0, Qt.ItemDataRole.UserRole)) for item in self.tree.selectedItems()
                if item.data(0, Qt.ItemDataRole.UserRole)}
        current = self.tree.currentItem()
        key = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        if key:
            mode = "face" if key[0] == 2 else "edge"
            self.view.set_mode(mode)
            self.selection_actions[mode].setChecked(True)
        dimension = 2 if self.view.mode == "face" else 1
        self.selection = {key for key in keys if key[0] == dimension}
        self.update_selection()

    def update_selection(self):
        self.tree.blockSignals(True)
        for key, item in self.items.items():
            item.setSelected(key in self.selection)
            if key in self.selection:
                item.parent().setExpanded(True)
        self.tree.blockSignals(False)
        self.view.set_selection([list(key) for key in sorted(self.selection)])
        if not self.selection:
            self.properties.setText("No entity selected.\n\nChoose Select faces (F) or Select edges (E), then click the geometry.")
            return
        lines = [f"{len(self.selection)} selected"]
        for entity in self.geometry["entities"]:
            if (entity["dimension"], entity["tag"]) in self.selection:
                kind = "Face" if entity["dimension"] == 2 else "Edge"
                lines.append(f"\n{kind} {entity['tag']}\nType: {entity['type']}\nGroups: {', '.join(map(str, entity['groups'])) or 'None'}")
        self.properties.setText("\n".join(lines))

    def closeEvent(self, event):
        self.sampling.shutdown()
        if self.import_process:
            process = self.import_process
            self.import_process = None
            process.kill()
            process.waitForFinished(2000)

        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("layout", self.saveState())
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="GeoSampler desktop application")
    parser.add_argument("geometry", nargs="?", help="Gmsh .geo file to open")
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
    if args.geometry:
        window.load_geometry(args.geometry)
    sys.exit(application.exec())
