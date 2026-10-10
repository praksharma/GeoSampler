"""Sampling controls and isolated background generation."""
import json
import sys
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QSpinBox, QLineEdit, QLabel, QPushButton, QHBoxLayout, QCheckBox, QMessageBox)
from .sampling_methods import METHODS


class SamplingPanel(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.process = None
        self.cancelled = False
        self.batches = []
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.target = QComboBox()
        self.target.addItem('Selected faces / edges', 'selection')
        self.target.addItem('Domain interior', 'interior')
        form.addRow('Target', self.target)
        self.method = QComboBox()
        for key, label in METHODS.items():
            self.method.addItem(label, key)
        form.addRow('Method', self.method)
        self.count = QSpinBox()
        self.count.setRange(1, 50000)
        self.count.setValue(1000)
        self.count.setToolTip('Total points across the target entities. Regular grid uses a candidate budget and may return fewer points.')
        form.addRow('Points / grid budget', self.count)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(42)
        form.addRow('Seed', self.seed)
        self.label = QLineEdit('boundary')
        form.addRow('Dataset label', self.label)
        self.resolution = QComboBox()
        for title, number in [('Standard', 32), ('Fine', 64)]:
            self.resolution.addItem(title, number)
        self.resolution.setToolTip('Independent sampling tessellation. Fine uses more memory and time; changing it changes the numerical domain approximation.')
        form.addRow('Geometry accuracy', self.resolution)
        layout.addLayout(form)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.note)
        row = QHBoxLayout()
        self.generate = QPushButton('Generate samples')
        self.generate.clicked.connect(self.start)
        self.cancel = QPushButton('Cancel')
        self.cancel.clicked.connect(self.stop)
        self.cancel.setEnabled(False)
        row.addWidget(self.generate);row.addWidget(self.cancel)
        layout.addLayout(row)
        self.show_points = QCheckBox('Show sample points')
        self.show_points.setChecked(True)
        self.show_points.toggled.connect(self.refresh_preview)
        layout.addWidget(self.show_points)
        self.through = QCheckBox('Show points through geometry')
        self.through.setChecked(True)
        self.through.toggled.connect(self.refresh_preview)
        layout.addWidget(self.through)
        self.clear = QPushButton('Clear generated datasets')
        self.clear.clicked.connect(self.clear_batches)
        layout.addWidget(self.clear)
        self.summary = QLabel('Open geometry to begin.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addStretch()
        self.method.currentIndexChanged.connect(self.update_note)
        self.target.currentIndexChanged.connect(self.update_note)
        self.update_note()
        self.generate.setEnabled(False)

    def update_note(self):
        text = 'Boundary coordinates follow the original curves/surfaces. Surface trim limits and 3D interiors use numerical geometry.'
        if self.method.currentData() == 'grid':
            text += '\nGrid clipping can reduce the point count; face grids are regular in surface parameters.'
        elif self.method.currentData() == 'sobol':
            text += '\nPrefer a power-of-two count for Sobol. Geometry mapping can alter sequence balance.'
        self.note.setText(text)

    def geometry_loaded(self):
        self.clear_batches()
        self.target.blockSignals(True)
        while self.target.count() > 2:
            self.target.removeItem(2)
        for group in self.window.geometry['groups']:
            if group['dimension'] in (1, 2):
                kind = 'edges' if group['dimension'] == 1 else 'faces'
                name = group['name'] or f"Group {group['tag']}"
                self.target.addItem(f'{name} ({kind})', {'dimension': group['dimension'], 'tags': group['entities']})
        self.target.blockSignals(False)
        self.generate.setEnabled(True)
        self.summary.setText('Select a target and generate a dataset.')

    def set_busy(self, busy):
        for control in (self.target, self.method, self.count, self.seed, self.label, self.resolution):
            control.setEnabled(not busy)
        self.generate.setEnabled(not busy and self.window.geometry is not None)
        self.cancel.setEnabled(busy)
        self.window.open_action.setEnabled(not busy)

    def start(self):
        if self.process or not self.window.geometry or self.window.import_process:
            return
        target = self.target.currentData()
        if isinstance(target, dict):
            entities = [[target['dimension'], t] for t in target['tags']]
            kind = 'group'
        else:
            entities = [list(key) for key in sorted(self.window.selection)]
            kind = target
        if kind != 'interior' and not entities:
            QMessageBox.information(self, 'Choose a sampling target', 'Select one or more faces/edges, choose an imported group, or choose Domain interior.')
            return
        label = self.label.text().strip()
        if not label:
            QMessageBox.information(self, 'Dataset label', 'Give this dataset a label before generating points.')
            return
        if any(batch['label'] == label for batch in self.batches):
            QMessageBox.information(self, 'Dataset label', 'This label already exists. Choose another label or clear the generated datasets.')
            return
        geometry = self.window.geometry
        request = {key: geometry[key] for key in ('source', 'source_hash', 'document')}
        request.update(target=kind, entities=entities, method=self.method.currentData(),
                       count=self.count.value(), seed=self.seed.value(), label=label,
                       resolution=self.resolution.currentData())
        process = QProcess(self)
        self.process = process
        self.cancelled = False
        self.set_busy(True)
        self.summary.setText('Generating samples…')
        self.window.statusBar().showMessage('Generating samples…')
        process.started.connect(lambda: self.write_request(process, request))
        process.finished.connect(lambda code, status: self.finished(process, code))
        process.errorOccurred.connect(lambda error: self.finished(process, -1) if error == QProcess.ProcessError.FailedToStart else None)
        process.start(sys.executable, ['-m', 'geosampler.sampling'])

    def write_request(self, process, request):
        process.write(json.dumps(request).encode())
        process.closeWriteChannel()

    def finished(self, process, code):
        if self.process is not process:
            return
        self.process = None
        self.set_busy(False)
        try:
            if self.cancelled:
                self.summary.setText('Generation cancelled. Existing datasets retained.')
                return
            if code:
                raise ValueError(bytes(process.readAllStandardError()).decode(errors='replace')[-2000:] or 'Sampling process could not start.')
            batch = json.loads(bytes(process.readAllStandardOutput()))
            if batch['document'] != self.window.geometry['document']:
                raise ValueError('The geometry changed during generation.')
            self.batches.append(batch)
            self.summary.setText(f"{batch['label']}: {batch['count']} points\n" + '\n'.join(batch['notes']))
            self.refresh_preview()
            self.window.results_dock.show()
            self.window.sample_results.setText('\n\n'.join(
                f"{b['label']} · {METHODS[b['method']]}\n{b['count']} points · Seed {b['seed']}\n" +
                ', '.join(f"{'Edge' if d == 1 else 'Face' if d == 2 else 'Volume'} {t}" for d, t in b['entities'])
                for b in self.batches))
            self.window.statusBar().showMessage(f"Generated {batch['count']} points for {batch['label']}")
        except (ValueError, KeyError) as error:
            self.summary.setText('Generation failed. Existing datasets retained.')
            QMessageBox.warning(self, 'Sampling failed', str(error))
        finally:
            process.deleteLater()

    def stop(self):
        if self.process:
            self.cancelled = True
            self.process.kill()

    def shutdown(self):
        if self.process:
            process = self.process
            self.process = None
            process.kill()
            process.waitForFinished(2000)

    def clear_batches(self):
        self.batches.clear()
        self.refresh_preview()
        self.window.sample_results.setText('No samples generated.')
        self.summary.setText('No generated datasets.')

    def refresh_preview(self):
        self.window.view.set_samples({'batches': self.batches,
                                     'visible': self.show_points.isChecked(),
                                     'through': self.through.isChecked()})
