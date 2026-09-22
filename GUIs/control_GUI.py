from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import core.shared_data as shared_data
from core.utils import *
from core.libCRUX import CRUX

from PIL import Image, ImageTk
import serial
import threading
import time
import queue
import logging
import sys
import os

'''
MainWidget
    ㄴMain Title
        ㄴEmergency Stop Button
    ㄴControl Frame
        ㄴBed Control Panel
            ㄴBed Control Buttons
            ㄴBed Speed Table
            ㄴBed Movement Mode Radio Buttons and Pulse Entry
        ㄴNozzle Control Panel
            ㄴNozzle Control Buttons
            ㄴNozzle Speed Table
            ㄴNozzle Movement Mode Radio Buttons and Pulse Entry

f'# {기능명}'로 주석 검색하여 색인 가능
'''

lock=threading.Lock()
# for exe to find proper path
def resource_path(relative_path):
     """ Get absolute path to resource, works for dev and for PyInstaller """
     try:
        base_path = sys._MEIPASS
     except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
     return os.path.join(base_path, relative_path)

class ControlGUI(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.crux = CRUX(logger)
        self.logger = logger

        self.noz_timer = QTimer(self)
        self.bed_timer = QTimer(self)

        self.noz_timer.timeout.connect(lambda: self.move('noz'))
        self.bed_timer.timeout.connect(lambda: self.move('bed'))

        self.worker_thread = None
        self.command_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.limit = 20000
        self.current_axis = None
        self.current_axis_name = None
        self.current_port = None
        self.current_direction = None


        self.process_commands()
        self.initUI()
        
    def initUI(self):
        # MainWidget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Main Title
        self.title_container = QWidget()
        self.title_layout = QGridLayout(self.title_container)

        self.main_title = QLabel("Control")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setStyleSheet('''background-color: #333333;
                                      color: white;
                                      padding: 15px;''')
        self.main_title.setFont(QFont('Arial', 24, QFont.Bold))
        
        # Active & Deactivate Button
        self.active_layout = QHBoxLayout()

        self.active_button = QPushButton("Activate")
        self.active_button.setStyleSheet(button_style())
        if shared_data.active_flag:
            self.active_button.setDisabled(True)
        else:
            self.active_button.setEnabled(True)
        self.active_button.setFont(QFont('Arial', 10, QFont.Bold))
        self.active_button.clicked.connect(lambda:activate(self.logger, self.active_button, self.deactivate_button, self.active_button))

        self.deactivate_button = QPushButton("Deactivate")
        self.deactivate_button.setStyleSheet(button_style())
        if shared_data.active_flag:
            self.deactivate_button.setEnabled(True)
        else:
            self.deactivate_button.setDisabled(True)
        self.deactivate_button.setFont(QFont('Arial', 10, QFont.Bold))
        self.deactivate_button.clicked.connect(lambda:activate(self.logger, self.active_button, self.deactivate_button, self.deactivate_button))

        self.active_layout.addWidget(self.active_button)
        self.active_layout.addWidget(self.deactivate_button)

        # Emergency Stop Button
        self.emergency_stop_button = QPushButton("Emergency Stop\n(Ctrl+E)")
        self.emergency_stop_button.setStyleSheet(button_style())
        self.emergency_stop_button.setFont(QFont('Arial', 10, QFont.Bold))
        self.emergency_stop_button.clicked.connect(lambda: self.crux.emergency_stop())

        self.title_layout.addWidget(self.main_title, 0, 1, alignment=Qt.AlignCenter)
        self.title_layout.addLayout(self.active_layout, 0, 0, alignment=Qt.AlignLeft)
        self.title_layout.addWidget(self.emergency_stop_button, 0, 2, alignment=Qt.AlignRight)

        self.main_layout.addWidget(self.title_container)

        # Control Frame
        self.control_frame = QFrame()
        self.control_frame.setObjectName("control_frame")
        self.control_frame.setStyleSheet('''background-color: #444444;
                                         color: white;''')
        self.control_frame.setFont(QFont('Arial', 16))
        self.main_layout.addWidget(self.control_frame, 8)

        self.sub_control_layout = QHBoxLayout(self.control_frame)
        self.sub_control_layout.setContentsMargins(10, 10, 10, 10)
        self.sub_control_layout.setSpacing(10)

        # Bed Control Panel
        self.bed_control_panel = QFrame(self.control_frame)
        self.bed_control_panel.setStyleSheet('''background-color: #333333;
                                             color: white;''')
        self.bed_control_panel.setFont(QFont('Arial', 16))
        self.sub_control_layout.addWidget(self.bed_control_panel, 5)

        # Bed Control Buttons
        self.bed_control_layout = QVBoxLayout(self.bed_control_panel)
        self.bed_title = QLabel("Bed")
        self.bed_title.setAlignment(Qt.AlignCenter)
        self.bed_title.setFont(QFont('Arial', 20, QFont.Bold))
        self.bed_control_layout.addWidget(self.bed_title, alignment=Qt.AlignTop)
        
        bed_control_frame = QFrame(self.bed_control_panel)
        self.bed_grid_button = QGridLayout(bed_control_frame)

        self.bed_x_pos = SquareButton()
        self.bed_x_pos.setIcon(QIcon(resource_path("../icon/bed_pos_x.png")))
        self.bed_x_pos.pressed.connect(lambda: self.on_button_press('BD-X', 'pos', 'bed', self.bed_x_pos))
        self.bed_x_pos.released.connect(lambda: self.on_button_release('bed', self.bed_x_pos))

        self.bed_x_neg = SquareButton()
        self.bed_x_neg.setIcon(QIcon(resource_path("../icon/bed_neg_x.png")))
        self.bed_x_neg.pressed.connect(lambda: self.on_button_press('BD-X', 'neg', 'bed', self.bed_x_neg))
        self.bed_x_neg.released.connect(lambda: self.on_button_release('bed', self.bed_x_neg))

        self.bed_y_pos = SquareButton()
        self.bed_y_pos.setIcon(QIcon(resource_path("../icon/bed_pos_y.png")))
        self.bed_y_pos.pressed.connect(lambda: self.on_button_press('BD-Y', 'pos', 'bed', self.bed_y_pos))
        self.bed_y_pos.released.connect(lambda: self.on_button_release('bed', self.bed_y_pos))

        self.bed_y_neg = SquareButton()
        self.bed_y_neg.setIcon(QIcon(resource_path("../icon/bed_neg_y.png")))
        self.bed_y_neg.pressed.connect(lambda: self.on_button_press('BD-Y', 'neg', 'bed', self.bed_y_neg))
        self.bed_y_neg.released.connect(lambda: self.on_button_release('bed', self.bed_y_neg))

        self.bed_z_pos = SquareButton()
        self.bed_z_pos.setIcon(QIcon(resource_path("../icon/bed_pos_z.png")))
        self.bed_z_pos.pressed.connect(lambda: self.on_button_press('BD-Z', 'pos', 'bed', self.bed_z_pos))
        self.bed_z_pos.released.connect(lambda: self.on_button_release('bed', self.bed_z_pos))

        self.bed_z_neg = SquareButton()
        self.bed_z_neg.setIcon(QIcon(resource_path("../icon/bed_neg_z.png")))
        self.bed_z_neg.pressed.connect(lambda: self.on_button_press('BD-Z', 'neg', 'bed', self.bed_z_neg))
        self.bed_z_neg.released.connect(lambda: self.on_button_release('bed', self.bed_z_neg))

        self.bed_tx_pos = SquareButton()
        self.bed_tx_pos.setIcon(QIcon(resource_path("../icon/bed_pos_tx.png")))
        self.bed_tx_pos.pressed.connect(lambda: self.on_button_press('BD-TX', 'pos', 'bed', self.bed_tx_pos))
        self.bed_tx_pos.released.connect(lambda: self.on_button_release('bed', self.bed_tx_pos))

        self.bed_tx_neg = SquareButton()
        self.bed_tx_neg.setIcon(QIcon(resource_path("../icon/bed_neg_tx.png")))
        self.bed_tx_neg.pressed.connect(lambda: self.on_button_press('BD-TX', 'neg', 'bed', self.bed_tx_neg))
        self.bed_tx_neg.released.connect(lambda: self.on_button_release('bed', self.bed_tx_neg))

        self.bed_ty_pos = SquareButton()
        self.bed_ty_pos.setIcon(QIcon(resource_path("../icon/bed_pos_ty.png")))
        self.bed_ty_pos.pressed.connect(lambda: self.on_button_press('BD-TY', 'pos', 'bed', self.bed_ty_pos))
        self.bed_ty_pos.released.connect(lambda: self.on_button_release('bed', self.bed_ty_pos))

        self.bed_ty_neg = SquareButton()
        self.bed_ty_neg.setIcon(QIcon(resource_path("../icon/bed_neg_ty.png")))
        self.bed_ty_neg.pressed.connect(lambda: self.on_button_press('BD-TY', 'neg', 'bed', self.bed_ty_neg))
        self.bed_ty_neg.released.connect(lambda: self.on_button_release('bed', self.bed_ty_neg))

        self.bed_home = SquareButton()
        self.bed_home.setIcon(QIcon(resource_path("../icon/origin.png")))
        self.bed_home.clicked.connect(lambda: self.homing('bed'))

        self.bed_buttons = [
            self.bed_x_pos,
            self.bed_x_neg, 
            self.bed_y_pos,
            self.bed_y_neg, 
            self.bed_z_pos,
            self.bed_z_neg, 
            self.bed_tx_pos,
            self.bed_tx_neg, 
            self.bed_ty_pos,
            self.bed_ty_neg,
            self.bed_home
        ]

        for btn in self.bed_buttons:
            btn.setStyleSheet(button_style())
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setIconSize(QSize(20, 20))

        self.bed_grid_button.addWidget(self.bed_x_pos, 5, 4)
        self.bed_grid_button.addWidget(self.bed_x_neg, 1, 2)
        self.bed_grid_button.addWidget(self.bed_y_pos, 1, 4)
        self.bed_grid_button.addWidget(self.bed_y_neg, 5, 2)
        self.bed_grid_button.addWidget(self.bed_z_pos, 0, 3)
        self.bed_grid_button.addWidget(self.bed_z_neg, 6, 3)

        self.tilt_widget_0 = QWidget()
        self.tilt_layout_0 = QVBoxLayout(self.tilt_widget_0)

        self.tilt_layout_0.setContentsMargins(0, 0, 0, 0)
        self.tilt_layout_0.setSpacing(0)

        self.tilt_layout_0.addWidget(self.bed_tx_neg)
        self.tilt_layout_0.addWidget(self.bed_ty_neg)
        
        self.bed_grid_button.addWidget(self.tilt_widget_0, 3, 0)

        self.tilt_widget_1 = QWidget()
        self.tilt_layout_1 = QVBoxLayout(self.tilt_widget_1)

        self.tilt_layout_1.setContentsMargins(0, 0, 0, 0)
        self.tilt_layout_1.setSpacing(0)

        self.tilt_layout_1.addWidget(self.bed_tx_pos)
        self.tilt_layout_1.addWidget(self.bed_ty_pos)
        
        self.bed_grid_button.addWidget(self.tilt_widget_1, 3, 6)

        self.bed_grid_button.addWidget(self.bed_home, 3, 3)

        self.bed_grid_button.setContentsMargins(10, 10, 10, 10)
        self.bed_grid_button.setSpacing(20)

        temp_container_0 = QWidget() 
        self.bed_layer = QStackedLayout(temp_container_0)

        temp_container_1 = QWidget()
        temp_container_1.setLayout(self.bed_grid_button)
        temp_container_1.setStyleSheet("background: transparent;")

        self.bg_0 = QLabel()
        self.bg_0.setPixmap(QPixmap(resource_path("../icon/bed.png")).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.bg_0.setScaledContents(True)

        self.bed_layer.setStackingMode(QStackedLayout.StackAll)

        self.bed_layer.addWidget(temp_container_1)
        self.bed_layer.addWidget(self.bg_0)

        self.bed_control_layout.addWidget(temp_container_0)

        self.speed_selection_0 = QComboBox()
        self.speed_selection_0.addItems(['   1   ', '   2   ', '   3   ', 
                                          '   4   ', '   5   ', '   6   ',
                                          '   7   ', '   8   ', '   9   '])
        self.speed_selection_0.setCurrentText("   9   ")
        self.speed_selection_0.setStyleSheet('''background-color: #555555;
                                             color: white;''')
        self.speed_selection_0.setFont(QFont('Arial', 14))

        self.bed_control_layout.addWidget(self.speed_selection_0, alignment=Qt.AlignRight)

        self.mode_layout_0 = QHBoxLayout()
        self.bed_mode_group = QButtonGroup()
        self.continuous_mode_button_0 = QRadioButton("Continuous")

        self.absolute_mode_layout_0 = QHBoxLayout()
        self.absolute_mode_button_0 = QRadioButton("Absolute")

        self.relative_mode_layout_0 = QHBoxLayout()
        self.relative_mode_button_0 = QRadioButton("Relative")

        self.absolute_mode_layout_0.addWidget(self.absolute_mode_button_0)
        self.absolute_text_0 = QLineEdit()
        self.absolute_text_0.setStyleSheet('''background-color: #555555;
                                         color: white;''')
        self.absolute_text_0.setFont(QFont('Arial', 10))
        self.absolute_text_0.setText("0")
        self.absolute_mode_layout_0.setSpacing(12)
        self.absolute_mode_layout_0.addWidget(self.absolute_text_0)
        
        self.relative_mode_layout_0.addWidget(self.relative_mode_button_0)
        self.relative_text_0 = QLineEdit()
        self.relative_text_0.setStyleSheet('''background-color: #555555;
                                         color: white;''')
        self.relative_text_0.setFont(QFont('Arial', 10))
        self.relative_text_0.setText("100")
        self.relative_mode_layout_0.setSpacing(12)
        self.relative_mode_layout_0.addWidget(self.relative_text_0)

        for btn in [
            self.continuous_mode_button_0,
            self.absolute_mode_button_0,
            self.relative_mode_button_0
        ]:
            self.bed_mode_group.addButton(btn)
            btn.setFont(QFont('Arial', 12))
        
        self.continuous_mode_button_0.setChecked(True)
        self.mode_layout_0.setSpacing(30)
        self.mode_layout_0.addWidget(self.continuous_mode_button_0)
        self.mode_layout_0.addLayout(self.absolute_mode_layout_0)
        self.mode_layout_0.addLayout(self.relative_mode_layout_0)
        self.bed_control_layout.addLayout(self.mode_layout_0)
        
        # Nozzle Control Panel
        self.nozzle_control_panel = QFrame(self.control_frame)
        self.nozzle_control_panel.setStyleSheet('''background-color: #333333;
                                                color: white;''')
        self.nozzle_control_panel.setFont(QFont('Arial', 16))
        self.sub_control_layout.addWidget(self.nozzle_control_panel, 5)

        # Nozzle Control Buttons
        self.nozzle_control_layout = QVBoxLayout(self.nozzle_control_panel)
        self.nozzle_title = QLabel("Nozzle")
        self.nozzle_title.setAlignment(Qt.AlignCenter)
        self.nozzle_title.setFont(QFont('Arial', 20, QFont.Bold))
        self.nozzle_control_layout.addWidget(self.nozzle_title, alignment=Qt.AlignTop)
        
        nozzle_control_frame = QFrame(self.nozzle_control_panel)
        self.nozzle_grid_button = QGridLayout(nozzle_control_frame)

        self.nozzle_x_pos = SquareButton()
        self.nozzle_x_pos.setIcon(QIcon(resource_path("../icon/nozzle_pos_x.png")))
        self.nozzle_x_pos.pressed.connect(lambda: self.on_button_press('NZ-X', 'pos', 'noz', self.nozzle_x_pos))
        self.nozzle_x_pos.released.connect(lambda: self.on_button_release('noz', self.nozzle_x_pos))

        self.nozzle_x_neg = SquareButton()
        self.nozzle_x_neg.setIcon(QIcon(resource_path("../icon/nozzle_neg_x.png")))
        self.nozzle_x_neg.pressed.connect(lambda: self.on_button_press('NZ-X', 'neg', 'noz', self.nozzle_x_neg))
        self.nozzle_x_neg.released.connect(lambda: self.on_button_release('noz', self.nozzle_x_neg))

        self.nozzle_y_pos = SquareButton()
        self.nozzle_y_pos.setIcon(QIcon(resource_path("../icon/nozzle_pos_y.png")))
        self.nozzle_y_pos.pressed.connect(lambda: self.on_button_press('NZ-Y', 'pos', 'noz', self.nozzle_y_pos))
        self.nozzle_y_pos.released.connect(lambda: self.on_button_release('noz', self.nozzle_y_pos))

        self.nozzle_y_neg = SquareButton()
        self.nozzle_y_neg.setIcon(QIcon(resource_path("../icon/nozzle_neg_y.png")))
        self.nozzle_y_neg.pressed.connect(lambda: self.on_button_press('NZ-Y', 'neg', 'noz', self.nozzle_y_neg))
        self.nozzle_y_neg.released.connect(lambda: self.on_button_release('noz', self.nozzle_y_neg))

        self.nozzle_z_pos = SquareButton()
        self.nozzle_z_pos.setIcon(QIcon(resource_path("../icon/nozzle_pos_z.png")))
        self.nozzle_z_pos.pressed.connect(lambda: self.on_button_press('NZ-Z', 'pos', 'noz', self.nozzle_z_pos))
        self.nozzle_z_pos.released.connect(lambda: self.on_button_release('noz', self.nozzle_z_pos))
    
        self.nozzle_z_neg = SquareButton()
        self.nozzle_z_neg.setIcon(QIcon(resource_path("../icon/nozzle_neg_z.png")))
        self.nozzle_z_neg.pressed.connect(lambda: self.on_button_press('NZ-Z', 'neg', 'noz', self.nozzle_z_neg))
        self.nozzle_z_neg.released.connect(lambda: self.on_button_release('noz', self.nozzle_z_neg))

        self.nozzle_r_pos = SquareButton()
        self.nozzle_r_pos.setIcon(QIcon(resource_path("../icon/nozzle_pos_r.png")))
        self.nozzle_r_pos.pressed.connect(lambda: self.on_button_press('NZ-R', 'pos', 'noz', self.nozzle_r_pos))
        self.nozzle_r_pos.released.connect(lambda: self.on_button_release('noz', self.nozzle_r_pos))

        self.nozzle_r_neg = SquareButton()
        self.nozzle_r_neg.setIcon(QIcon(resource_path("../icon/nozzle_neg_r.png")))
        self.nozzle_r_neg.pressed.connect(lambda: self.on_button_press('NZ-R', 'neg', 'noz', self.nozzle_r_neg))
        self.nozzle_r_neg.released.connect(lambda: self.on_button_release('noz', self.nozzle_r_neg))

        self.nozzle_home = SquareButton()
        self.nozzle_home.setIcon(QIcon(resource_path("../icon/origin.png")))
        self.nozzle_home.clicked.connect(lambda: self.homing('noz'))

        self.noz_buttons = [
            self.nozzle_x_pos,
            self.nozzle_x_neg, 
            self.nozzle_y_pos,
            self.nozzle_y_neg, 
            self.nozzle_z_pos,
            self.nozzle_z_neg, 
            self.nozzle_r_pos,
            self.nozzle_r_neg, 
            self.nozzle_home
        ]

        for btn in self.noz_buttons:
            btn.setStyleSheet(button_style())
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setIconSize(QSize(20, 20))

        self.nozzle_grid_button.addWidget(self.nozzle_x_pos, 5, 4)
        self.nozzle_grid_button.addWidget(self.nozzle_x_neg, 1, 2)
        self.nozzle_grid_button.addWidget(self.nozzle_y_pos, 1, 4)
        self.nozzle_grid_button.addWidget(self.nozzle_y_neg, 5, 2)
        self.nozzle_grid_button.addWidget(self.nozzle_z_pos, 0, 3)
        self.nozzle_grid_button.addWidget(self.nozzle_z_neg, 6, 3)
        self.nozzle_grid_button.addWidget(self.nozzle_r_pos, 3, 6)
        self.nozzle_grid_button.addWidget(self.nozzle_r_neg, 3, 0)
        self.nozzle_grid_button.addWidget(self.nozzle_home, 3, 3)

        self.nozzle_grid_button.setContentsMargins(10, 10, 10, 10)
        self.nozzle_grid_button.setSpacing(20)

        temp_container_2 = QWidget() 
        self.nozzle_layer = QStackedLayout(temp_container_2)

        temp_container_3 = QWidget()
        temp_container_3.setLayout(self.nozzle_grid_button)
        temp_container_3.setStyleSheet("background: transparent;")

        self.bg_1 = QLabel()
        self.bg_1.setPixmap(QPixmap(resource_path("../icon/nozzle.png")).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.bg_1.setScaledContents(True)

        self.nozzle_layer.setStackingMode(QStackedLayout.StackAll)

        self.nozzle_layer.addWidget(temp_container_3)
        self.nozzle_layer.addWidget(self.bg_1)

        self.nozzle_control_layout.addWidget(temp_container_2)

        self.speed_selection_1 = QComboBox()
        self.speed_selection_1.addItems(['   1   ', '   2   ', '   3   ', 
                                          '   4   ', '   5   ', '   6   ', 
                                          '   7   ', '   8   ', '   9   '])
        self.speed_selection_1.setCurrentText("   9   ")
        self.speed_selection_1.setStyleSheet('''background-color: #555555;
                                           color: white;''')
        self.speed_selection_1.setFont(QFont('Arial', 14))

        self.nozzle_control_layout.addWidget(self.speed_selection_1, alignment=Qt.AlignRight)

        self.mode_layout_1 = QHBoxLayout()
        self.nozzle_mode_group = QButtonGroup()
        self.continuous_mode_button_1 = QRadioButton("Continuous")

        self.absolute_mode_layout_1 = QHBoxLayout()
        self.absolute_mode_button_1 = QRadioButton("Absolute")

        self.relative_mode_layout_1 = QHBoxLayout()
        self.relative_mode_button_1 = QRadioButton("Relative")

        self.absolute_mode_layout_1.addWidget(self.absolute_mode_button_1)
        self.absolute_text_1 = QLineEdit()
        self.absolute_text_1.setStyleSheet('''background-color: #555555;
                                         color: white;''')
        self.absolute_text_1.setFont(QFont('Arial', 10))
        self.absolute_text_1.setText("0")
        self.absolute_mode_layout_1.setSpacing(12)
        self.absolute_mode_layout_1.addWidget(self.absolute_text_1)
        
        self.relative_mode_layout_1.addWidget(self.relative_mode_button_1)
        self.relative_text_1 = QLineEdit()
        self.relative_text_1.setStyleSheet('''background-color: #555555;
                                         color: white;''')
        self.relative_text_1.setFont(QFont('Arial', 10))
        self.relative_text_1.setText("100")
        self.relative_mode_layout_1.setSpacing(12)
        self.relative_mode_layout_1.addWidget(self.relative_text_1)

        for btn in [
            self.continuous_mode_button_1,
            self.absolute_mode_button_1,
            self.relative_mode_button_1
        ]:
            self.nozzle_mode_group.addButton(btn)
            btn.setFont(QFont('Arial', 12))
        
        self.continuous_mode_button_1.setChecked(True)
        self.mode_layout_1.setSpacing(30)
        self.mode_layout_1.addWidget(self.continuous_mode_button_1)
        self.mode_layout_1.addLayout(self.absolute_mode_layout_1)
        self.mode_layout_1.addLayout(self.relative_mode_layout_1)
        self.nozzle_control_layout.addLayout(self.mode_layout_1)

    # Functions
    def process_commands(self):
        def worker():
            while not self.stop_event.is_set():
                try:
                    command = self.command_queue.get(timeout=1)
                    command()
                    self.command_queue.task_done()
                except queue.Empty:
                    continue

        self.worker_thread=threading.Thread(target=worker)
        self.worker_thread.daemon=True
        self.worker_thread.start()
        
    def activate(self):
        activate(self.logger, self.active_button, self.deactivate_button, self.active_button)

        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_event.clear()
            self.process_commands()
    
    def get_mode(self, typ):
        if typ == 'bed':
            con_btn_idx = self.continuous_mode_button_0
            abs_btn_idx = self.absolute_mode_button_0
            rel_btn_idx = self.relative_mode_button_0
        elif typ == 'noz':
            con_btn_idx = self.continuous_mode_button_1
            abs_btn_idx = self.absolute_mode_button_1
            rel_btn_idx = self.relative_mode_button_1

        if con_btn_idx.isChecked():
            mode = 'Continuous'
        elif abs_btn_idx.isChecked():
            mode = 'Absolute'
        elif rel_btn_idx.isChecked():
            mode = 'Relative'

        return mode

    def get_position_value(self, typ):
        pos = 0
        if typ == 'bed':
            mode = self.get_mode('bed')
            abs_value = int(self.absolute_text_0.text())
            rel_value = int(self.relative_text_0.text())
        elif typ == 'noz':
            mode = self.get_mode('noz')
            abs_value = int(self.absolute_text_1.text())
            rel_value = int(self.relative_text_1.text())

        try:
            if mode == 'Absolute' and self.current_direction == 'pos':
                pos = abs(abs_value)
            elif mode == 'Absolute' and self.current_direction == 'neg':
                pos = -abs(abs_value)
            elif mode == 'Relative' and self.current_direction == 'pos':
                pos = abs(rel_value)
            elif mode == 'Relative' and self.current_direction == 'neg':
                pos = -abs(rel_value)
        except: pass

        return pos

    def on_button_press(self, axis, direction, mode, event=None):
        if shared_data.model is None:
            self.logger.error("Save serial port data first!")
            return
        
        self.model = shared_data.model

        if shared_data.active_flag:
            self.is_button_pressed = True
            self.current_axis_name = axis
            self.current_axis, self.current_port = search_target_port(self.logger, self.current_axis_name)
            self.current_direction = direction

            if mode == 'bed':
                self.move('bed')
                if self.get_mode('bed') == 'Continuous':
                    self.bed_timer.start(100)
            elif mode == 'noz':
                self.move('noz')
                if self.get_mode('noz') == 'Continuous':
                    self.noz_timer.start(100)

    def on_button_release(self, mode, event=None):
        self.is_button_pressed = False

        if mode == 'bed':
            self.bed_timer.stop()
        elif mode == 'noz':
            self.noz_timer.stop()

        if self.current_port is not None:
            self.command_queue.put(lambda axis=self.current_axis, port=self.current_port: 
                                   self.model.STP(axis, port))

    def move(self, typ):
        if typ == 'bed':
            mode = self.get_mode('bed')
        elif typ == 'noz':
            mode = self.get_mode('noz')

        if self.current_axis is None or self.current_port is None:
            return
        
        axis = self.current_axis
        port = self.current_port
        
        current_pos = 0
        if typ == 'bed':
            speedtable = int(self.speed_selection_0.currentText())
        elif typ == 'noz':
            speedtable = int(self.speed_selection_1.currentText())

        if self.current_direction == 'pos':
            direction = 0
        elif self.current_direction == 'neg':
            direction = 1

        try:
            if mode in ('Absolute','Relative'):
                if typ == 'bed':
                    pos=self.get_position_value('bed')
                elif typ == 'noz':
                    pos=self.get_position_value('noz')

                if mode == 'Absolute':
                    if -self.limit > pos or pos > self.limit:
                        self.logger.error(f"The entered value exceeds the maximum limit for absolute movement. It will be set to {self.limit}.")
                    else:
                        self.command_queue.put(lambda axis=axis, speedtable=speedtable, port=port, pos=pos: 
                                            self.model.APS(axis, speedtable, port, pos))
                elif mode == 'Relative':
                    self.model.RDP_manual(axis, port)
                    current_pos = int(self.model.for_return)
                    if current_pos + pos > self.limit:
                        self.logger.error(f"The entered value exceeds the maximum limit for relative movement. It will be set to {self.limit}.")
                    elif -self.limit > current_pos + pos:
                        self.logger.error(f"The entered value exceeds the minimum limit for relative movement. It will be set to {self.limit}.")
                    else:
                        self.command_queue.put(lambda axis=axis, speedtable=speedtable, port=port, pos=pos:
                                            self.model.RPS(axis, speedtable, port, pos))
            elif mode == 'Continuous':
                self.command_queue.put(lambda axis=axis, speedtable=speedtable, port=port, direction=direction: 
                                       self.model.FRP(axis, speedtable, port, direction))
        except Exception as e:
            self.logger.error(f"Error: {e}")

    def homing(self, mode):
        if shared_data.model is None:
            self.logger.error("Save serial port data first!")
        else:
            self.model = shared_data.model

        if mode == 'bed':
            temp_list = ['BD-X', 'BD-Y', 'BD-Z', 'BD-TX', 'BD-TY']
            for a in temp_list:
                self.current_axis_name = a
                axis, port=search_target_port(self.logger, self.current_axis_name)
                self.command_queue.put(lambda axis=axis, speedtable=int(self.speed_selection_0.currentText()), port=port: 
                                       self.model.ORG(axis, speedtable, port))
        elif mode == 'noz':
            temp_list = ['NZ-X', 'NZ-Y', 'NZ-Z', 'NZ-R']
            for a in temp_list:
                self.current_axis_name = a
                axis, port=search_target_port(self.logger, self.current_axis_name)
                self.command_queue.put(lambda axis=axis, speedtable=int(self.speed_selection_1.currentText()), port=port: 
                                       self.model.ORG(axis, speedtable, port))
        else:
            return