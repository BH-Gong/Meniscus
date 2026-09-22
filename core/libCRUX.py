import time
import sqlite3
import pandas as pd
import threading
from datetime import datetime
import math
import matplotlib.pyplot as plt
import serial

from core import shared_data
from core import utils

all_error_code={'0':'Emergency stop status is detected (not dependent on the driv e conditions)',
        '1':'No STX on the head of the command.',
        '4':'Characters other than specified characters and numbers are included.',
        '5':'No applicable command.',
        '100':'Total number of parameters is incorrect.',
        '101':'Parameter value on 1st parameter is out of range.',
        '102':'Parameter value on 2nd parameter is out of range.',
        '103':'Parameter value on 3rd parameter is out of range.',
        '104':'Parameter value on 4th parameter is out of range.',
        '105':'Parameter value on 5th parameter is out of range.',
        '106':'Parameter value on 6th parameter is out of range.',
        '121':'There is no applicable system No.',
        '130':'Due to system settings being made, commands cannot be executed.',
        '300':'Tried to turn excitation of the axis being driven OFF.',
        '302':'Tried to operate while axes are driving.',
        '303':'Tried to write the present value of the axis during driving',
        '304':('Stopped at CW limit during driving. ','Tried to drive in the CW direction in the CW limit detection state.'),
        
        '305':('Stopped at CCW limit during driving. ','Tried to drive in the CCW direction in the CCW limit detection state.'),
        '306':('Some MPS driving in the limit detection state direction','Tried to conduct MPS driving in the limit detection state direction.'),
        '307':'Both CW and CCW limiters are included.',
        '308':'Tried to move an axis with its excitation OFF.',
        '310':'Coordinates of the movement destination are outside of the manageable range.',
        '313':'Tried to write the system settings of the axis being driven.',
        '314':'The axis being driven was stopped due to emergency stop detection.',
        '325':'The axis being driven was stopped by INCOM due to a command.',
        '500':'Tried to drive iin MPS with the MPI command not issued.',
        '505':'Coordinates of the first axis movement destination are outside of the manageable range.',
        '506':'Coordinates of the second axis movement destination are outside of the manageable range.',
        '511':'The first axis and second axis are the same axis.',
        '605':'Tried to set the start speed in excess of 80% of the maximum speed',
        '700':'Tried to change an incompatible system setting No.',
        '800':'Tried to execute a drive command during emergency stop.',
        '804':'Tried to execute an RST command during drive.'}

sys_default=[
    (1,0),(2,4),(6,0),(7,0),(8,0),(21,0),(22,0),(23,0),(61,1),(68,2000)
]
# The value of '0' in speedtable will be use as gcode actuation speed value. 
# (Will not appear at speedtable in control pennel.)
speedtable_default=[
(0,1,16,500,500),(1,2,20,500,2000),
(2,2,24,500,3000),(3,2,28,500,4000),
(4,2,32,500,5000),(5,2,36,500,6000),
(6,2,40,500,7000),(7,2,44,500,8000),
(8,2,48,500,9000),(9,2,52,500,10000)
]

class CRUX:
    def __init__(self, logger, ports, connections, debugmode=False):
        self.logger = logger
        self.debugmode = debugmode
        self.connections = connections
        self.ports = ports
        self.debounces = {}
        self.conn = sqlite3.connect('CRUX.db')
        self.cursor = self.conn.cursor()
        self.error_codes = all_error_code
        self.pos = shared_data.pos
        self.stop_lock = threading.Lock()
        self.emg_event = threading.Event()
        self.stop_flag = False
        self.commands = []
        self.line = []
        self.for_return = 0

    def __str__(self):
        return f"CRUX(ports={self.ports}, connections={self.connections})"

# update data in database ##############################################################################################################################################################
    def change_speedtable(self, table_No, pattern, time, startspeed, topspeed):
        table_No=int(input("변경할 speedtabel의 번호를 입력하세요(0~9): "))
        if table_No > 9:
            print("입력하신 값은 0~9 사이의 값이 아닙니다.")
        else:
            print("입력하신 번호인 {}번 speed table에 입력값을 저장합니다.".format(table_No))
            self.cursor.execute('''UPDATE speedtable SET pattern = ?, time = ?, startspeed = ?, topspeed = ? WHERE table_No = ?''', (pattern, time, startspeed, topspeed, table_No))
            self.conn.commit()
            input_value=(table_No, pattern, time, startspeed, topspeed)
            return input_value
        
    def change_sys_setting(self,sys_No, value): 
        if sys_No>68 or sys_No==0:
            print("입력하신 값은 1~68 사이의 값이 아닙니다.")
        elif sys_No in (1,2,6,7,8,21,22,23,61,66,67,68):
            self.cursor.execute('''UPDATE sys_setting SET value = ? WHERE sys_No= ?''',(value, sys_No))
            self.conn.commit()
            sys_setting=(sys_No, value) 
            return sys_setting
        else:
            print("존재하지 않는 시스템 번호입니다.")

    def change_parameter(self,parameter_name,value):
        self.cursor.execute('''UPDATE parameter SET value = ? WHERE parameter_name= ?''',(value,parameter_name))
        self.conn.commit()
        parameter=(parameter_name,value)
        return parameter

# select data in database ##############################################################################################################################################################
    def select_speedtable(self, table_No): 
        self.cursor.execute('SELECT * FROM speedtable LIMIT 1 OFFSET ?',(table_No,))
        parameter=self.cursor.fetchone()
        return parameter
    
    def select_sys_setting(self):
        id=int(input("읽을 System setting 번호를 입력하세요: "))
        self.cursor.execute('SELECT * FROM sys_setting WHERE id=? LIMIT 1',(id,))
        sys_setting=self.cursor.fetchone()
        return sys_setting

    def select_parameter(self,parameter_name):
        self.cursor.execute('SELECT * FROM parameter WHERE parameter_name= ? LIMIT 1',(parameter_name,))
        parameter_value=self.cursor.fetchone()
        return parameter_value

# search data in database ######################################################################################################
    def search_speedtable_data(self):
        self.cursor.execute("SELECT * FROM speedtable")
        rows = self.cursor.fetchall()
        cols = [column[0] for column in self.cursor.description]
        df_speedtable = pd.DataFrame.from_records(data=rows, columns=cols)
        print(df_speedtable)
    
    def search_parameter_data(self):
        self.cursor.execute("SELECT * FROM parameter")
        rows = self.cursor.fetchall()
        cols = [column[0] for column in self.cursor.description]
        df_parameter = pd.DataFrame.from_records(data=rows, columns=cols)
        print(df_parameter)

    def search_sys_setting_data(self):
        self.cursor.execute("SELECT * FROM sys_setting")
        rows = self.cursor.fetchall()
        cols = [column[0] for column in self.cursor.description]
        df_sys_setting = pd.DataFrame.from_records(data=rows, columns=cols)
        print(df_sys_setting)

# command communication ##############################################################################################################################################################
    def select_port(self, port):
        if target_port_name in shared_data.ports:
            idx = shared_data.ports.index(target_port_name)

            return shared_data.connections[idx]

        return ValueError(f"Port '{target_port_name}' not found in shared_data.ports: {shared_data.ports}")
    
    def commun(self, code, connection, port):
        try:
            if self.emg_event.is_set():
                return
            
            utils.port_locker([port])
            lock = shared_data.port_lock[port]

            with lock:
                if self.debugmode: self.logger.log(f"Sending command: {code}")
                response = ""

                if code is not None:
                    print(code)
                    encode = b'\x02' + code.encode('ascii') + b'\r\n'
                    connection.write(encode)

                    if code.startswith('STP'):
                        with self.stop_lock:
                            self.stop_flag = True

                        encoded_response = connection.read_until(b'\n')
                        response = encoded_response.decode('ascii')

                        with self.stop_lock:
                            self.stop_flag = False

                        return
                    
                    while True:
                        if self.stop_flag:
                            if self.debugmode: 
                                self.logger.log("Stop flag is set. Exiting command.")

                            break

                        encoded_response = connection.read_until(b'\n')
                        response = encoded_response.decode('ascii')
                        
                        self.logger.log(f"[Worker] Commanding Done...")
                        
                        if self.debugmode: 
                            self.logger.log(f"Data received: {response}- {port}")

                        break

                    if code.startswith(('APS', 'RPS')):
                        axis_no = int(code.split('/')[0][-1])
                        self.check_end(connection, axis_no)

                    elif code.startswith('MPS'):
                        axis1 = int(code.split('/')[0][-1])
                        axis2 = int(code.split('/')[2][-1])

                        self.check_end(connection, axis1)
                        self.check_end(connection, axis2)

                    if response and (response.startswith('C') or response.startswith('E')):
                        id_code = response.split('\t')[0]
                        command_code = response[2:5]

                        if id_code == ('C'):
                            if command_code == 'IDN':
                                model_name = response.split('\t')[2]
                                Version = int(response.split('\t')[3].rstrip('\r\n')) / 1000
                                self.logger.log('%s Ver.%s' %(model_name, Version))
                            elif command_code == 'RDP':
                                value = response.split('\t')[2].rstrip('\r\n')
                                self.for_return = value
                                axis_No = response[5]
                                self.logger.log("Current position of Axis No.%s is : %s"%(axis_No, value))
                                self.logger.log(shared_data.pos)
                            elif command_code == 'RSY':
                                Sys_No = response.split('\t')[2]
                                value = response.split('\t')[3].rstrip('\r\n')
                                self.logger.log("Setup value of system No.%s is : %s"%(Sys_No, value))
                            elif command_code == 'RTB':
                                a = response[5]
                                b = response.split('\t')[2]
                                c = response.split('\t')[3]
                                d = response.split('\t')[4]
                                e = response.split('\t')[5]
                                f = response.split('\t')[6].rstrip('\r\n')
                                self.for_return = (a, b, c, d, e, f)
                                self.logger.log("Axis No.%s : speedtable No=%s, Initial Velocity=%s, Maximum Velocity=%s, Acceleration Time=%s, Acceleration Mode=%s(1:Rectangular drive, 2:Trapezoidal drive)"%(a, b, c, d, e, f))
                            elif command_code == 'STR':
                                a = response[5]
                                if a != 0:
                                    b = response.split('\t')[2]
                                    c = response.split('\t')[3]
                                    d = response.split('\t')[4]
                                    e = response.split('\t')[5]
                                    f = response.split('\t')[6].rstrip('\r\n')
                                    self.logger.log("Axis No.%s : driving state=%s, ORG sig.=%s, NORG sig.=%s, CCW limit sig.=%s, CW limit sig.=%s(0:OFF(STOP), 1:ON(Operating))"%(a, b, c, d, e, f))
                                else:
                                    self.logger.log('EMG sig.=%s(0:OFF, 1:ON)' %a)
                            elif command_code == 'WSY':
                                a = response[5]
                                b = response.split('\t')[2]
                                c = response.split('\t')[3]
                                self.logger.log('Axis No.%s : Setup value of system No.%s is : %s' %(a, b, c))
                            else:
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                if self.debugmode: self.logger.log(f"Data received at {current_time}:{response}")
                        elif id_code == ('E'):
                            self.logger.error(response)
                            if command_code == ('SYS'):
                                error_code = response[5:].rstrip('\r\n')
                                self.lookup_error(error_code)
                            else:
                                error_code = response.split('\t')[2].rstrip('\r\n')
                                self.lookup_error(error_code)
    
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(traceback.format_exc())

    def check_end(self, connection, axis_no):
        while True:
            code = 'STR%d' %(axis_no)
            encode = b'\x02' + code.encode('ascii') + b'\r\n'
            connection.write(encode)

            encoded_response = connection.read_until(b'\n')
            response = encoded_response.decode('ascii')

            if response.split('\t')[1][0:3] == 'STR':
                if int(response.split('\t')[2]) == 0:
                    break

            time.sleep(0.01)

    # look up error message
    def get_error_message(self, error_code):
        return self.error_codes.get(error_code, 'Unknown Error')
    
    def lookup_error(self, error_code):
        error_message=self.get_error_message(error_code)
        length = len(error_code)

        if length == 1:
            self.logger.error('This error is a kind of system error')
            self.logger.error(error_message)
        elif length != 1 and error_code.startswith('1'):
            self.logger.error('This error is a kind of parameter error')
            self.logger.error(error_message)
        elif error_code.startswith('3'):
            self.logger.error('This error is a kind of drive system error')
            if error_code in ('304', '305', '306'):
                self.logger.error(error_message[0])
            else:
                self.logger.error(error_message)
        elif length!=1 and error_code.startswith('5'):
            self.logger.error('This error is a kind of MPS command error')
            self.logger.error(error_message)
        elif error_code.startswith('6'):
            self.logger.error('This error is a kind of WTB command calculation error')
            self.logger.error(error_message)
        elif error_code.startswith('7'):
            self.logger.error('This error is a kind of system setting errors(WSY command errors)')
            self.logger.error(error_message)
        else:
            self.logger.error('This is error is other error')
            self.logger.error(error_message)
    
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
            print(shared_data.ports)
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

    ## manual command code ##############################################################################################################################################################
    def APS_manual(self,axis,speedtable,port):
        connection=self.select_port(port)
        command='APS'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=speedtable
        parameter_index='pos_abs%d' %a
        c=self.select_parameter([parameter_index])[1]
        d=self.select_parameter('response_method')[1]
        code1='APS%d/%d/%d/%d' %(a,b,c,d)
        self.commun(code1,connection,port)
        time.sleep(wait_secs)
        code2='RDP%d' %a
        self.commun(code2,connection,port)
        time.sleep(wait_secs)
    
    def COF_manual(self,axis,port):
        connection=self.select_port(port)
        command='COF'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=int(input('Choose ON/OFF for excitation(0=OFF/1=ON): '))
        code='COF%d/%d' %(a,b)
        self.commun(code,connection,port)
        time.sleep(wait_secs)

    def FRP_manual(self, axis, speedtable,port):
        connection=self.select_port(port)
        command='FRP'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=speedtable
        c=int(input('Choose Rotating direction(0=CW/1=CCW): '))
        code='FRP%d/%d/%d' %(a,b,c)
        self.commun(code,connection,port)
        time.sleep(wait_secs)

    def IDN_manual(self,port):
        connection=self.select_port(port)
        command='IDN'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        code='IDN'
        self.commun(code,connection,port)
        time.sleep(wait_secs)
    
    def MPI_manual(self,axis,speedtable,port):
        connection=self.select_port(port)
        command='MPI'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=self.select_parameter('drive_type')[1]
        c=speedtable
        code1='MPI%d/%d/%d' %(a,b,c)
        self.commun(code1,connection,port)
        time.sleep(wait_secs)
        code2='RDP%d' %a
        self.commun(code2,connection,port)
        time.sleep(wait_secs)
    
    def MPS_manual(self,axis1, axis2,port):
        connection=self.select_port(port)
        x=self.select_parameter('drive_type')[1]
        command='MPS'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        if x==0:# 절대이동
            a=axis1
            parameter_index1='pos_abs%d' %a
            b=self.select_parameter(parameter_index1)[1]
            c=axis2
            parameter_index2='pos_abs%d' %c
            d=self.select_parameter(parameter_index2)[1]
            e=self.select_parameter('response_method')[1]
            code1='MPS%d/%d/%d/%d/%d' %(a,b,c,d,e)
            self.commun(code1,connection,port)
            time.sleep(wait_secs)
            code2='RDP%d' %a
            self.commun(code2,connection,port)
            code3='RDP%d' %c
            self.commun(code3,connection,port)
            time.sleep(wait_secs)
        else: # 상대이동
            a=axis1
            parameter_index1='pos_rel%d' %a
            b=self.select_parameter(parameter_index1)[1]
            c=axis2
            parameter_index2='pos_rel%d' %c
            d=self.select_parameter(parameter_index2)[1]
            e=self.select_parameter('response_method')[1]
            code1='MPS%d/%d/%d/%d/%d' %(a,b,c,d,e)
            self.commun(code1,connection,port)
            time.sleep(wait_secs)
            code2='RDP%d' %a
            self.commun(code2,connection,port)
            code3='RDP%d' %c
            self.commun(code3,connection,port)
            time.sleep(wait_secs)
            
    def ORG_manual(self, axis, speedtable,port):
        connection=self.select_port(port)
        command='ORG'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=speedtable
        c=self.select_parameter('response_method')[1]
        code1='ORG%d/%d/%d' %(a,b,c)
        self.commun(code1,connection,port)
        time.sleep(wait_secs)
        code2='RDP%d' %a
        self.commun(code2,connection,port)
        time.sleep(wait_secs)

    def RDP_manual(self, axis,port):
        connection=self.select_port(port)
        command='RDP'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        code='RDP%d' %a
        self.commun(code,connection,port)
        time.sleep(wait_secs)
    
    def RPS_manual(self,axis,speedtable,port):
        connection=self.select_port(port)
        command='RPS'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        parameter_index='pos_rel%d' %a
        b=speedtable
        c=self.select_parameter(parameter_index)[1]
        d=self.select_parameter('response_method')[1]
        code1='RPS%d/%d/%d/%d' %(a,b,c,d)
        self.commun(code1,connection,port)
        time.sleep(wait_secs)
        code2='RDP%d' %a
        self.commun(code2,connection,port)
        time.sleep(wait_secs)
    
    def RST_manual(self,port):
        connection=self.select_port(port)
        command='RST'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        code='RST'
        self.commun(code,connection,port)
        for table_No, pattern, acctime, startspeed, topspeed in speedtable_default:
            self.change_speedtable(table_No, pattern,acctime,startspeed,topspeed)
        for sys_No, value in sys_default:
            self.change_sys_setting(sys_No,value)
        self.change_parameter('pos_current1', 0)
        self.change_parameter('pos_current2', 0)
        time.sleep(wait_secs)

    def RSY_manual(self,axis,port):
        connection=self.select_port(port)
        command='RSY'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=int(input("읽을 system setting 번호를 입력하세요: "))
        code='RSY%d/%d' %(a,b)
        self.commun(code,connection,port)
        time.sleep(wait_secs)
    
    def RTB_manual(self,axis,port,table_No=None):
        connection=self.select_port(port)
        command='RTB'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        if table_No is None:
            b=int(input("읽을 speedtable 번호를 입력하세요: "))
        else:
            b=table_No
        code='RTB%d/%d' %(a,b)
        self.commun(code,connection,port)
        time.sleep(wait_secs)
        
    #  def SAV(self,port):
    #    connection=self.select_port(port)
    #    command='SAV'
    #    self.debounce(command, wait_secs=0.007)
    #    wait_secs=self.debounces[command]
    #    code='SAV'
    #    self.commun(code,connection)
    #    time.sleep(wait_secs)

    def STP_manual(self,axis,port):
        connection=self.select_port(port)
        command='STP'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        b=self.select_parameter('stop_mode')
        code='STP%d/%d' %(a,b)
        self.commun(code,connection,port)
        time.sleep(wait_secs)
    
    def STR_manual(self, axis,port):
        connection=self.select_port(port)
        command='STR'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        a=axis
        if a==0: #check EMG sig.
            code='STR0'
            self.commun(code,connection,port)
            time.sleep(wait_secs)
        else:
            code='STR%d' %a
            self.commun(code,connection,port)
            time.sleep(wait_secs)
        
    def WRP_manual(self,axis,port): ## write current pulse
        connection=self.select_port(port)
        command='WRP'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        parameter_name='pos_current%d' %a
        pos=self.change_parameter(parameter_name)
        a=axis
        b=pos[1] 
        code='WRP%d/%d' %(a,b)
        self.commun(code,connection,port)
        time.sleep(wait_secs)

    def WSY_manual(self,axis,port): ## write system setting
        connection=self.select_port(port)
        command='WSY'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        sys_setting=self.change_sys_setting()
        a=axis
        b=sys_setting[0]
        c=sys_setting[1]
        code='WSY%d/%d/%d' %(a,b,c)
        self.commun(code,connection,port)
        time.sleep(wait_secs)

    def WTB_manual(self,axis,port):
        connection=self.select_port(port)
        input_value=self.change_speedtable()
        a=axis
        b=input_value[0]
        c=input_value[3]
        d=input_value[4]
        e=input_value[2]
        f=input_value[1]
        command='WTB'
        self.debounce(command, wait_secs=0.007)
        wait_secs=self.debounces[command]
        code='WTB%d/%d/%d/%d/%d/%d' %(a,b,c,d,e,f)
        self.commun(code,connection,port)
        time.sleep(wait_secs)

# debounce 설정 ######################################################################################
    def debounce(self, command, wait_secs):
        self.debounces[command]=wait_secs

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