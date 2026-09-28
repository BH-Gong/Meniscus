from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import sys
from PIL import Image, ImageTk
import threading
import os

from GUIs.serial_GUI import Serial_Selection
from GUIs.control_GUI import ControlGUI
from GUIs.actuate_GUI import ActuateGUI
from core.serial_ports import SerialPorts
from core import shared_data
from core.libCRUX import CRUX
from core import utils
from core.logger import Logger

'''
ㄴMainWindow
    ㄴMenu Bar
        ㄴFile
            ㄴExit
        ㄴEdit
            ㄴSerial Window
            ㄴControl Window
            ㄴText Clear
            ㄴSave Log
        ㄴControl
            ㄴEmergency Stop
        ㄴSetting 추가 필요
            ㄴHidden 보이기 설정 추가 필요
    ㄴCentralWidget
        ㄴFunction Panel
            ㄴSerial Window Button
            ㄴControl Window Button
            ㄴG-code Window Button
            ㄴText Clear Button
            ㄴQuit Button
        ㄴStatus Panel
            ㄴLogger
        ㄴDisplay Panel
            ㄴSerial Window
            ㄴControl Window
            ㄴG-code Window

f'# {기능명}'로 주석 검색하여 색인 가능
'''

class MainGUI:
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.app = app
        self.initUI(self.win)

    def initUI(self, MainWindow):
        # MainWindow
        MainWindow.setObjectName("MainGUI")
        MainWindow.resize(1600, 900)
        MainWindow.move(0, 0)
        MainWindow.showMaximized()
        MainWindow.setStyleSheet("background-color: #222222;")
        MainWindow.setFont(QFont('Arial', 16))

        # Menu Bar
        self.menubar = QMenuBar()
        MainWindow.setMenuBar(self.menubar)
        self.menubar.setStyleSheet(utils.menubar_style())
        self.menubar.setFont(QFont('Arial', 12))

        # File
        self.file = QMenu("File", self.menubar)
        self.file.setStyleSheet(utils.menu_style())
        self.file.setFont(QFont('Arial', 12))
        self.menubar.addMenu(self.file)
        
        # Exit
        self.action_exit = QAction("Exit", MainWindow)
        self.action_exit.triggered.connect(self.close_func)
        self.action_exit.setShortcut("Ctrl+Q")
        self.file.addAction(self.action_exit)

        # Edit
        self.edit = QMenu("Edit", self.menubar)
        self.edit.setStyleSheet(utils.menu_style())
        self.edit.setFont(QFont('Arial', 12))
        self.menubar.addMenu(self.edit)

        # Serial Window
        self.action_serial = QAction("Serial Window", MainWindow)
        self.action_serial.triggered.connect(self.open_serial_window)
        self.action_serial.setShortcut("Ctrl+S")
        self.edit.addAction(self.action_serial)

        # Control Window
        self.action_control = QAction("Control Window", MainWindow)
        self.action_control.triggered.connect(self.open_control_window)
        self.action_control.setShortcut("Ctrl+T")
        self.edit.addAction(self.action_control)

        # G-code Window
        self.gcode = QAction("G-code Window", MainWindow)
        self.gcode.triggered.connect(self.open_g_code_window)
        self.gcode.setShortcut("Ctrl+G")
        self.edit.addAction(self.gcode)

        # Text Clear
        self.action_clear = QAction("Text Clear", MainWindow)
        self.action_clear.triggered.connect(self.text_box_clear)
        self.action_clear.setShortcut("Ctrl+R")
        self.edit.addAction(self.action_clear)

        # Save Log
        self.save_log = QAction("Save Log", MainWindow)
        self.save_log.triggered.connect(self.save_log_file)
        self.edit.addAction(self.save_log)

        # Control
        self.control = QMenu("Control", self.menubar)
        self.control.setStyleSheet(utils.menu_style())
        self.control.setFont(QFont('Arial', 12))
        self.menubar.addMenu(self.control)

        # Emergency Stop
        self.action_emergency_stop = QAction("Emergency Stop", MainWindow)
        self.action_emergency_stop.triggered.connect(self.conn_emergency_stop)
        self.action_emergency_stop.setShortcut("Ctrl+E")
        self.control.addAction(self.action_emergency_stop)

        # Setting
        self.setting = QMenu("Setting", self.menubar)
        self.setting.setStyleSheet(utils.menu_style())
        self.setting.setFont(QFont('Arial', 12))
        self.menubar.addMenu(self.setting)

        # Show Hidden Log
        self.show_hidden = QAction("Show Hidden Log", MainWindow)
        self.show_hidden.triggered.connect(self.show_hidden_log)
        self.setting.addAction(self.show_hidden)

        # Central Widget
        self.central_widget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Functional Panel
        self.function_panel = QFrame(self.central_widget)
        self.function_panel.setObjectName("function_panel")
        self.function_panel.setFrameShape(QFrame.StyledPanel)
        self.function_panel.setFrameShadow(QFrame.Raised)
        self.function_panel.setStyleSheet('''background-color: #333333;
                                          border-radius: 5px;''')
        
        self.function_layout = QVBoxLayout(self.function_panel)
        self.function_layout.setContentsMargins(20, 20, 20, 20)
        self.function_layout.setSpacing(20)

        # Serial Window Button
        self.serial_window_button = QPushButton("Serial Selection Window\n(Ctrl+S)", self.function_panel)
        self.serial_window_button.clicked.connect(self.open_serial_window)

        # Control Window Button
        self.control_window_button = QPushButton("Control Window\n(Ctrl+T)", self.function_panel)
        self.control_window_button.clicked.connect(self.open_control_window)

        # G-code Window Button
        self.g_code_window_button = QPushButton("G-code Window\n(Ctrl+G)", self.function_panel)
        self.g_code_window_button.clicked.connect(self.open_g_code_window)

        # Text Clear Button
        self.test_button = QPushButton("Text Clear\n(Ctrl+R)", self.function_panel)
        self.test_button.clicked.connect(self.text_box_clear)

        # Quit Button
        self.quit_button = QPushButton("Quit\n(Ctrl+Q)", self.function_panel)
        self.quit_button.clicked.connect(self.close_func)

        for btn in [
            self.serial_window_button,
            self.control_window_button,
            self.g_code_window_button,
            self.test_button,
            self.quit_button
        ]:
            self.function_layout.addWidget(btn)

            btn.setFont(QFont('Arial', 12))
            btn.setStyleSheet("""
                background-color: #444444;
                border-radius: 5px;
                border: 1px solid #555555;
                color: white;
                height: 60px;
            """)

        # Status Panel
        self.status_panel = QFrame(self.central_widget)
        self.status_panel.setObjectName("status_panel")
        self.status_panel.setFrameShape(QFrame.StyledPanel)
        self.status_panel.setFrameShadow(QFrame.Raised)
        self.status_panel.setStyleSheet('''background-color: #333333;
                                         border-radius: 5px;''')
        
        self.text_box = QTextEdit(self.status_panel)
        self.text_box.setReadOnly(True)
        self.text_box.setStyleSheet('''background-color: #444444;
                                    color: white;''')
        self.text_box.setFont(QFont('Arial', 10))

        self.status_layout = QVBoxLayout(self.status_panel)
        self.status_layout.setContentsMargins(10, 10, 10, 10)
        self.status_layout.setSpacing(0)
        self.status_layout.addWidget(self.text_box)

        # Logger
        self.logger = Logger(self.text_box)
        
        # Display Panel
        self.display_panel = QFrame(self.central_widget)
        self.display_panel.setObjectName("display_panel")
        self.display_panel.setFrameShape(QFrame.StyledPanel)
        self.display_panel.setFrameShadow(QFrame.Raised)
        self.display_panel.setStyleSheet('''background-color: #333333;
                                         border-radius: 5px;''')
        
        self.main_layout.addWidget(self.display_panel, 5)
        self.right_panel = QVBoxLayout()
        self.main_layout.addLayout(self.right_panel, 1)
        self.right_panel.addWidget(self.function_panel)
        self.right_panel.addWidget(self.status_panel)

        self.display_layout = QVBoxLayout(self.display_panel)
        self.display_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.display_layout.addWidget(self.stack)

        # Serial Window
        self.serial_window = Serial_Selection(self.logger)
        self.stack.addWidget(self.serial_window)

        # Control Window
        self.control_window = ControlGUI(self.logger)
        self.stack.addWidget(self.control_window)

        # G-code Window
        self.g_code_window = ActuateGUI(self.logger)
        self.stack.addWidget(self.g_code_window)
    
    def conn_emergency_stop(self):
        utils.emergency_stop(self.logger)

    def update_data(self, data):
        self.serial_port_data=data
        self.logger.log(f"Serial port data updated: {self.serial_port_data}")

    def open_serial_window(self):
        self.stack.setCurrentWidget(self.serial_window)

    def open_control_window(self):
        self.stack.setCurrentWidget(self.control_window)

    def open_g_code_window(self):
        self.stack.setCurrentWidget(self.g_code_window)

    def show_hidden_log(self):
        if self.logger.show_hidden:
            self.logger.show_hidden = False
            self.logger.log('Hidden log : Invisiable')

            self.logger._refresh()
            self.logger.hidden("for test 안보이기")

        else:
            self.logger.show_hidden = True
            self.logger.log('Hidden log : Visiable')

            self.logger._refresh()
            self.logger.hidden("for test 보이기")

    def text_box_clear(self):
        if self.text_box is not None:
            self.text_box.clear()

    def close_func(self):
        utils.close(shared_data.connections,
                    shared_data.worker_thread,
                    shared_data.stop_event,
                    shared_data.command_queue)

    def save_log_file(self):
        try:
            if not os.path.exists("log"):
                os.makedirs("log")

            date_time = QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
            logs = self.text_box.toPlainText()
            with open(f"log/log_{date_time}.txt", "w") as f:
                f.write(logs)
            self.logger.log(f"Log saved as log_{date_time}.txt")
        except Exception as e:
            self.logger.error(f"Error saving log file: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QMainWindow()
    ui = MainGUI(win)
    win.show()
    sys.exit(app.exec_())