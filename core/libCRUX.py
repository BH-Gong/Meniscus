import time
import pandas as pd
import threading
from datetime import datetime
import math
import matplotlib.pyplot as plt
import serial
import traceback

from core import shared_data
from core import utils

sys_default=[
    (1,0),(2,4),(6,0),(7,0),(8,0),(21,0),(22,0),(23,0),(61,1),(68,2000)
]

speedtable_default=[
(0,1,16,500,500),(1,2,20,500,2000),
(2,2,24,500,3000),(3,2,28,500,4000),
(4,2,32,500,5000),(5,2,36,500,6000),
(6,2,40,500,7000),(7,2,44,500,8000),
(8,2,48,500,9000),(9,2,52,500,10000)
]

class CRUX:
    def __init__(self, logger):
        self.logger = logger
        self.connections = shared_data.connections
        self.ports = shared_data.ports
        self.debounces = {}
        self.error_codes = all_error_code
        self.pos = shared_data.pos
        self.stop_lock = threading.Lock()
        self.emg_event = threading.Event()
        self.stop_flag = False
        self.commands = []
        self.line = []
        self.for_return = ()

    def __str__(self):
        return f"CRUX(ports={self.ports}, connections={self.connections})"

# command communication ##############################################################################################################################################################
    def select_port(self, port):
        if port in shared_data.ports:
            idx = shared_data.ports.index(port)

            return shared_data.connections[idx]
        
        return ValueError(f"Port '{port}' not found in shared_data.ports: {shared_data.ports}")

    def commun(self, code, connection, port):
        try:
            if code is not None:
                encode = b'\x02' + code.encode('ascii') + b'\r\n'
                connection.write(encode)

                utils.port_locker([port])
                lock = shared_data.port_lock[port]

                with lock:
                    self.logger.hidden(f"Sending command: {code}")

                    response = b''
                    start_time = time.time()

                    while time.time() - start_time < 3:

                        if shared_data.stop_event is not None and shared_data.stop_event.is_set():

                            return

                        waiting = connection.in_waiting

                        if waiting > 0:
                            response += connection.read(waiting)

                            if b'\n' in response:
                                break

                    if response:
                        decode_response = response.decode('ascii')
                        self.decode_response(decode_response)

                    self.logger.hidden(f"Commanding Done...")
    
        except Exception as e:
            self.logger.error(e)

    def decode_response(self, response):
        try:
            parts = response.rstrip('\r\n').split('\t')
            id_code = parts[0]
            command_code = parts[1][:3]
            a = parts[1][-1:]
            params = parts[2:]

            if a.isdigit():
                params.insert(0, a)

            if id_code == 'C':
                if command_code == 'APS':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Absolute position drive, axis No.{axis_no}.')

                elif command_code == 'FRP':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Free rotation drive, axis No.{axis_no}.')

                elif command_code == 'IDN':
                    model_name = params[0]
                    version = int(params[1]) / 1000

                    self.for_return = (model_name, version)
                    self.logger.hidden(f'{model_name} Ver.{version}')

                elif command_code == 'MPI':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f"Initial parameter setted for MPS, axis No.{axis_no}.")

                elif command_code == 'MPS':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f"Multi-axis position drive, {axis_no}(first one).")

                elif command_code == 'ORG':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Origin return drive, axis No.{axis_no}.')

                elif command_code == 'RDP':
                    axis_no = params[0]
                    position = params[1]

                    self.for_return = (axis_no, position)
                    self.logger.hidden(f'Current position of Axis No.{axis_no} is {position}.')

                elif command_code == 'RPS':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Relative position drive, axis No.{axis_no}.')

                elif command_code == 'RST':
                    self.for_return = ()
                    self.logger.hidden(f'System reseted.')

                elif command_code == 'RSY':
                    axis_no = params[0]
                    sys_no = params[1]
                    set_value = params[2]

                    self.for_return = (axis_no, sys_no, set_value)
                    self.logger.hidden(f'Set value of system No.{sys_no} in axis No.{axis_no} as {set_value}')

                elif command_code == 'RTB':
                    axis_no = params[0]
                    spdtable_no = params[1]
                    str_spd = params[2]
                    max_spd = params[3]
                    acc_time = params[4]
                    acc_mode = params[5]

                    self.for_return = (axis_no, spdtable_no, str_spd, max_spd, acc_time, acc_mode)
                    self.logger.hidden(f'Axis No.{axis_no} : speedtable No.{spdtable_no},'
                                       f'Initial Velocity={str_spd}, Maximum Velocity={max_spd},' 
                                       f'Acceleration Time={acc_time}, Acceleration Mode={acc_mode}' 
                                       f'(1:Rectangular drive, 2:Trapezoidal drive)')

                elif command_code == 'SAV':
                    self.for_return = ()
                    self.logger.hidden(f'Position data saved.')

                elif command_code == 'STP':
                    axis_no = params[0]

                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Motor stop, axis No.{axis_no}.')
                
                elif command_code == 'STR':
                    axis_no = params[0]
                    drv_state = params[1]
                    org_sig = params[2]
                    norg_sig = params[3]
                    ccw_lim = params[4]
                    cw_lim = params[5]

                    if axis_no == '1' or axis_no == '2':
                        self.for_return = (axis_no, drv_state, org_sig, norg_sig, ccw_lim, cw_lim)
                        self.logger.hidden(f'Axis No.{axis_no} : driving state={drv_state},'
                                           f'ORG signal={org_sig}, NORG signal={norg_sig},' 
                                           f'CCW limit signal={ccw_lim}, CW limit signal={cw_lim}'
                                           f'(0:OFF(STOP), 1:ON(Operating))')

                    elif axis_no == '0':
                        self.for_return = (axis_no, drv_state)
                        self.logger.hidden(f'Axis No.{axis_no} : EMG signal={drv_state} (0:OFF, 1:ON).')
                
                elif command_code == 'WRP':
                    axis_no = params[0]
                    set_value = params[1]

                    self.for_return = (axis_no, sys_no, set_value)
                    self.logger.hidden(f'Set position value of axis No.{axis_no} as {set_value}.')

                elif command_code == 'WSY':
                    axis_no = params[0]
                    sys_no = params[1]
                    set_value = params[2]

                    self.for_return = (axis_no, sys_no, set_value)
                    self.logger.hidden(f'Set value of system No.{sys_no} in axis No.{axis_no} as {set_value}.')

                elif command_code == 'WTB':
                    axis_no = params[0]
                    
                    self.for_return = (axis_no,)
                    self.logger.hidden(f'Write speed table, axis No.{axis_no}.')

                else:
                    raise ValueError(f'Unexpected response : {response}')

            elif id_code == ('E'):
                code_pack_0 = ['SYS']
                code_pack_1 = ['APS', 'FRP', 'MPI', 'MPS', 'ORG', 'RPS', 'RSY', 
                               'RTB', 'STP', 'STR', 'WRP', 'WSY', 'WTB']
                code_pack_2 = ['RST', 'SAV']

                if command_code in code_pack_0:
                    error_typ = 'sys'
 
                elif command_code in code_pack_1:
                    error_typ = 'gen'

                elif command_code in code_pack_2:
                    error_typ = 'rst_sav'

                else:
                    raise ValueError(f'Unexpected response : {response}')

                error_para = params
                error_msg = self.get_error_message(error_typ, error_para)

                self.for_return = (error_typ, error_para)
                self.logger.error(f'{error_msg}')

            else:
                raise ValueError(f'Unexpected response : {response}')

            self.logger.hidden(f"Data received: {response}")

        except Exception as e:
            traceback.print_exc()
            self.logger.error(traceback.format_exc())
            
    def check_end(self, connection, port):
        start_time = time.time()

        while True:
            if time.time() - start_time >= 3:
                raise TimeoutError(f"No response received for command '{code}' on port '{port}'.")

            all_stopped = True

            for axis_no in range(1, 3):
                code = 'STR%d' %(axis_no)
                encode = b'\x02' + code.encode('ascii') + b'\r\n'
                connection.write(encode)

                encoded_response = connection.read_until(b'\n')
                response = encoded_response.decode('ascii')

                para = self.decode_response(code, response)

                if not para:
                    raise ValueError(f"Invalid response for '{code}': {response!r}")

                if para[0] == '0':
                    pass
                elif para[0] == '1':
                    all_stopped = False
                else:
                    raise ValueError(f"Unexpected response format: {response}")

            if all_stopped:
                break

            time.sleep(0.01)

        return True

    def get_error_message(self, error_typ, error_para):
        if error_typ == 'sys':
            err_msg = self.lookup_error(error_para[0])
            s = f'System Error : {err_msg}'
        elif error_typ == 'gen':
            err_msg = self.lookup_error(error_para[1])
            s = f'Error at {error_para[0]} : {err_msg}'
        elif error_typ == 'rst_sav':
            err_msg = self.lookup_error(error_para[0])
            s = f'STR, SAV Error : {err_msg}'

        return s

    def lookup_error(self, error_no):
        if error_no == '0':
            err_str = 'Emergency stop status is detected.'
        elif error_no == '1':
            err_str = 'No STX on the head of the command.'
        elif error_no == '4':
            err_str = 'Characters other than specified characters and numbers are included.'
        elif error_no == '5':
            err_str = 'No applicable command.'
        elif error_no == '100':
            err_str = 'Total number of parameters is incorrect.'
        elif error_no in ('101', '102', '103', '104', '105', '106'):
            err_str = f'Parameter value on {error_no[-1]}th parameter is out of range.'
        elif error_no == '121':
            err_str = 'There is no applicable system.'
        elif error_no == '130':
            err_str = 'Due to system settings being made, commands cannot be executed.'
        elif error_no == '300':
            err_str = 'Tried to turn excitation of the axis being driven OFF.'
        elif error_no == '302':
            err_str = 'Tried to operate while axes are driving.'
        elif error_no == '303':
            err_str = 'Tried to write the present value of the axis during driving.'
        elif error_no == '304':
            err_str = 'Tried to drive in the CW direction in the CW limit detection state. OR Stopped at CW limit during driving.'
        elif error_no == '305':
            err_str = 'Tried to drive in the CCW direction in the CCW limit detection state. OR Stopped at CCW limit during driving.'
        elif error_no == '306':
            err_str = 'Tried to conduct MPS driving in the limit detection state direction. OR Some MPS driving axes stopped at limit.'
        elif error_no == '307':
            err_str = 'Both CW and CCW limiters are included.'
        elif error_no == '308':
            err_str = 'Tried to move an axis with its excitation OFF.'
        elif error_no == '310':
            err_str = 'Coordinates of the mov ement destination are outside of the manageable range.'
        elif error_no == '313':
            err_str = 'Tried to write the system settings of the axis being driven.'
        elif error_no == '314':
            err_str = 'The axis being driven was stopped due to emergency stop detection.'
        elif error_no == '325':
            err_str = 'The axis being driven was stopped by INCOM due to a command.'
        elif error_no == '500':
            err_str = 'Tried to drive in MPS with the MPI command not issued.'
        elif error_no == '505':
            err_str = 'Coordinates of the first axis movement destination are outside of the manageable range.'
        elif error_no == '506':
            err_str = 'Coordinates of the second axis movement destination are outside of the manageable range.'
        elif error_no == '511':
            err_str = 'The first axis and second axis are the same axis.'
        elif error_no == '605':
            err_str = 'Tried to set the start speed in excess of 80% of the maximum speed.'
        elif error_no == '700':
            err_str = 'Tried to change an incompatible system setting.'
        elif error_no == '800':
            err_str = 'Tried to execute a drive command during emergency stop.'
        elif error_no == '804':
            err_str = 'Tried to execute an RST command during drive.'
        else:
            err_str = ""
            raise ValueError(f'Unexpected error number : {error_no}') 

        return err_str
    
    def send_signals(self, codes, ports):
        try:
            print("send_signals start")
            threads = []

            for code, port in zip(codes, ports):
                if self.emg_event.is_set():
                    return
                
                if code is not None:
                    connection=self.select_port(port)
                    self.logger.log(f'{code} connection is {connection} to {port}')
                    t = threading.Thread(target=self.commun, args=(code, connection, port))
                    t.start()
                    threads.append(t)
                else:
                    pass

            for t in threads:
                t.join()
            print("send_signals end")

        except Exception as e:
            self.logger.error(e)

    def emergency_stop(self):
        utils.thread_close(shared_data.worker_thread, shared_data.stop_event, shared_data.command_queue)

        self.logger.error("Emergency Stop!")

        if shared_data.ports:
            for port in shared_data.ports:
                try:
                    self.emg_STP(0, port)
                except Exception as e:
                    self.logger.error(f"Failed to send emergency stop to port: {e}")

    ##command code ##############################################################################################################################################################
    def APS(self,axis,speedtable,port,pos_pulse):
        connection=self.select_port(port)
        code1='APS%d/%d/%d/%d' %(axis,speedtable,pos_pulse,0)
        self.commun(code1,connection,port)
        code2='RDP%d' %axis
        self.commun(code2,connection,port)

    def MPI(self,axis,speedtable,port,drive_type):
        connection=self.select_port(port)
        code1='MPI%d/%d/%d' %(axis,drive_type,speedtable)
        self.commun(code1,connection,port)
        # code2='RDP%d' %axis
        # self.commun(code2,connection,port)

    def MPS(self, axis1, axis2, port, drive_type, pos1, pos2, feedrate,abs_flag):
        connection=self.select_port(port)
        pos=self.pos
        pos3=pos['pos_z']
        vel_x, vel_y, vel_z = utils.cal_vel(pos, pos1, pos2, pos3, feedrate,abs_flag)

        self.WTB(axis1, port, axis1,vel_x)
        self.WTB(axis2, port, axis2,vel_y)
        
        self.MPI(axis1,axis1,port,drive_type)
        self.MPI(axis2,axis2,port,drive_type)
 
        code1='MPS%d/%d/%d/%d/%d' %(axis1,pos1,axis2,pos2,0)
        self.commun(code1,connection,port)
        code2='RDP%d' %axis1
        self.commun(code2,connection,port)
        code3='RDP%d' %axis2
        self.commun(code3,connection,port)

    def ORG(self, axis, speedtable, port):
        connection=self.select_port(port)
        code1='ORG%d/%d/%d' %(axis,speedtable,0)
        self.commun(code1,connection,port)
        code2='RDP%d' %axis
        self.commun(code2,connection,port)

    def RDP(self, axis,port):
        connection=self.select_port(port)
        code='RDP%d' %axis
        self.commun(code,connection,port)

    def RTB(self, axis, table_no, port):
        connection=self.select_port(port)
        code='RTB%d/%d' %(axis, table_no)
        self.commun(code, connection, port)
        
    def RPS(self, axis, speedtable, port, pos_pulse):
        connection=self.select_port(port)
        code1='RPS%d/%d/%d/%d' %(axis,speedtable,pos_pulse,0)
        self.commun(code1,connection,port)
        code2='RDP%d' %axis
        self.commun(code2,connection,port)

    def WTB(self,axis,port,speedtable_No,vel): ## write speedtable
        connection=self.select_port(port)
        code='WTB%d/%d/%d/%d/%d/%d' %(axis,speedtable_No,vel,vel,1,1)
        self.commun(code,connection,port)
    
    def RSY(self,axis,sys_no,port):
        connection=self.select_port(port)
        code='RSY%d/%d' %(axis,sys_no)
        self.commun(code,connection,port)

    def WSY(self,axis,sys_no,value,port): ## write system setting
        connection=self.select_port(port)
        sys_setting=self.change_sys_setting(sys_no,value)
        code='WSY%d/%d/%d' %(axis,sys_setting[0],sys_setting[1])
        self.commun(code,connection,port)

    def STP(self,axis,port):
        connection=self.select_port(port)
        code='STP%d/%d' %(axis,0)
        self.commun(code,connection,port)

    def emg_STP(self, axis, port):
        connection=self.select_port(port)
        code='STP%d/%d' %(axis, 1)
        self.commun(code, connection, port)

    def FRP(self, axis, speedtable, port, direction):
        connection=self.select_port(port)
        code='FRP%d/%d/%d' %(axis, speedtable, direction)
        self.commun(code,connection,port)

# g code to motor code ################################################################################
    def plot_trajectory(self,trajectory):
        x_coords = [point[0] for point in trajectory]
        y_coords = [point[1] for point in trajectory]

        plt.figure(figsize=(10, 10))
        plt.plot(x_coords, y_coords, marker='o')
        plt.title('G-code Trajectory')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.grid(True)
        plt.axis('equal')
        for i in range(len(trajectory)):
            plt.text(x_coords[i], y_coords[i], str(i))
        plt.show()

    def parse_gcode_line(self,line):
        keys=['G', 'M', 'X', 'Y', 'Z', 'I', 'J', 'K', 'P', 'Q', 'R', 'F']
        params = {key: None for key in keys}

        for part in line.split():
            if part[0] in params:
                key=part[0]
                try:
                    value=float(part[1:])
                except ValueError:
                    value=None
                params[key]=value
        return params

    def generate_arc_points(self, cx, cy, cp_z,radius, start_angle, end_angle, is_clockwise, num_points=100):
        points = []
        if is_clockwise:
            step = -abs(end_angle - start_angle) / num_points
        else:
            step = abs(end_angle - start_angle) / num_points

        for i in range(num_points):
            angle = start_angle + (i+1) * step
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            z=cp_z
            points.append((x, y,z))
        return points


    ## 추후 수정
    def convert_cir_to_linear(self, line, gcode,current_position,trajectory,resolution=50):
        params = self.parse_gcode_line(line)
        cx = current_position['X'] + params.get('I', 0)
        cy = current_position['Y'] + params.get('J', 0)
        cp_z=current_position['Z']
        radius = math.sqrt(params.get('I', 0)**2 + params.get('J', 0)**2)
        start_angle = math.atan2(current_position['Y'] - cy, current_position['X'] - cx)
        if params['X'] is not None and params['Y'] is not None:
            end_angle = math.atan2(params['Y'] - cy, params['X'] - cx)
            current_position['X'] = params['X']
            current_position['Y'] = params['Y']
        else: 
            end_angle = start_angle+2*math.pi
        is_clockwise = line.startswith('G2')
        points = self.generate_arc_points(cx, cy, cp_z, radius, start_angle, end_angle, is_clockwise, resolution)

        for x, y ,z in points:
            gcode.append(f'G1 X{x:.4f} Y{y:.4f}')
            trajectory.append((x, y, z))

        return gcode,trajectory,current_position

    def convert_spline_to_linear(self, line, gcode, current_position,trajectory,resolution=100):
        point=[]
        params = self.parse_gcode_line(line)
        cp_z=current_position['Z']
        if params['I'] is not None and params['J'] is not None:
            p1_x=current_position['X']+params['I']
            p1_y=current_position['Y']+params['J']
            p2_x=params['X']+params['P']
            p2_y=params['Y']+params['Q']
            
            for i in range(resolution):
                t=(i+1)/resolution
                s=1-t
                px=(s**3)*current_position['X']+3*(s**2)*t*(p1_x)+3*s*(t**2)*(p2_x)+(t**3)*params['X']
                py=(s**3)*current_position['Y']+3*(s**2)*t*(p1_y)+3*s*(t**2)*(p2_y)+(t**3)*params['Y']
                point.append((px,py,cp_z))
        else:
            p_x=params['X']+params['P']
            p_y=params['Y']+params['Q']
            for i in range(resolution):
                t=(i+1)/resolution
                s=1-t
                px=(s**2)*current_position['X']+2*s*t*p_x+(t**2)*params['X']
                py=(s**2)*current_position['Y']+2*s*t*p_y+(t**2)*params['Y']
                point.append((px,py,cp_z))

        for x, y,z in point:
            trajectory.append((x, y,z))
            gcode.append(f'G1 X{x:.4f} Y{y:.4f}')

        current_position['X'] = params['X']
        current_position['Y'] = params['Y']
        return gcode,trajectory,current_position

    def linear_gcode(self,line,gcode,current_position,trajectory):
        params = self.parse_gcode_line(line)
        gcode.append(line)

        ## X, Y, Z are not None
        if params['X'] is not None and params['Y'] is not None and params['Z'] is not None:
            current_position['X'] = params.get('X', current_position['X'])
            current_position['Y'] = params.get('Y', current_position['Y'])
            current_position['Z'] = params.get('Z', current_position['Z'])
        ## X is None    
        elif params['X'] is None and params['Y'] is not None and params['Z'] is not None: 
            current_position['Y'] = params.get('Y', current_position['Y'])
            current_position['Z'] = params.get('Z', current_position['Z'])
        ## Y is None    
        elif params['X'] is not None and params['Y'] is None and params['Z'] is not None: 
            current_position['X'] = params.get('X', current_position['X'])
            current_position['Z'] = params.get('Z', current_position['Z'])
        ## Z is None
        elif params['X'] is not None and params['Y'] is not None and params['Z'] is None: 
            current_position['X'] = params.get('X', current_position['X'])
            current_position['Y'] = params.get('Y', current_position['Y'])

        ## X,Y are None
        elif params['X'] is None and params['Y'] is None and params['Z'] is not None: 
            current_position['Z'] = params.get('Z', current_position['Z'])
        ## X,Z are None
        elif params['X'] is None and params['Y'] is not None and params['Z'] is None:
            current_position['Y'] = params.get('Y', current_position['Y'])
        ## Y,Z are None
        elif params['X'] is not None and params['Y'] is None and params['Z'] is None:
            current_position['X'] = params.get('X', current_position['X'])

        trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        return gcode, trajectory,current_position

    def org_gcode(self, line,gcode,current_position,trajectory):
        gcode.append(line)
        if line == 'G28':
            current_position['X']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
            current_position['Y']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z'])) 
            current_position['Z']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line == 'G28 X':
            current_position['X']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line =='G28 Y':
            current_position['Y']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line =='G28 Z':
            current_position['Z']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line == 'G28 X Y':
            current_position['X']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
            current_position['Y']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line == 'G28 X Z':
            current_position['X']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
            current_position['Z']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        elif line == 'G28 Y Z':
            current_position['Y']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
            current_position['Z']=0
            trajectory.append((current_position['X'], current_position['Y'],current_position['Z']))
        return gcode, trajectory,current_position