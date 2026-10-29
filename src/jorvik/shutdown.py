"""Deliver terminal shutdown requests through Qt instead of raising in its callbacks."""
import signal
from PySide6.QtCore import QTimer


class SignalShutdown:
    def __init__(self):
        self.timer = None
        self.window = None
        self.pending = False
        self.handling = False
        self.previous = {}
        for number in (signal.SIGINT, signal.SIGTERM):
            self.previous[number] = signal.signal(number, self.request)

    def start(self, application):
        # Python needs regular interpreter entry while QApplication.exec runs in C++.
        self.timer = QTimer(application)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def request(self, number, frame):
        # Never raise KeyboardInterrupt or re-enter Qt from a Python signal handler.
        self.pending = True

    def poll(self):
        if not self.pending or self.handling or self.window is None:
            return
        self.pending = False
        self.handling = True
        try:
            self.window.close()
        finally:
            self.handling = False

    def restore(self, terminating=False):
        if self.timer is not None:
            self.timer.stop()
        for number, previous in self.previous.items():
            # uv can forward a second SIGINT after a terminal process-group signal.
            # Once the GUI has exited, use native termination instead of raising
            # a late KeyboardInterrupt inside Python/Qt interpreter finalizers.
            if terminating and number == signal.SIGINT and previous == signal.default_int_handler:
                previous = signal.SIG_DFL
            signal.signal(number, previous)
        self.previous.clear()
