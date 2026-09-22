from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from core import shared_data
from core.libCRUX import CRUX
from core.logger import Logger
from core.utils import *
from core.code_generator import CodeGenerator

from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import threading
import queue
import logging
import time
import math
import sys

lock=threading.Lock()

class ActuateGUI(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.crux = CRUX(logger, shared_data.connections, shared_data.connections)
        self.logger = logger
        command_queue = queue.Queue()
        shared_data.command_queue = command_queue
        self.is_paused = False
        self.is_active = False
        self.pos={'pos_x':0, 'pos_y':0, 'pos_z':0}
        self.stop_event = threading.Event()
        self.absolute_flag = True
        self.sum_pause_time = 0.0

        try:
            for _ in shared_data.port_axis_mapping:
                port=shared_data.port_axis_mapping['info'].get('name')
                self.ports.append(port)
            for connection in shared_data.connections:
                self.connections.append(connection)
            self.model=shared_data.model
        except IndexError:
            self.container.destroy()

        self.initUI()

    def initUI(self):
        # Main Widget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Main Title
        self.title_container = QWidget()
        self.title_layout = QGridLayout(self.title_container)
        
        self.main_title = QLabel("G-code")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setStyleSheet('''background-color: #333333;
                                      color: white;
                                      padding: 15px;''')
        self.main_title.setFont(QFont('Arial', 24, QFont.Bold))

        # Emergency Stop Button
        self.emergency_stop_button = QPushButton("Emergency Stop\n(Ctrl+E)")
        self.emergency_stop_button.setStyleSheet(button_style())
        self.emergency_stop_button.setFont(QFont('Arial', 10, QFont.Bold))
        self.emergency_stop_button.clicked.connect(lambda: self.crux.emergency_stop())

        # Clear Button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet(button_style())
        self.clear_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.clear_button.setContentsMargins(20, 20, 20, 20)
        self.clear_button.clicked.connect(lambda: self.gcode_clear())

        self.title_layout.addWidget(self.clear_button, 0, 0, alignment=Qt.AlignLeft)
        self.title_layout.addWidget(self.main_title, 0, 1, alignment=Qt.AlignCenter)
        self.title_layout.addWidget(self.emergency_stop_button, 0, 2, alignment=Qt.AlignRight)
        
        self.main_layout.addWidget(self.title_container, alignment=Qt.AlignTop)
        
        # G-code Panel
        self.gcode_panel = QWidget()
        self.gcode_panel.setStyleSheet('''background-color: #444444;
                                       color: white;''')
        self.gcode_layout = QHBoxLayout(self.gcode_panel)

        # Command Panel
        self.command_panel = QWidget()
        self.command_panel.setStyleSheet('''background-color: #333333;
                                         color: white;''')
        self.command_layout = QVBoxLayout(self.command_panel)

        self.command_label = QLabel("G-code Data")
        self.command_label.setStyleSheet('''background-color: #333333;
                                         color: white;''')
        self.command_label.setAlignment(Qt.AlignCenter)
        self.command_label.setFont(QFont('Arial', 18, QFont.Bold))

        self.load_file_button = QPushButton("Load G-code File")
        self.load_file_button.setStyleSheet(button_style())
        self.load_file_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.load_file_button.clicked.connect(lambda: self.open_file())

        self.command_tree = QTreeWidget()
        self.command_tree.setHeaderLabels(["Index", "Command"])
        self.command_tree.setStyleSheet(tree_style())
        self.command_tree.setFont(QFont('Arial', 12))
        self.command_tree.verticalScrollBarPolicy()

        self.time_panel = QWidget()
        self.time_panel.setStyleSheet('''background-color: #444444;
                                      color: white;''')
        self.time_layout = QHBoxLayout(self.time_panel)

        self.est_time_panel = QWidget()
        self.est_time_panel.setStyleSheet('''color: #00ff00;''')
        self.est_time_layout = QHBoxLayout(self.est_time_panel)

        self.est_time_label = QLabel("Estimated Time: ")
        self.est_time_label.setAlignment(Qt.AlignCenter)
        self.est_time_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.est_time_value = QLabel("00:00:00")
        self.est_time_value.setAlignment(Qt.AlignCenter)
        self.est_time_value.setFont(QFont('Arial', 18, QFont.Bold))

        self.est_time_layout.addWidget(self.est_time_label)
        self.est_time_layout.addWidget(self.est_time_value)

        self.elap_time_panel = QWidget()
        self.elap_time_panel.setStyleSheet('''color: #ff0000;''')
        self.elap_time_layout = QHBoxLayout(self.elap_time_panel)

        self.elap_time_label = QLabel("Elapsed Time: ")
        self.elap_time_label.setAlignment(Qt.AlignCenter)
        self.elap_time_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.elap_time_value = QLabel("00:00:00") # modification necessary
        self.elap_time_value.setAlignment(Qt.AlignCenter)
        self.elap_time_value.setFont(QFont('Arial', 18, QFont.Bold))

        self.elap_time_layout.addWidget(self.elap_time_label)
        self.elap_time_layout.addWidget(self.elap_time_value)

        self.time_layout.addWidget(self.est_time_panel, alignment=Qt.AlignCenter)
        self.time_layout.addWidget(self.elap_time_panel, alignment=Qt.AlignCenter)

        self.command_layout.addWidget(self.command_label)
        self.command_layout.addWidget(self.load_file_button)
        self.command_layout.addWidget(self.command_tree)
        self.command_layout.addWidget(self.time_panel)

        self.command_layout.setStretch(0, 0)
        self.command_layout.setStretch(1, 0)
        self.command_layout.setStretch(2, 1)
        self.command_layout.setStretch(3, 0)

        self.gcode_layout.addWidget(self.command_panel, 1)

        # Trajectory Panel
        self.trajectory_panel = QWidget()
        self.trajectory_panel.setStyleSheet('''background-color: #333333;
                                            color: white;''')
        self.trajectory_layout = QVBoxLayout(self.trajectory_panel)

        self.trajectory_label = QLabel("Actuate Path")
        self.trajectory_label.setFont(QFont('Arial', 18, QFont.Bold))

        self.trajectory_layout.addWidget(self.trajectory_label, alignment=Qt.AlignCenter)

        self.plot_button = QPushButton("Plot Trajectory")
        self.plot_button.setStyleSheet(button_style())
        self.plot_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.plot_button.setContentsMargins(20, 20, 20, 20)
        self.plot_button.clicked.connect(lambda: self.plot_trajectory())

        self.trajectory_layout.addWidget(self.plot_button)

        self.plot_area = QWidget()
        self.plot_area.setStyleSheet('''background-color: #444444;
                                     color: white;''')
        self.plot_layout = QVBoxLayout(self.plot_area)
        
        self.trajectory_layout.addWidget(self.plot_area)

        self.functional_panel = QWidget()
        self.functional_panel.setStyleSheet('''background-color: #333333;
                                            color: white;''')
        self.functional_layout = QHBoxLayout(self.functional_panel)

        self.act_button = QPushButton("Act")
        self.act_button.setEnabled(False)
        self.act_button.setStyleSheet(button_style())
        self.act_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.act_button.setContentsMargins(0, 0, 0, 0)
        self.act_button.clicked.connect(lambda: self.execute())

        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.setStyleSheet(button_style())
        self.pause_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.pause_button.setContentsMargins(0, 0, 0, 0)
        self.pause_button.clicked.connect(lambda: self.pause())

        self.resume_button = QPushButton("Resume")
        self.resume_button.setEnabled(False)
        self.resume_button.setStyleSheet(button_style())
        self.resume_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.resume_button.setContentsMargins(0, 0, 0, 0)
        self.resume_button.clicked.connect(lambda: self.resume())

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(button_style())
        self.stop_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.stop_button.setContentsMargins(0, 0, 0, 0)
        self.stop_button.clicked.connect(lambda: self.stop())

        self.reset_button = QPushButton("Reset")
        self.reset_button.setEnabled(False)
        self.reset_button.setStyleSheet(button_style())
        self.reset_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.reset_button.setContentsMargins(0, 0, 0, 0)
        self.reset_button.clicked.connect(lambda: self.reset())

        self.functional_layout.addWidget(self.act_button)
        self.functional_layout.addWidget(self.pause_button)
        self.functional_layout.addWidget(self.resume_button)
        self.functional_layout.addWidget(self.stop_button)
        self.functional_layout.addWidget(self.reset_button)

        self.trajectory_layout.addWidget(self.functional_panel)
        
        self.trajectory_layout.setStretch(0, 0)
        self.trajectory_layout.setStretch(1, 0)
        self.trajectory_layout.setStretch(2, 1)
        self.trajectory_layout.setStretch(3, 0)

        self.gcode_layout.addWidget(self.trajectory_panel, 1)
        
        self.main_layout.addWidget(self.gcode_panel)

    def open_file(self):
        self.model = shared_data.model
        if self.model is None:
            self.logger.error("No driver model loaded! Please save a serial port data first.")
            return

        self.code_generator = CodeGenerator(self.logger, self.model)

        # self.logger.warning(self.model)
        # self.logger.warning(self.code_generator)

        self.act_button.setEnabled(True)
        self.gcode, self.trajectory, self.estimate_time = open_file(self.logger, self.command_tree, self.model)
        formatted_time = format_seconds(self.estimate_time)
        self.est_time_value.setText(formatted_time)

    def plot_trajectory(self):
        if self.trajectory:
            self.figure = plot_trajectory(self.trajectory)
            while self.plot_layout.count():
                item = self.plot_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.canvas = FigureCanvasQTAgg(self.figure)
            self.canvas.setStyleSheet("background-color:#333333;")
            self.plot_layout.addWidget(self.canvas)

            self.logger.log("Plotting trajectory...")
        else:
            self.logger.log("No trajectory data to plot.")

    def execute(self):
        for line in self.gcode:
            self.code_generator.convert_gcode_to_motor(line)

        self.act_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        self.is_active = True
        self.paused_duration = 0.0
        self.start_time = time.time()
        self.update_timer()

        self.logger.log("Actuating G-code...")

        self.process_commands()

    def pause(self):
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)

        self.is_paused = True
        self.pause_start_time = time.time()

        self.logger.log("Pausing...")

    def resume(self):
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)

        self.is_paused = False
        self.sum_pause_time += self.paused_duration
        self.paused_duration = 0.0

        self.logger.log("Resuming...")

    def stop(self):
        self.reset_button.setEnabled(True)
        self.act_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.is_active = False
        self.stop_event.set()

        self.logger.log("Stopping...")

    def reset(self):
        self.act_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.reset_button.setEnabled(False)

        self.is_active = False
        self.is_paused = False
        self.pause_start_time = None
        self.paused_duration = 0.0
        self.elap_time_value.setText("00:00:00")
        self.stop_event.clear()

        shared_data.command_queue = queue.Queue()

        self.logger.log("Resetting...")

    def gcode_clear(self):
        self.command_tree.clear()
        self.est_time_value.setText("00:00:00")
        self.elap_time_value.setText("00:00:00")
        self.act_button.setEnabled(False)

        while self.plot_layout.count():
            item = self.plot_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.logger.log("Clearing G-code data...")

    def process_commands(self):
        if is_worker_running(shared_data.worker_thread, shared_data.stop_event):
            return
        
        self.stop_event.clear()
        
        def worker():
            count = 0
            while True:
                if self.stop_event.is_set():
                    break
                
                while self.is_paused:
                    time.sleep(0.1)
                    if self.stop_event.is_set():
                        break

                try:
                    command = shared_data.command_queue.get(timeout=1)
                    count += 1
                    print(f"START COMMAND {count}")
                    command()
                    print(f"END COMMAND {count}")
                    shared_data.command_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f'Error while executing command: {e}')
        
        self.worker_thread = threading.Thread(target=worker)
        self.worker_thread.daemon=True

        shared_data.worker_thread = self.worker_thread
        shared_data.stop_event = self.stop_event

        self.worker_thread.start()

    def update_timer(self):
        elapsed = 0.0
        if self.is_active:
            if self.is_paused:
                self.paused_duration = (time.time() - self.pause_start_time)
            elapsed = time.time() - self.start_time - self.sum_pause_time - self.paused_duration
            self.elap_time_value.setText(format_seconds(elapsed))

        if elapsed >= self.estimate_time:
            self.stop()
            self.timer.stop()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1)