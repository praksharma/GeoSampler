"""GeoSampler desktop shell, adapted from PyniteGUI's Qt layout."""
import argparse
import sys
from pathlib import Path
import json
from PySide6.QtCore import QProcess, QSettings, Qt, QSize, QSignalBlocker
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QLabel,
    QMainWindow, QMessageBox, QToolBar, QTreeWidget, QTreeWidgetItem, QFileDialog, QAbstractItemView, QScrollArea, QSizePolicy, QSplitter)
from . import __version__
from .theme import configure_theme
from .viewport import Viewport
from .graphics import configure_graphics
from .window_controls import install_window_controls
from .sampling_panel import SamplingPanel
from .sampled_areas import SampledAreasTree, area_details
from .icons import tool_icon


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("GeoSampler", "GeoSampler")
        self.geometry = None
        self.import_process = None
        self.selection = set()
        self.selected_area = None
        self.icon_actions = []
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
        self.export_action = file_menu.addAction("&Export samples…", self.export_samples, "Ctrl+Shift+S")
        self.export_action.setEnabled(False)
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")
        self.view_menu = self.menuBar().addMenu("&View")
        self.toolbar = QToolBar("Viewport", self)
        self.toolbar.setObjectName("viewport_toolbar")
        self.addToolBar(self.toolbar)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toolbar.setIconSize(QSize(24,24))
        for action, icon in ((self.open_action,'open'),(self.export_action,'export')):
            action.setToolTip(action.text().replace('&',''))
            self.icon_actions.append((action,icon))
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self.orientation = QComboBox()
        self.orientation.addItems(["Isometric", "Front XY", "Top XZ", "Right YZ", "Back XY", "Bottom XZ", "Left YZ", "Orbit"])
        self.orientation.model().item(7).setEnabled(False)
        self.orientation.setToolTip("Camera orientation")
        self.orientation.activated.connect(lambda index: self.view.call("orient", index))
        self.view.oriented.connect(self.orientation.setCurrentIndex)
        self.toolbar.addWidget(self.orientation)
        self.tool_action("Reset view", "reset", "Fit the geometry in the isometric view", lambda: self.view.call("reset"))
        self.toolbar.addSeparator()
        for label, attribute in (("Grid", "show_grid"), ("Axes", "show_axes")):
            action = self.tool_action(label, label.lower(), f"Show/hide {label.lower()}")
            action.setCheckable(True)
            action.setChecked(getattr(self.view, attribute))
            action.toggled.connect(lambda checked, attr=attribute: self.set_visibility(attr, checked))
        self.toolbar.addSeparator()
        self.selection_tools = QActionGroup(self)
        self.selection_actions = {}
        for mode, label, shortcut in (("face", "Select faces", "F"), ("edge", "Select edges", "E")):
            action = self.tool_action(label, mode, label)
            action.setCheckable(True)
            action.setChecked(mode == "face")
            action.setShortcut(shortcut)
            action.setToolTip(label + " — click to select; Ctrl/Shift-click to add; drag to orbit")
            action.triggered.connect(lambda checked=False, mode=mode: self.set_selection_mode(mode))
            self.selection_tools.addAction(action)
            self.selection_actions[mode] = action
        self.tool_action("Clear selection", "clear", "Clear CAD entity selection (Esc)", self.clear_selection).setShortcut("Esc")
        self.toolbar.addSeparator()
        visibility_menu = self.view_menu.addMenu('Visibility')
        self.visibility_actions = {}
        for key, label, icon, hint in (
            ('geometry','Geometry','geometry','Show/hide all geometry without changing selections'),
            ('faces','Faces','faces','Show/hide shaded faces; keep enabled edges'),
            ('edges','Edges','edges','Show/hide edges and their highlights')):
            action = self.tool_action(label,icon,hint)
            action.setCheckable(True);action.setChecked(True)
            action.toggled.connect(lambda checked, key=key: self.view.set_geometry_visibility({key:checked}))
            self.visibility_actions[key] = action
            visibility_menu.addAction(action)
        self.samples_action = self.tool_action('All samples','samples','Show/hide all generated sample points')
        self.samples_action.setCheckable(True);self.samples_action.setChecked(True)
        visibility_menu.addAction(self.samples_action)
        self.region_samples_action = self.tool_action('Selected region samples','region','Show/hide only the selected Sampled Areas region')
        self.region_samples_action.setCheckable(True);self.region_samples_action.setEnabled(False)
        self.region_samples_action.toggled.connect(self.set_region_samples_visible)
        visibility_menu.addAction(self.region_samples_action)
        self.toolbar.addSeparator();visibility_menu.addSeparator()
        self.isolate_action = self.tool_action('Isolate region','isolate','Isolate the selected Sampled Areas label; toggle off to restore visibility')
        self.isolate_action.setCheckable(True);self.isolate_action.setEnabled(False)
        self.isolate_action.toggled.connect(self.update_isolation)
        self.isolate_geometry_action = self.tool_action('Geometry in isolation','context','Include only the isolated region’s geometry; otherwise show its points alone')
        self.isolate_geometry_action.setCheckable(True)
        self.isolate_geometry_action.setEnabled(False)
        self.isolate_geometry_action.toggled.connect(self.update_isolation)
        visibility_menu.addAction(self.isolate_action);visibility_menu.addAction(self.isolate_geometry_action)
        self.view.picked.connect(self.pick_entity)
        tree = QTreeWidget()
        self.tree = tree
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.itemSelectionChanged.connect(self.tree_selection_changed)
        tree.setHeaderHidden(True)
        tree.addTopLevelItems([QTreeWidgetItem(["Geometry"]), QTreeWidgetItem(["Regions"])])
        self.sampled_areas = SampledAreasTree()
        self.sampled_areas.areaSelected.connect(self.show_sampled_area)
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.addWidget(tree)
        self.left_splitter.addWidget(self.sampled_areas)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.setSizes([350, 350])
        self.geometry_dock = self.dock("Geometry and Sampled Areas", "geometry", self.left_splitter, Qt.DockWidgetArea.LeftDockWidgetArea)
        properties = QLabel("No geometry selected.")
        self.properties = properties
        properties.setWordWrap(True)
        properties.setTextFormat(Qt.TextFormat.PlainText)
        properties.setMargin(16)
        properties.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.properties_dock = self.dock("Properties", "properties", self.scrollable_text(properties), Qt.DockWidgetArea.RightDockWidgetArea)
        self.sampling = SamplingPanel(self)
        self.samples_action.toggled.connect(self.sampling.show_points.setChecked)
        self.sampling.show_points.toggled.connect(self.samples_action.setChecked)
        self.sampled_areas.visibilityChanged.connect(self.sampling.refresh_style)
        self.sampled_areas.visibilityChanged.connect(self.sync_region_visibility)
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
        self.refresh_icons()

    def tool_action(self, title, icon, tooltip, callback=None):
        action = self.toolbar.addAction(title)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        if callback:
            action.triggered.connect(callback)
        self.icon_actions.append((action,icon))
        return action

    def refresh_icons(self):
        colour = self.palette().windowText().color().name()
        for action, name in self.icon_actions:
            action.setIcon(tool_icon(name,colour))

    def sync_region_visibility(self):
        item = self.sampled_areas.items.get(self.selected_area)
        generated = bool(item and self.sampled_areas.areas[self.selected_area][1]=='Generated')
        self.region_samples_action.setEnabled(generated)
        with QSignalBlocker(self.region_samples_action):
            self.region_samples_action.setChecked(generated and item.checkState(0)==Qt.CheckState.Checked)

    def set_region_samples_visible(self, visible):
        if self.selected_area in self.sampled_areas.items:
            self.sampled_areas.items[self.selected_area].setCheckState(0,Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)

    def isolated_label(self):
        return self.selected_area if self.isolate_action.isChecked() else None

    def clear_isolation(self):
        self.selected_area = None
        self.isolate_action.setChecked(False)
        self.isolate_action.setEnabled(False)
        self.region_samples_action.setEnabled(False)
        with QSignalBlocker(self.region_samples_action):
            self.region_samples_action.setChecked(False)
        self.view.set_geometry_visibility({'isolatedEntities':None})

    def update_isolation(self):
        self.isolate_geometry_action.setEnabled(self.isolate_action.isChecked())
        entities = None
        label = self.isolated_label()
        if label:
            area, status = self.sampled_areas.areas[label]
            entities = []
            if self.isolate_geometry_action.isChecked():
                entities = [list(key) for key in area['entities']]
                if area['entity_dimension'] == 3:
                    # Interior generation currently targets all domain volumes.
                    entities = [[e['dimension'],e['tag']] for e in self.geometry['entities']]
                else:
                    keys = {tuple(key) for key in entities}
                    entities += [boundary for e in self.geometry['entities']
                                 if (e['dimension'],e['tag']) in keys for boundary in e['boundary'] if boundary[0]==1]
        self.view.set_geometry_visibility({'isolatedEntities':entities})
        if hasattr(self,'sampling'):
            self.sampling.refresh_style()

    @staticmethod
    def scrollable_text(label):
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(label)
        return scroll

    def dock(self, title, name, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())
        return dock

    def show_sampled_area(self, label):
        area, status = self.sampled_areas.areas[label]
        self.selected_area = label
        self.sync_region_visibility()
        if status != 'Generated':
            self.isolate_action.setChecked(False)
        self.isolate_action.setEnabled(status == 'Generated')
        if self.isolate_action.isChecked():
            self.update_isolation()
        text = label + '\n\n' + '\n'.join(area_details(area, status))
        if area.get('notes'):
            text += '\n\n' + '\n'.join(area['notes'])
        self.properties.setText(text)
        self.properties_dock.raise_()

    def export_samples(self):
        if not self.sampling.batches or self.sampling.process:
            return
        directory = self.settings.value('export/directory', str(Path.home()))
        stem = Path(self.geometry['source']).stem if self.geometry else 'geometry'
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, 'Export samples', str(Path(directory) / f'{stem}_samples'),
            'NetCDF (*.nc);;NumPy archive (*.npz)')
        if not filename:
            return
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix('.npz' if 'npz' in selected_filter else '.nc')
        try:
            # Keep scientific data dependencies out of application startup.
            from .export import export_samples
            export_samples(self.sampling.batches, path)
        except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
            QMessageBox.warning(self, 'Export failed', str(error))
            return
        self.settings.setValue('export/directory', str(path.parent))
        self.statusBar().showMessage(f'Exported {len(self.sampling.batches)} datasets to {path}')

    def set_visibility(self, attribute, checked):
        setattr(self.view, attribute, checked)
        self.view.apply_theme()

    def reset_layout(self):
        for dock, area in ((self.geometry_dock, Qt.DockWidgetArea.LeftDockWidgetArea),
                           (self.properties_dock, Qt.DockWidgetArea.RightDockWidgetArea)):
            dock.setFloating(False)
            self.addDockWidget(area, dock)
            dock.show()
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
        self.refresh_icons()

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
