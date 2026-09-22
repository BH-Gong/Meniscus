import sys
import os 
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QCheckBox, QRadioButton, QGroupBox, QGridLayout, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import logging
import serial
import serial.tools.list_ports

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

logging.basicConfig(filename='Log_UI.log',level=logging.DEBUG)

class main_window(QWidget):
    def __init__(self):
        QWidget.__init__(self, flags= Qt.Widget)
        self.setWindowTitle("Meniscus Guided 3D Printing Motor Control")
        self.setWindowIcon(QIcon(resource_path("logo.png")))

        self.btn_port=QPushButton("Open Serial Selection Window")
        self.btn_port.setFixedSize(300, 50)
        font_btn_port = self.btn_port.font()
        font_btn_port.setPointSize(15)
        self.btn_port.setFont(font_btn_port)
        self.btn_port.setCursor(Qt.PointingHandCursor)
        self.btn_port.clicked.connect(self.get_port_list)
        
        ##
        hbox_btn_port=QHBoxLayout()
        hbox_btn_port.addStretch(1)
        hbox_btn_port.addWidget(self.btn_port)
        hbox_btn_port.addStretch(1)

        vbox=QVBoxLayout()
        vbox.addLayout(hbox_btn_port)

        hbox_main=QHBoxLayout()
        hbox_main.addLayout(vbox)

        self.setLayout(hbox_main)

    def get_port_list(self):
        port_selector = PortSelector()
        port_selector.exec_()
        self.connection=port_selector.get_connection()

class PortSelector(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Port Selection")
        self.setGeometry(100, 100, 500, 500)
        self.serial_vars={}
        port_info=self.port_list_up()

        layout=QVBoxLayout()
        self.button_group=QButtonGroup(self)
        for port in port_info:
            button=QRadioButton(port)
            self.button_group.addButton(button)
            layout.addWidget(button)
    
    def port_list_up(self):
        ports = serial.tools.list_ports.comports()
        port_info=[]
        for port in ports:
            port_info.append(port.device)
        return port_info

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = main_window()
    main.show()
    sys.exit(app.exec_())