import serial
from multiprocessing import Process
import time

# 포트 설정
PORTS = {
    "port1": {"port": "COM4", "baudrate": 115200},
    "port2": {"port": "COM5", "baudrate": 115200},
}

# 포트 연결 및 제어 함수
def control_motor(port_settings, commands):
    try:
        conn = serial.Serial(
            port=port_settings["port"],
            baudrate=port_settings["baudrate"],
            timeout=None
        )
        for command in commands:
            conn.write(command.encode('ascii'))
            current_time = time.time()
            print(f"{port_settings['port']}로 명령 전송: {command}-{current_time}")
            #time.sleep(0.01)  # 최소한의 간격
            encoded_response = conn.read_until(b'\n')
            response = encoded_response.decode('ascii')
            print(f"{port_settings['port']}로부터 응답: {response}")
        conn.close()
        print(f"{port_settings['port']} 연결 종료")
    except Exception as e:
        print(f"{port_settings['port']}에서 오류 발생: {e}")

# 메인 프로세스
if __name__ == "__main__":
    # 각 포트에 보낼 명령
    commands_port1 = ["WTB1/1/500/500/1/1", "WTB2/2/500/500/1/1"]  # 1번 포트에 보낼 신호
    commands_port2 = ["WTB2/3/500/500/1/1"]          # 2번 포트에 보낼 신호

    # 멀티프로세스 생성
    process1 = Process(target=control_motor, args=(PORTS["port1"], commands_port1))
    process2 = Process(target=control_motor, args=(PORTS["port2"], commands_port2))

    # 프로세스 시작
    process1.start()
    process2.start()

    # 프로세스 종료 대기
    process1.join()
    process2.join()
