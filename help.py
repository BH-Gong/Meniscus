import serial
import threading
import time
from core import shared_data

def commun(code, connection):
    encode = b'\x02' + code.encode('ascii') + b'\r\n'
    print(code)
    connection.write(encode)
    print(connection)
    s_time = time.time()

    while True:
        encoded_response = connection.read_until(b'\n')
        response = encoded_response.decode('ascii')
        break

    duration = time.time() - s_time
    print('response: %s, duration: %f' %(response, duration)) 

def send_signals(codes, ports):
    try:
        threads = []

        for code, port in zip(codes, ports):
            if code is not None:
                connection = select_port(port)
                t = threading.Thread(target=commun, args=(code, connection))
                t.start()
                threads.append(t)
            else:
                pass

        for t in threads:
            t.join()

    except Exception as e:
        print(e)

def select_port(port):
    if port == 'COM6':
        temp_ser = serial.Serial('COM6', 115200, 8, serial.PARITY_NONE,
                                serial.STOPBITS_ONE, timeout=None)
    elif port == 'COM7':
        temp_ser = serial.Serial('COM7', 115200, 8, serial.PARITY_NONE,
                                serial.STOPBITS_ONE, timeout=None)
        
    return temp_ser

command0 = 'MPI1/1/0'
commands0 = [command0, command0]
command1 = 'MPI2/1/0'
commands1 = [command1, command1]
command2 = 'MPS1/0/2/0/0'
commands2 = [command2, command2]
command3 = 'STR2'
commands3 = [command3, command3]
ports = ['COM6', "COM7"]

send_signals(commands0, ports)
send_signals(commands1, ports)
send_signals(commands2, ports)
send_signals(commands3, ports)