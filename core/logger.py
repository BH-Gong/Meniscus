from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class Logger(QObject):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    warning_signal = pyqtSignal(str)

    def __init__(self, text_box):
        super().__init__()
        self.text_box = text_box
        self.log_signal.connect(self._log)
        self.error_signal.connect(self._error)
        self.warning_signal.connect(self._warning)

    def log(self, message):
        self.log_signal.emit(str(message))

    def error(self, message):
        self.error_signal.emit(str(message))

    def warning(self, message):
        self.warning_signal.emit(str(message))

    def _log(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")
        self.text_box.append(f"<span style='color:yellow;'>[{time}]</span> - {message}")
        self.text_box.verticalScrollBar().setValue(
            self.text_box.verticalScrollBar().maximum()
        )

    def _error(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")
        self.text_box.append(f"<span style='color:yellow;'>[{time}]</span> - <span style='color:red;'>{message}</span>")
        self.text_box.verticalScrollBar().setValue(
            self.text_box.verticalScrollBar().maximum()
        )

    def _warning(self, message):
        time = QTime.currentTime().toString("hh:mm:ss")
        self.text_box.append(f"<span style='color:yellow;'>[{time}]</span> - <span style='color:yellow;'>{message}</span>")
        self.text_box.verticalScrollBar().setValue(
            self.text_box.verticalScrollBar().maximum()
        )