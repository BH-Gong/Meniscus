from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from core.serial_ports import SerialPorts
import core.shared_data as shared_data
from core.libCRUX import CRUX
from core.utils import *

import serial
import time

'''
ㄴMainWiget
    ㄴMain Title
    ㄴSave Button
    ㄴRefresh Button
    ㄴSerial Ports Panel
        ㄴSerial Port Checkboxes
    ㄴAxis Selection Panel
        ㄴ Axis Selection
            ㄴAxis 1
                ㄴTest Button
                ㄴCombo Box
            ㄴAxis 2
                ㄴTest Button
                ㄴCombo Box
    ㄴTest Function
    ㄴSetup Save Function
f'# {기능명}'로 주석 검색하여 색인 가능
'''

class Serial_Selection(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.crux = CRUX(logger)
        self.logger = logger
        self.checked_port = set()
        self.port_index = {}
        self.ax_frame = {}
        self.test_cycle = 1
        self.initUI()

    def initUI(self):
        # Main Widget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Main Title
        self.title_container = QWidget()
        self.title_layout = QGridLayout(self.title_container)

        self.main_title = QLabel("Serial")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setStyleSheet('''background-color: #333333;
                                      color: white;
                                      padding: 15px;''')
        self.main_title.setFont(QFont('Arial', 24, QFont.Bold))

        # Save Button
        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet(button_style())
        self.save_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.save_button.setContentsMargins(20, 20, 20, 20)
        self.save_button.clicked.connect(lambda: self.setup_save())

        # Refresh Button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet(button_style())
        self.refresh_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.refresh_button.setContentsMargins(20, 20, 20, 20)
        self.refresh_button.clicked.connect(lambda: self.serial_refresh(self.serial_ports_layout))

        self.title_layout.addWidget(self.main_title, 0, 1, alignment=Qt.AlignCenter)
        self.title_layout.addWidget(self.save_button, 0, 2, alignment=Qt.AlignRight)
        self.title_layout.addWidget(self.refresh_button, 0, 0, alignment=Qt.AlignLeft)

        self.main_layout.addWidget(self.title_container, alignment=Qt.AlignTop)

        # Serial setup panel
        self.setup_panel = QFrame()
        self.setup_layout = QVBoxLayout(self.setup_panel)
        self.setup_panel.setStyleSheet("background-color: #444444;")

        # Serial Ports Panel
        self.serial_ports_panel = QFrame()
        self.serial_ports_panel.setStyleSheet("background-color: #333333;")

        self.serial_ports_layout = QVBoxLayout(self.serial_ports_panel)
        self.serial_ports_layout.setAlignment(Qt.AlignTop)
        
        self.serial_scroll = QScrollArea()
        self.serial_scroll.setWidgetResizable(True)
        self.serial_scroll.setWidget(self.serial_ports_panel)

        self.serial_ports_layout = self.serial_refresh(self.serial_ports_layout)

        self.setup_layout.addWidget(self.serial_scroll, 2)

        # Axis Selection Panel
        self.axis_selection_panel = QFrame()
        self.axis_selection_panel.setStyleSheet("background-color: #333333;")
        self.axis_selection_layout = QVBoxLayout(self.axis_selection_panel)
        self.axis_selection_layout.setAlignment(Qt.AlignTop)

        self.axis_scroll = QScrollArea()
        self.axis_scroll.setWidgetResizable(True)
        self.axis_scroll.setWidget(self.axis_selection_panel)

        self.setup_layout.addWidget(self.axis_scroll, 9)

        self.main_layout.addWidget(self.setup_panel)

    def serial_refresh(self, layout):
        idx = None
        if self.checked_port:
            idx = self.checked_port
        self.logger.log("Serial ports refreshed!")

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        serial_port = {}

        # Serial Port Checkboxes
        for i, port in enumerate(serial.tools.list_ports.comports()):
            serial_port[i] = QCheckBox(f"{port.device} - {port.description}")
            serial_port[i].setStyleSheet("color: white;")
            serial_port[i].setFont(QFont('Arial', 8))
            if idx is not None and port.device in idx:
                serial_port[i].setChecked(True)
            serial_port[i].stateChanged.connect(lambda state, port_name=port.device: self.plot_axis_selection(state, port_name))
            layout.addWidget(serial_port[i])
            self.port_index[i] = port.device

        return layout

    def plot_axis_selection(self, state, port_name):
        if state == Qt.Checked:
            # Axis Selection
            self.checked_port.add(port_name)
            self.ax_frame[port_name] = {}
            self.ax_frame[port_name]['frame'] = FixedFrameRatio(400, 33)
            self.ax_frame[port_name]['frame'].setStyleSheet('''background-color: #444444;
                                                     color: white;''')
            self.ax_frame[port_name]['frame'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.ax_frame[port_name]['frame'].setFont(QFont('Arial', 12))

            self.ax_frame[port_name]['layout'] = QVBoxLayout(self.ax_frame[port_name]['frame'])

            label = QLabel(f"{port_name}")
            label.setAlignment(Qt.AlignCenter)
            label.setFont(QFont('Arial', 12, QFont.Bold))
            self.ax_frame[port_name]['layout'].addWidget(label)

            self.ax_frame[port_name]['sublayout'] = QHBoxLayout()

            # Axis 1
            self.ax_frame[port_name]['ax1_info'] = {'name': port_name, 'axis': 1}

            self.ax_frame[port_name]['ax1_frame'] = QFrame()
            self.ax_frame[port_name]['ax1_frame'].setStyleSheet('''background-color: #555555;
                                      color: white;''')
            self.ax_frame[port_name]['ax1_layout'] = QVBoxLayout(self.ax_frame[port_name]['ax1_frame'])
            ax1_label = QLabel("Axis 1")
            ax1_label.setAlignment(Qt.AlignCenter)
            ax1_label.setFont(QFont('Arial', 12, QFont.Bold))

            # Test Button
            self.ax_frame[port_name]['ax1_test'] = QPushButton("Test")
            self.ax_frame[port_name]['ax1_test'].setStyleSheet(button_style())
            self.ax_frame[port_name]['ax1_test'].setFont(QFont('Arial', 10))
            self.ax_frame[port_name]['ax1_test'].clicked.connect(lambda: self.test_function(self.ax_frame[port_name]['ax1_info']))

            # Combo Box
            self.ax_frame[port_name]['ax1_combo'] = QComboBox()
            self.ax_frame[port_name]['ax1_combo'].setStyleSheet(combo_style())
            self.ax_frame[port_name]['ax1_combo'].setFont(QFont('Arial', 10))
            self.ax_frame[port_name]['ax1_combo'].setMaxVisibleItems(11)
            self.ax_frame[port_name]['ax1_combo'].addItems(['-', 'BD-X', 'BD-Y', 'BD-Z', 'BD-TX', 'BD-TY', 'NZ-X', 'NZ-Y', 'NZ-Z', 'NZ-R', 'None'])
            self.ax_frame[port_name]['ax1_combo'].currentTextChanged.connect(lambda text: self.ax_frame[port_name]['ax1_info'].__setitem__('combo_value', text))

            self.ax_frame[port_name]['ax1_sublayout'] = QHBoxLayout()
            self.ax_frame[port_name]['ax1_sublayout'].addWidget(self.ax_frame[port_name]['ax1_test'])
            self.ax_frame[port_name]['ax1_sublayout'].addWidget(self.ax_frame[port_name]['ax1_combo'])

            self.ax_frame[port_name]['ax1_layout'].addWidget(ax1_label, alignment=Qt.AlignTop)
            self.ax_frame[port_name]['ax1_layout'].addLayout(self.ax_frame[port_name]['ax1_sublayout'])

            # Axis 2
            self.ax_frame[port_name]['ax2_info'] = {'name': port_name, 'axis': 2}

            self.ax_frame[port_name]['ax2_frame'] = QFrame()
            self.ax_frame[port_name]['ax2_frame'].setStyleSheet('''background-color: #555555;
                                      color: white;''')
            self.ax_frame[port_name]['ax2_layout'] = QVBoxLayout(self.ax_frame[port_name]['ax2_frame'])
            ax2_label = QLabel("Axis 2")
            ax2_label.setAlignment(Qt.AlignCenter)
            ax2_label.setFont(QFont('Arial', 12, QFont.Bold))

            # Test Button
            self.ax_frame[port_name]['ax2_test'] = QPushButton("Test")
            self.ax_frame[port_name]['ax2_test'].setStyleSheet(button_style())
            self.ax_frame[port_name]['ax2_test'].setFont(QFont('Arial', 10))
            self.ax_frame[port_name]['ax2_test'].clicked.connect(lambda: self.test_function(self.ax_frame[port_name]['ax2_info']))

            # Combo Box
            self.ax_frame[port_name]['ax2_combo'] = QComboBox()
            self.ax_frame[port_name]['ax2_combo'].setStyleSheet(combo_style())
            self.ax_frame[port_name]['ax2_combo'].setFont(QFont('Arial', 10))
            self.ax_frame[port_name]['ax2_combo'].setMaxVisibleItems(11)
            self.ax_frame[port_name]['ax2_combo'].addItems(['-', 'BD-X', 'BD-Y', 'BD-Z', 'BD-TX', 'BD-TY', 'NZ-X', 'NZ-Y', 'NZ-Z', 'NZ-R', 'None'])
            self.ax_frame[port_name]['ax2_combo'].currentTextChanged.connect(lambda text: self.ax_frame[port_name]['ax2_info'].__setitem__('combo_value', text))

            self.ax_frame[port_name]['ax2_sublayout'] = QHBoxLayout()
            self.ax_frame[port_name]['ax2_sublayout'].addWidget(self.ax_frame[port_name]['ax2_test'])
            self.ax_frame[port_name]['ax2_sublayout'].addWidget(self.ax_frame[port_name]['ax2_combo'])

            self.ax_frame[port_name]['ax2_layout'].addWidget(ax2_label, alignment=Qt.AlignTop)
            self.ax_frame[port_name]['ax2_layout'].addLayout(self.ax_frame[port_name]['ax2_sublayout'])

            self.ax_frame[port_name]['sublayout'].addWidget(self.ax_frame[port_name]['ax1_frame'])
            self.ax_frame[port_name]['sublayout'].addWidget(self.ax_frame[port_name]['ax2_frame'])

            self.ax_frame[port_name]['layout'].addLayout(self.ax_frame[port_name]['sublayout'])

            self.axis_selection_layout.addWidget(self.ax_frame[port_name]['frame'], 1)

        elif state == Qt.Unchecked:
            self.checked_port.discard(port_name)
            if port_name in self.ax_frame.keys():
                self.ax_frame[port_name]['frame'].deleteLater()
                del self.ax_frame[port_name]

    # Test Function
    def test_function(self, ax_info):
        temp_ser = None
        
        try:
            temp_ser=serial.Serial(ax_info['name'], 115200, 8, serial.PARITY_NONE,
                                serial.STOPBITS_ONE, timeout=1)

            shared_data.ports.append(ax_info['name'])
            shared_data.connections.append(temp_ser)

            temp_connection = CRUX(self.logger)
            temp_connection.RTB(ax_info['axis'], 0, ax_info['name'])
            original_setting_speed = temp_connection.for_return

            if not original_setting_speed:
                raise TimeoutError(f"Driver not responding or wrong device connected in ({ax_info['name']}).")
            elif len(original_setting_speed) < 3:
                raise ValueError(f"Unexpected response from driver in ({ax_info['name']}): {original_setting_speed}")

            temp_connection.WTB(ax_info['axis'], ax_info['name'], 0, 1)
            temp_connection.RTB(ax_info['axis'], 0, ax_info['name'])

            for _ in range(self.test_cycle):
                temp_connection.RPS(ax_info['axis'], 0, ax_info['name'], 1)
                time.sleep(0.1)
                temp_connection.RPS(ax_info['axis'], 0, ax_info['name'], -1)
                time.sleep(0.1)

            temp_connection.WTB(ax_info['axis'], ax_info['name'], 0, int(original_setting_speed[2]))
            temp_connection.RTB(ax_info['axis'], 0, ax_info['name'])

        except Exception as e:
            self.logger.error(f"check_button_action error: {e}")

        finally:
            if temp_ser is not None and temp_ser.is_open:
                shared_data.ports.remove(ax_info['name'])
                shared_data.connections.remove(temp_ser)
                temp_ser.close()
                
                self.logger.log(f"{ax_info['name']} closed")
                time.sleep(0.1)
    
    # Setup Save Function
    def setup_save(self):
        if shared_data.connections:
            try:
                for connection in shared_data.connections:
                    if connection.is_open:
                        connection.close()
                        time.sleep(0.1)
            except Exception as e:
                self.logger.log(f"Error closing connections: {e}:")

        shared_data.connections = []
        shared_data.ports = []
        shared_data.port_axis_mapping = {}

        for port_name in self.ax_frame.keys():
            ser = None
            ser = serial.Serial(port_name, 115200, 8, serial.PARITY_NONE,
                                serial.STOPBITS_ONE, timeout=None)

            shared_data.port_axis_mapping[port_name] = (self.ax_frame[port_name]['ax1_info'], self.ax_frame[port_name]['ax2_info'])
            shared_data.connections.append(ser)
            shared_data.ports.append(port_name)
        
        self.model=CRUX(self.logger)
        shared_data.model=self.model

        try:
            port_option()
            find_driver_set()
        except Exception as e:
            self.logger.error(e)

        # self.logger.log(self.model)
        self.logger.log("Setup saved!")