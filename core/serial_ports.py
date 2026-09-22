import serial
import serial.tools.list_ports

class SerialPorts:
    def __init__(self):
        self.ports = self.detect_serial_ports()

    def detect_serial_ports(self):
        """시스템에서 사용 가능한 시리얼 포트를 탐지하고 정보를 리스트로 반환"""
        ports = serial.tools.list_ports.comports()
        port_list = []
        for port in ports:
            port_info = {"device": port.device, "name": port.name, 
            "description": port.description, "hwid": port.hwid}
             
            port_list.append(port_info)
            
        return port_list
    
    def get_ports_info(self):

        return self.ports

if __name__ == "__main__":
    sp = SerialPorts()
    ports_info = sp.get_ports_info()
    
    for info in ports_info:
        print(info)