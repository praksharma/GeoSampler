"""Explicit single-configuration processing workspace; no automatic computation."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QComboBox, QDoubleSpinBox, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QHBoxLayout, QFileDialog, QMessageBox)
from pathlib import Path
from .parametrisation import export_configuration, validate_setup, save_setup, load_setup


class ParametrisationDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle('Parametrisation — Translation')
        self.resize(560, 480)
        self.setModal(False)
        self.source_hash = window.geometry['source_hash'] if window.geometry else None
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        parameters = QWidget(); form = QFormLayout(parameters)
        self.scope = QComboBox()
        self.scope.addItem('Whole domain — consistent translation', 'domain')
        self.scope.addItem('Selected regions — dataset augmentation', 'regions')
        form.addRow('Scope', self.scope)
        self.offsets = []
        for axis in 'XYZ':
            spin = QDoubleSpinBox(); spin.setDecimals(8); spin.setRange(-1e12, 1e12)
            self.offsets.append(spin)
            form.addRow(f'Translation {axis}', spin)
        form.addRow(QLabel('Distances use the source geometry units.'))
        self.regions = QListWidget()
        for batch in window.sampling.batches:
            item = QListWidgetItem(batch['label'], self.regions)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if batch['label'] == window.selected_area else Qt.CheckState.Unchecked)
        form.addRow('Affected regions', self.regions)
        self.warning = QLabel(''); self.warning.setWordWrap(True); form.addRow(self.warning)
        self.scope.currentIndexChanged.connect(self.scope_changed)
        self.scope_changed()
        self.tabs.addTab(parameters, 'Parameters')
        combinations = QWidget(); box = QVBoxLayout(combinations)
        text = QLabel('One configuration uses the three translation values in Parameters.\n\nParameter ranges and Cartesian/LHS/Sobol sweeps will be added in a later stage.')
        text.setWordWrap(True); box.addWidget(text); box.addStretch()
        self.tabs.addTab(combinations, 'Combinations')
        processing = QWidget(); box = QVBoxLayout(processing)
        text = QLabel('Preview explicitly applies one configuration to the viewport. Original geometry and sampled datasets stay unchanged. Restore or close this workspace to return to the originals.')
        text.setWordWrap(True); box.addWidget(text)
        self.preview_button = QPushButton('Preview configuration'); self.preview_button.clicked.connect(self.preview)
        box.addWidget(self.preview_button)
        button = QPushButton('Restore original view'); button.clicked.connect(self.restore); box.addWidget(button)
        self.status = QLabel('Not processed.'); self.status.setWordWrap(True); box.addStretch()
        self.tabs.addTab(processing, 'Processing')
        export = QWidget(); box = QVBoxLayout(export)
        text = QLabel('Process the current configuration from the original samples and export every region to NetCDF or NPZ. Parameter values, scope and original sampling metadata are retained. Hidden regions are included.')
        text.setWordWrap(True); box.addWidget(text)
        self.export_button = QPushButton('Process configuration and export…')
        self.export_button.clicked.connect(self.export_configuration); box.addWidget(self.export_button); box.addStretch()
        self.tabs.addTab(export, 'Export')
        layout.addWidget(self.status)
        for spin in self.offsets:
            spin.valueChanged.connect(self.mark_changed)
        self.scope.currentIndexChanged.connect(self.mark_changed)
        self.regions.itemChanged.connect(self.mark_changed)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        for title, callback in [('Save setup…', self.save), ('Load setup…', self.load), ('Close', self.close)]:
            button = QPushButton(title); button.clicked.connect(callback); buttons.addWidget(button)

    def mark_changed(self):
        if self.window.view.translation_preview is not None:
            self.status.setText('Parameters changed. The viewport still shows the previous preview; click Preview configuration to update.')

    def scope_changed(self):
        regions = self.scope.currentData() == 'regions'
        self.regions.setEnabled(regions)
        self.warning.setText('Only checked point clouds move. CAD geometry stays fixed; boundary/interior consistency is unverified.' if regions else 'Geometry display and all sampled regions translate together. The source CAD file is unchanged.')

    def setup(self):
        return {'schema_version': 1, 'scope': self.scope.currentData(),
                'translation': [spin.value() for spin in self.offsets],
                'regions': [self.regions.item(i).text() for i in range(self.regions.count())
                            if self.regions.item(i).checkState() == Qt.CheckState.Checked],
                'source_hash': self.source_hash}

    def report_error(self, error):
        QMessageBox.warning(self, 'Parametrisation', str(error))

    def preview(self):
        try:
            setup = self.setup()
            validate_setup(setup, self.window.sampling.batches)
            self.window.view.set_translation_preview(setup)
            self.status.setText('Preview active — original datasets unchanged. Export processes these parameter values independently.')
        except (ValueError, TypeError) as error:
            self.report_error(error)

    def restore(self):
        self.window.view.set_translation_preview(None)
        self.status.setText('Original view restored.')

    def done(self, result):
        self.restore()
        super().done(result)

    def closeEvent(self, event):
        self.restore()
        super().closeEvent(event)

    def export_configuration(self):
        try:
            setup = self.setup()
            validate_setup(setup, self.window.sampling.batches)
            filename, selected = QFileDialog.getSaveFileName(self, 'Export translated configuration', 'translated_samples.nc', 'NetCDF (*.nc);;NumPy archive (*.npz)')
            if not filename:
                return
            path = Path(filename)
            if not path.suffix:
                path = path.with_suffix('.npz' if 'npz' in selected else '.nc')
            export_configuration(self.window.sampling.batches, setup, path)
            self.status.setText(f'Processed 1 configuration. Exported to {path}')
        except (ValueError, TypeError, OSError) as error:
            self.report_error(error)

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save parametrisation setup', 'parametrisation.json', 'JSON (*.json)')
        if filename:
            try:
                path = Path(filename)
                save_setup(self.setup(), path if path.suffix else path.with_suffix('.json'))
            except (ValueError, TypeError, OSError) as error:
                self.report_error(error)

    def load(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Load parametrisation setup', '', 'JSON (*.json)')
        if filename:
            try:
                setup = load_setup(filename)
                validate_setup(setup, self.window.sampling.batches)
                # Check representable values before changing any controls.
                if any(abs(value) > 1e12 for value in setup['translation']):
                    raise ValueError('Translation exceeds the supported range.')
                self.restore()
                self.scope.setCurrentIndex(self.scope.findData(setup['scope']))
                for spin, value in zip(self.offsets, setup['translation']): spin.setValue(value)
                for i in range(self.regions.count()):
                    item = self.regions.item(i)
                    item.setCheckState(Qt.CheckState.Checked if item.text() in setup['regions'] else Qt.CheckState.Unchecked)
                self.source_hash = setup['source_hash']
                self.status.setText('Setup loaded. Preview or process explicitly.')
            except (ValueError, TypeError, OSError) as error:
                self.report_error(error)
