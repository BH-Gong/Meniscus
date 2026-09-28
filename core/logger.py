from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from core import shared_data

class Logger(QObject):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    warning_signal = pyqtSignal(str)
    hidden_signal = pyqtSignal(str)

    def __init__(self, text_box):
        super().__init__()
        self.text_box = text_box
        self.show_hidden = shared_data.show_hidden_logs
        self.logs = []

        self.log_signal.connect(self._log)
        self.error_signal.connect(self._error)
        self.warning_signal.connect(self._warning)
        self.hidden_signal.connect(self._hidden)

    def log(self, message):
        self.log_signal.emit(str(message))

    def error(self, message):
        self.error_signal.emit(str(message))

    def warning(self, message):
        self.warning_signal.emit(str(message))

    def hidden(self, message):
        self.hidden_signal.emit(str(message))

    def _log(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")

        self.logs.append(("log", time, message))
        self._refresh()

    def _error(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")

        self.logs.append(("error", time, message))
        self._refresh()

    def _warning(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")

        self.logs.append(("warning", time, message))
        self._refresh()

    def _hidden(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")

        self.logs.append(("hidden", time, message))
        self._refresh()

    def _refresh(self):
        self.text_box.clear()

        for log_type, time, message in self.logs:
            if log_type == "hidden" and not self.show_hidden:
                continue

            if log_type == "log":
                html = (f"<span style='color:yellow;'>[{time}]</span> - {message}")

            elif log_type == "error":
                html = (f"<span style='color:yellow;'>[{time}]</span> - <span style='color:red;'>{message}</span>")

            elif log_type == "warning":
                html = (f"<span style='color:yellow;'>[{time}]</span> - <span style='color:yellow;'>{message}</span>")

            elif log_type == "hidden":
                html = (f"<span style='color:yellow;'>[{time}]</span> - <span style='color:gray;'>{message}</span>")

            self.text_box.append(html)