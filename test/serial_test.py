from serial.tools import list_ports

ports = list_ports.comports()

print((ports[0].device, ports[0].description))

print(ports)