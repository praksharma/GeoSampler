"""Atomic recovery copies for interrupted sessions, with per-window ownership."""
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import QLockFile, QSettings, QStandardPaths, QTimer, Qt
from PySide6.QtWidgets import QMessageBox
from .project import save_project, PROJECT_EXTENSION, PROJECT_EXTENSIONS


class RecoveryActions:
    def initialize_recovery(self):
        if self.settings.format() == QSettings.Format.IniFormat:
            self.recovery_directory = Path(self.settings.fileName()).parent / 'recovery'
        else:
            self.recovery_directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'recovery'
        self.recovery_path = self.recovery_directory / (uuid4().hex + PROJECT_EXTENSION)
        self.recovery_lock = None
        self.recovered_from = None
        self.recovery_digest = None
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setInterval(120000)
        self.recovery_timer.timeout.connect(self.autosave)
        self.recovery_timer.start()
        QTimer.singleShot(0, self.offer_recovery)

    def clear_recovery(self):
        for path in (self.recovery_path, self.recovered_from):
            if path is not None:
                try: path.unlink(missing_ok=True)
                except OSError as error: self.statusBar().showMessage('Could not remove recovery copy: ' + str(error))
        if self.recovery_lock is not None:
            self.recovery_lock.unlock()
            self.recovery_lock = None
        self.recovered_from = None
        self.recovery_digest = None

    def autosave(self):
        if not self.geometry or self.project_busy(): return False
        digest = self.workspace_digest()
        if digest == self.saved_digest:
            self.clear_recovery()
            return False
        if digest == self.recovery_digest and self.recovery_path.is_file(): return True
        try:
            self.recovery_directory.mkdir(parents=True, exist_ok=True)
            if self.recovery_lock is None:
                lock = QLockFile(str(self.recovery_path) + '.lock')
                lock.setStaleLockTime(0)
                if not lock.tryLock(0): raise OSError('The recovery copy is locked by another session.')
                self.recovery_lock = lock
            state = self.project_state()
            state['recovery_origin'] = str(self.project_path) if self.project_path else None
            areas = [(area,status,self.sampled_areas.items[label].checkState(0) == Qt.CheckState.Checked)
                     for label,(area,status) in self.sampled_areas.areas.items()]
            self.project_io_call(lambda: save_project(self.recovery_path,self.geometry,areas,state))
            self.recovery_digest = digest
            if self.recovered_from is not None and self.recovered_from != self.recovery_path:
                self.recovered_from.unlink(missing_ok=True)
                self.recovered_from = None
            self.statusBar().showMessage('Recovery copy saved; use Save project to keep your changes.')
            return True
        except Exception as error:
            self.statusBar().showMessage('Recovery copy failed; previous copy retained: ' + str(error))
            return False

    def offer_recovery(self):
        if not self.isVisible(): return
        if self.project_busy():
            QTimer.singleShot(1000, self.offer_recovery)
            return
        if not self.recovery_directory.is_dir(): return
        for path in sorted(self.recovery_directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in PROJECT_EXTENSIONS: continue
            if path == self.recovery_path: continue
            lock = QLockFile(str(path) + '.lock')
            lock.setStaleLockTime(0)
            if not lock.tryLock(0): continue  # A live window owns this copy.
            try:
                answer = QMessageBox.question(self, 'Recover interrupted session',
                    'A recovery copy from an interrupted session is available. Recover it now?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes)
                if answer == QMessageBox.StandardButton.Cancel: return
                if answer == QMessageBox.StandardButton.Yes:
                    if self.load_project_file(path):
                        self.autosave()  # Transfer to this window before deleting the old copy.
                        return
                elif answer == QMessageBox.StandardButton.No:
                    path.unlink(missing_ok=True)
            finally:
                lock.unlock()
