"""One bounded project I/O job; no widgets or geometry kernel objects in workers."""
from PySide6.QtCore import QThread


class ProjectWorker(QThread):
    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.operation()
        except Exception as error:
            self.error = error
        finally:
            self.operation = None
