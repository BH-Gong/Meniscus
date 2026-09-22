import math
import time
import numpy as np
from tkinter import filedialog

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import sys
import threading

from matplotlib.figure import Figure
from matplotlib.pyplot import plot
import serial

from core import shared_data

class SquareButton(QPushButton):
    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return width

    def resizeEvent(self, event):
        size = min(self.width(), self.height())
        self.setIconSize(QSize(int(size * 0.7), int(size * 0.7)))
        super().resizeEvent(event)

class FixedFrameRatio(QFrame):
    def __init__(self, wRatio, hRatio):
        super().__init__()
        self.ratio = wRatio / hRatio
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        w = self.width()
        h = int(w / self.ratio)
        self.setFixedHeight(h)
        super().resizeEvent(event)

def button_style():
    return (
            """QPushButton {
            background-color: #555555;
            border: 3px solid #888888;
            border-radius: 6px;
            color: white;
            padding: 10px;
            }
            QPushButton:hover {
            background-color: #666666;
            }
            QPushButton:pressed {
            background-color: #333333;
            }
            QPushButton:disabled {
            background-color: #333333;
            color: #888888;
            }"""
            )

def combo_style():
    return (
            """QComboBox {
            background-color: #555555;
            border: 3px solid #888888;
            border-radius: 6px;
            color: white;
            padding: 10px;
            }
            QComboBox:hover {
            background-color: #666666;
            }
            QComboBox:pressed {
            background-color: #333333;
            }
            QComboBox:disabled {
            background-color: #333333;
            color: #888888;
            }
            QComboBox::drop-down {
            width: 20px;
            margin-top: 5px;
            margin-bottom: 5px;
            margin-right: 5px;
            margin-left: 5px;
            }"""
    )

def tree_style():
    return ("""
            QTreeWidget {
                background-color: #444444;
                color: white;
                gridline-color: #222222;
            }
            QHeaderView::section {
                background-color: #555555;
                color: #FFFFFF;
                padding: 4px;
                border: 1px solid #222222;
                font: bold 12pt Arial;
            }
            """)

def chk_none_variable(data):
    temp_list = []
    temp_bool = False

    for key, value in data.items():
        if value is None:
            temp_list.append(key)
            temp_bool = True

    return temp_list, temp_bool

def chk_display_panel(self):
    if hasattr(self, "serial_window") and self.serial_window is not None:
        return True
    elif hasattr(self, "control_window") and self.control_window is not None:
        return True
    elif hasattr(self, "g_code_window") and self.g_code_window is not None:
        return True
    else:
        return False

def serial_close(serial):
    if serial is not None and getattr(serial, 'is_open', False):
        try:
            serial.close()
        except Exception:
            pass

def thread_close(worker_thread, stop_event, command_queue):
    if stop_event is not None:
        stop_event.set()

    if command_queue is not None:
        try:
            with command_queue.mutex:
                command_queue.queue.clear()
            command_queue.put(shared_data.SENTINEL)
        except Exception:
            pass

    if (
        worker_thread is not None and
        worker_thread.is_alive() and
        worker_thread != threading.current_thread()
    ):
        worker_thread.join(timeout=2)

    shared_data.worker_thread = None
    shared_data.stop_event = None

def close(serials, worker_thread, stop_event, command_queue, event=None):
    thread_close(worker_thread, stop_event, command_queue)

    if serials:
        for serial in serials:
            serial_close(serial)

    if event is not None:
        event.accept()
    else:
        sys.exit(0)

def activate(logger, act_btn, deact_btn, prss_btn):
    if prss_btn.text() == "Activate":
        active_flag = True
        shared_data.active_flag = active_flag
        logger.log("Activated!")
        act_btn.setDisabled(True)
        deact_btn.setEnabled(True)

    elif prss_btn.text() == "Deactivate":
        active_flag = False
        shared_data.active_flag = active_flag
        logger.log("Deactivated!")
        deact_btn.setDisabled(True)
        act_btn.setEnabled(True)

def open_file(logger, tree, model):
    try:
        file_path = filedialog.askopenfilename(filetypes=[("G-code files", "*.gcode")])
        if file_path:
            tree.clear()
            with open(file_path, 'r') as file:
                commands=file.readlines()
                for i, command in enumerate(commands, start=1):
                    item = QTreeWidgetItem([str(i), command.strip()])
                    tree.addTopLevelItem(item)
        
        gcode = []
        trajectory = []
        current_position = {'X': 0, 'Y': 0, 'Z': 0}
        viz_absolute = True 
        
        total_seconds = 0.0
        current_feedrate = 1000.0 
        rapid_feedrate = 5000.0   

        trajectory.append((0, 0, 0))

        for line in commands: 
            line = line.strip()
            if not line: continue
            parts = line.split()
            g_command = parts[0]

            if g_command == 'G90':
                viz_absolute = True
                gcode.append(line)
            elif g_command == 'G91':
                viz_absolute = False
                gcode.append(line)
            
            elif g_command in ['G0', 'G1']:
                params = model.parse_gcode_line(line)
                move_feedrate = current_feedrate
                if g_command == 'G0': move_feedrate = rapid_feedrate
                elif params['F'] is not None:
                    current_feedrate = params['F']
                    move_feedrate = current_feedrate

                new_x = current_position['X']
                new_y = current_position['Y']
                new_z = current_position['Z']
                dx = 0; dy = 0; dz = 0

                if viz_absolute:
                    if params['X'] is not None: 
                        dx = params['X'] - current_position['X']
                        new_x = params['X']
                    if params['Y'] is not None: 
                        dy = params['Y'] - current_position['Y']
                        new_y = params['Y']
                    if params['Z'] is not None: 
                        dz = params['Z'] - current_position['Z']
                        new_z = params['Z']
                else:
                    if params['X'] is not None: 
                        dx = params['X']
                        new_x += params['X']
                    if params['Y'] is not None: 
                        dy = params['Y']
                        new_y += params['Y']
                    if params['Z'] is not None: 
                        dz = params['Z']
                        new_z += params['Z']
                
                distance = math.sqrt(dx**2 + dy**2 + dz**2)
                if move_feedrate > 0:
                    total_seconds += (distance / move_feedrate)

                current_position['X'] = new_x
                current_position['Y'] = new_y
                current_position['Z'] = new_z
                trajectory.append((new_x, new_y, new_z))
                gcode.append(line)

            elif g_command in ['G2', 'G3']:
                gcode, trajectory, current_position = model.convert_cir_to_linear(
                    line, gcode, current_position, trajectory, resolution=100
                )
            elif g_command == 'G28':
                current_position = {'X': 0, 'Y': 0, 'Z': 0}
                trajectory.append((0, 0, 0))
                gcode.append(line)
            elif g_command == 'G04':
                dwell_time = 0.0
                for part in parts:
                    if part.startswith('P'):
                        try: dwell_time = float(part[1:]) / 1000.0
                        except: pass
                    elif part.startswith('S') or part.startswith('X'):
                        try: dwell_time = float(part[1:])
                        except: pass
                total_seconds += dwell_time
                gcode.append(line)
            elif g_command in ['G98', 'G99', 'G5']:
                gcode.append(line)

        # gcode.append('G99') # 원점 복귀

        gcode = gcode
        trajectory = trajectory

        logger.log(f"File '{file_path}' loaded successfully!")

        return gcode, trajectory, total_seconds
        
    except Exception as error:
        logger.error(str(error))
        return None

def plot_trajectory(trajectory):
    if not trajectory: return

    start_point = trajectory[0]
    end_point = trajectory[-1]

    x_coords = [point[0] for point in trajectory]
    y_coords = [point[1] for point in trajectory]
    z_coords = [point[2] for point in trajectory]

    fig = Figure(figsize=(5, 5), dpi=100)
    fig.patch.set_facecolor('#333333')
    
    plot = fig.add_subplot(111, projection='3d')
    plot.plot(x_coords, y_coords, z_coords, color='#00ffff', linewidth=2)
    plot.set_facecolor('#333333')

    plot.scatter(start_point[0], start_point[1], start_point[2], color='green', s=20, label='Start')
    plot.scatter(end_point[0], end_point[1], end_point[2], color='red', s=20, label='End')
    
    plot.set_xlabel('X-axis')
    plot.set_ylabel('Y-axis')
    plot.set_zlabel('Z-axis')

    zmin, zmax = plot.get_zlim()
    plot.set_zlim(zmin, zmax)
    xmin, xmax = plot.get_xlim()
    ymin, ymax = plot.get_ylim()

    plot.legend(facecolor='#555555', labelcolor = 'white', edgecolor='#000000')

    if xmax - xmin > ymax - ymin:
        plot.set_ylim(ymin * (xmax - xmin) / (ymax - ymin), ymax * (xmax - xmin) / (ymax - ymin))
    elif ymax - ymin > xmax - xmin:
        plot.set_xlim(xmin * (ymax - ymin) / (xmax - xmin), xmax * (ymax - ymin) / (xmax - xmin))

    plot.tick_params(colors='white')

    plot.xaxis._axinfo['grid']['color'] = '#888888'
    plot.yaxis._axinfo['grid']['color'] = '#888888'
    plot.zaxis._axinfo['grid']['color'] = '#888888'

    plot.xaxis.set_pane_color((0.2,0.2,0.2,1))
    plot.yaxis.set_pane_color((0.2,0.2,0.2,1))
    plot.zaxis.set_pane_color((0.2,0.2,0.2,1))

    plot.set_xlabel('X-axis', color='white')
    plot.set_ylabel('Y-axis', color='white')
    plot.set_zlabel('Z-axis', color='white')

    plot.invert_yaxis()

    return fig

def format_seconds(s):
    h, r = divmod(s, 3600)
    m, s_r = divmod(r, 60)
    
    return f"{int(h):02d}:{int(m):02d}:{s_r:06.3f}"

def port_option():
    if shared_data.port_axis_mapping == {}:
        raise ValueError("port_axis_mapping is missig")
    
    axis_bdx = axis_bdy = axis_bdz = axis_nzx = axis_nzy = axis_nzz = axis_nzr = axis_bdtx = axis_bdty = None
    port_bdx = port_bdy = port_bdz = port_nzx = port_nzy = port_nzz = port_nzr = port_bdtx = port_bdty = None

    for port in shared_data.port_axis_mapping.values():
        for i in range(len(port)):
            if port[i].get('combo_value') == 'BD-X':
                axis_bdx, port_bdx = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'BD-Y':
                axis_bdy, port_bdy = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'BD-Z':
                axis_bdz, port_bdz = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'NZ-X':
                axis_nzx, port_nzx = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'NZ-Y':
                axis_nzy, port_nzy = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'NZ-Z':
                axis_nzz, port_nzz = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'NZ-R':
                axis_nzr, port_nzr = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'BD-TX':
                axis_bdtx, port_bdtx = port[i].get('axis'), port[i].get('name')
            elif port[i].get('combo_value') == 'BD-TY':
                axis_bdty, port_bdty = port[i].get('axis'), port[i].get('name')

    info_dict = {'axis_BDX': axis_bdx, 'axis_BDY': axis_bdy, 'axis_BDZ': axis_bdz, 
                 'axis_NZX': axis_nzx, 'axis_NZY': axis_nzy, 'axis_NZZ': axis_nzz,
                 'axis_NZR': axis_nzr, 'axis_BDTY': axis_bdtx, 'axis_BDTY': axis_bdty,
                 'port_BDX': port_bdx, 'port_BDY': port_bdy, 'port_BDZ': port_bdz, 
                 'port_NZX': port_nzx, 'port_NZY': port_nzy, 'port_NZZ': port_nzz,
                 'port_NZR': port_nzr, 'port_BDTX': port_bdtx, 'port_BDTY': port_bdty}
    
    shared_data.info_dict = info_dict

    return info_dict

def find_driver_set():
    if shared_data.info_dict == {}:
        raise ValueError("info_dict is missig")
    
    port_group = {}
    for key in shared_data.info_dict.keys():
        if key.startswith('port'):
            port = shared_data.info_dict[key]
            
            port_group[port] = []
            port_group[port].append(key.split('_')[-1])

    shared_data.port_group = port_group

def calculate_parameter(params):
    x_par = 4 * params['X'] if params['X'] is not None else 0
    y_par = 4 * params['Y'] if params['Y'] is not None else 0
    z_par = 4 * params['Z'] if params['Z'] is not None else 0
    feedrate = 4 * params['F'] if params['F'] is not None else None
    
    return x_par, y_par, z_par, feedrate

def calculate_displacement(params, pos):
    if params['X'] is not None:
        del_x = 4 * (params['X'] - pos['X'])
        pos['X'] = params.get('X')
    else: del_x = 0
    if params['Y'] is not None:
        del_y = 4 * (params['Y'] - pos['Y'])
        pos['Y'] = params.get('Y') 
    else: del_y = 0 
    if params['Z'] is not None:
        del_z = 4 * (params['Z'] - pos['Z'])
        pos['Z'] = params.get('Z')
    else: del_z = 0

    return pos, del_x, del_y, del_z

def search_target_port(logger, target_value):
    axis=None
    port=None

    for data in shared_data.port_axis_mapping.values():
        for i in range(len(data)):
            if target_value in data[i]['combo_value']:
                axis=data[i]['axis']
                port=data[i]['name']
                return axis, port
            
    logger.error(f"Target value '{target_value}' not found in port_axis_mapping.")

    return None, None

def is_grouped(a, b):
    return shared_data.info_dict.get(a) == shared_data.info_dict.get(b)

def is_worker_running(worker_thread, stop_event):
    return (
        worker_thread is not None and
        worker_thread.is_alive() and
        not stop_event.is_set()
    )

def cal_vel(pos, pos1, pos2, pos3, feedrate, abs_flag):
    vel = feedrate
    
    if abs_flag:
        del1 = pos1 - pos['pos_x']
        del2 = pos2 - pos['pos_y']
        del3 = pos3 - pos['pos_z']
    else:
        del1 = pos1
        del2 = pos2
        del3 = pos3

    pos_s = ((del1**2 + del2**2 + del3**2))**(0.5)

    if pos_s == 0:
        return 0, 0, 0

    vel_x = abs(vel * (del1 / pos_s))
    vel_y = abs(vel * (del2 / pos_s))
    vel_z = abs(vel * (del3 / pos_s))

    vel_x = seperate_speed(vel_x)
    vel_y = seperate_speed(vel_y)
    vel_z = seperate_speed(vel_z)

    return vel_x, vel_y, vel_z

def seperate_speed(vel):
    if vel < 1:
        return 1
    return vel

def port_locker(ports):
    for port in ports:
        if port not in shared_data.port_lock:
            shared_data.port_lock[port] = threading.Lock()