Remote Delivery Vehicle Project
Tổng quan
Dự án này là một hệ thống xe giao hàng điều khiển từ xa được xây dựng để điều khiển robot qua mạng TCP, tích hợp cảm biến GPS để lấy dữ liệu vị trí, tốc độ, và camera để stream video trực tiếp. Robot sử dụng Raspberry Pi làm bộ điều khiển chính, kết hợp với giao diện LabVIEW để điều khiển từ xa, bao gồm cả việc mở khay hàng thông qua động cơ servo.
Hệ thống này phù hợp cho các ứng dụng giao hàng tự động, giám sát từ xa hoặc các dự án nghiên cứu liên quan đến robot di động.

Cấu trúc dự án

Phần cứng:

Raspberry Pi (khuyến nghị sử dụng Raspberry Pi 4).
Module GPS (kết nối qua UART, ví dụ NEO-6M).
Camera USB hoặc Raspberry Pi Camera để stream video.
Động cơ DC (điều khiển thông qua L298N).
Động cơ servo (để mở khay hàng).
Nguồn cấp điện phù hợp (pin hoặc adapter).


Phần mềm:

Raspberry Pi: Chạy mã Python để điều khiển robot, thu thập dữ liệu GPS, và stream video.
LabVIEW: Giao diện điều khiển từ xa, hiển thị dữ liệu GPS và video stream.
Giao thức: TCP/IP để giao tiếp giữa LabVIEW và Raspberry Pi.




Yêu cầu cài đặt
Phía Raspberry Pi

Hệ điều hành: Raspbian OS (hoặc Raspberry Pi OS mới nhất).

Thư viện Python:
pip install RPi.GPIO pigpio pynmea2


Kích hoạt pigpio daemon:
sudo systemctl enable pigpiod
sudo systemctl start pigpiod


Cấu hình GPS:

Kết nối module GPS qua cổng UART (/dev/ttyAMA0).
Đảm bảo đã tắt console trên cổng serial bằng cách chỉnh sửa /boot/cmdline.txt và /boot/config.txt.


Cấu hình camera:

Sử dụng camera USB hoặc Raspberry Pi Camera.
Cài đặt thư viện stream video (ví dụ: mjpg-streamer hoặc sử dụng OpenCV).



Phía LabVIEW

Cài đặt LabVIEW (phiên bản 2018 trở lên được khuyến nghị).
Cài đặt NI-VISA để xử lý giao tiếp TCP.
Tải file LabVIEW từ thư mục labview/ trong repository này.


Hướng dẫn sử dụng
1. Cài đặt và chạy mã Python trên Raspberry Pi

Sao chép file remote_delivery_vehicle.py từ repository vào Raspberry Pi.

Kết nối phần cứng theo cấu hình chân GPIO được định nghĩa trong mã:

ENA, ENB, IN1, IN2, IN3, IN4: Điều khiển động cơ DC qua L298N.
SERVO_PIN: Động cơ servo để mở khay hàng.


Chạy mã Python:
python3 remote_delivery_vehicle.py


Mã sẽ in ra địa chỉ IP của Raspberry Pi và cổng (mặc định là 65432). Ghi lại thông tin này để sử dụng trong LabVIEW.


2. Cấu hình stream camera

Nếu sử dụng mjpg-streamer:
sudo apt-get install mjpg-streamer
mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080"


Truy cập stream video qua trình duyệt tại: http://<IP_Raspberry_Pi>:8080/?action=stream.


3. Chạy giao diện LabVIEW

Mở file LabVIEW (remote_delivery_vehicle.vi) trong thư mục labview/.
Nhập địa chỉ IP và cổng của Raspberry Pi (lấy từ bước chạy mã Python).
Sử dụng giao diện để:
Điều khiển xe: Tiến, lùi, rẽ trái, rẽ phải, dừng.
Điều khiển khay hàng: Mở/đóng khay bằng cách gửi góc servo (0-180 độ).
Hiển thị GPS: Xem vĩ độ, kinh độ và tốc độ từ module GPS.
Xem video stream: Nhập URL stream (ví dụ: http://<IP>:8080/?action=stream) vào trình duyệt hoặc tích hợp trong LabVIEW.




Mã nguồn
Python (Raspberry Pi)
Mã Python điều khiển robot, thu thập dữ liệu GPS và giao tiếp với LabVIEW qua TCP.
<xaiArtifact artifact_id="7298324d-2f48-4567-ab01-88fb5cfae816" artifact_version_id="6ec0bb76-7f2a-47d6-85fa-c0b99cbebb5e" title="remote_delivery_vehicle.py" contentType="text/python">
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import socket
import time
import serial
import pynmea2
import threading
import sys
import pigpio

# --- CẤU HÌNH CHÂN GPIO (theo chuẩn BCM) ---
ENA = 12
IN1 = 23
IN2 = 24
ENB = 13
IN3 = 27
IN4 = 22
SERVO_PIN = 18

# --- CẤU HÌNH MẠNG TCP ---
HOST = ''
PORT = 65432

# --- CẤU HÌNH GPS ---
SERIAL_PORT = "/dev/ttyAMA0"
BAUDRATE = 9600

# Biến toàn cục để lưu tọa độ, tốc độ và trạng thái GPS hiện tại
current_latitude = 0.0
current_longitude = 0.0
current_speed_kmh = 0.0
is_gps_valid = False
gps_lock = threading.Lock()

# --- KHỞI TẠO GPIO và PIGPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
pins = [ENA, IN1, IN2, ENB, IN3, IN4]
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)

GPIO.output(IN1, GPIO.LOW)
GPIO.output(IN2, GPIO.LOW)
GPIO.output(IN3, GPIO.LOW)
GPIO.output(IN4, GPIO.LOW)
GPIO.output(ENA, GPIO.LOW)
GPIO.output(ENB, GPIO.LOW)

pwm_a = GPIO.PWM(ENA, 1000)
pwm_b = GPIO.PWM(ENB, 1000)
pwm_a.start(0)
pwm_b.start(0)

# Khởi tạo pigpio
try:
    pi = pigpio.pi()
    if not pi.connected:
        print("Lỗi: Không thể kết nối với daemon pigpio.")
        sys.exit()
except Exception as e:
    print(f"Lỗi khởi tạo pigpio: {e}")
    sys.exit()

# --- CÁC HÀM ĐIỀU KHIỂN ĐỘNG CƠ DC ---
def convert_speed(speed_val):
    """Chuyển đổi tốc độ từ 0-255 (từ LabVIEW) sang 0-100 (duty cycle của PWM)."""
    speed_val = max(0, min(255, speed_val))
    return (speed_val / 255.0) * 100.0

def forward(speed):
    duty_cycle = convert_speed(speed)
    print(f"Lệnh: Tiến, Tốc độ: {speed} -> Duty Cycle: {duty_cycle:.2f}%")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(duty_cycle)
    pwm_b.ChangeDutyCycle(duty_cycle)

def backward(speed):
    duty_cycle = convert_speed(speed)
    print(f"Lệnh: Lùi, Tốc độ: {speed} -> Duty Cycle: {duty_cycle:.2f}%")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_a.ChangeDutyCycle(duty_cycle)
    pwm_b.ChangeDutyCycle(duty_cycle)

def turn_left(speed):
    duty_cycle = convert_speed(speed)
    print(f"Lệnh: Rẽ trái, Tốc độ: {speed} -> Duty Cycle: {duty_cycle:.2f}%")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_a.ChangeDutyCycle(duty_cycle)
    pwm_b.ChangeDutyCycle(duty_cycle)

def turn_right(speed):
    duty_cycle = convert_speed(speed)
    print(f"Lệnh: Rẽ phải, Tốc độ: {speed} -> Duty Cycle: {duty_cycle:.2f}%")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(duty_cycle)
    pwm_b.ChangeDutyCycle(duty_cycle)

def stop():
    print("Lệnh: Dừng")
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

def test_motors():
    print("Bắt đầu kiểm tra động cơ...")
    forward(150)
    time.sleep(2)
    stop()
    time.sleep(1)
    backward(150)
    time.sleep(2)
    stop()
    time.sleep(1)
    turn_left(150)
    time.sleep(2)
    stop()
    time.sleep(1)
    turn_right(150)
    time.sleep(2)
    stop()
    print("Kiểm tra hoàn tất.")

# --- HÀM ĐIỀU KHIỂN ĐỘNG CƠ SERVO ---
def set_servo_angle(angle):
    """
    Đặt vị trí của servo dựa trên góc (0-180 độ).
    Sử dụng thư viện pigpio để tạo tín hiệu PWM.
    Độ rộng xung (pulse width) cho servo thường là:
    - 500 us cho 0 độ
    - 1500 us cho 90 độ
    - 2500 us cho 180 độ
    """
    if not 0 <= angle <= 180:
        print(f"Lỗi: Góc servo {angle} không hợp lệ. Chỉ chấp nhận từ 0 đến 180.")
        return
    pulse_width = int(500 + (angle / 180.0) * 2000)
    print(f"Lệnh: Servo đến góc {angle} độ -> Độ rộng xung: {pulse_width} µs")
    pi.set_servo_pulsewidth(SERVO_PIN, pulse_width)

# --- HÀM LẤY IP ---
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Không thể lấy địa chỉ IP: {e}")
        return "127.0.0.1"

# --- HÀM ĐỌC DỮ LIỆU GPS (CHẠY TRÊN LUỒNG RIÊNG) ---
def read_gps_data(stop_event):
    """
    Hàm này chạy liên tục trong một luồng riêng để đọc dữ liệu từ module GPS.
    """
    global current_latitude, current_longitude, current_speed_kmh, is_gps_valid
    last_status = None
    try:
        ser = serial.Serial(SERIAL_PORT, baudrate=BAUDRATE, timeout=1)
        print("Đang chờ tín hiệu GPS...")
    except serial.SerialException as e:
        print(f"Lỗi: Không thể mở cổng nối tiếp {SERIAL_PORT}. Vui lòng kiểm tra lại kết nối và thiết lập.", file=sys.stderr)
        stop_event.set()
        return
    while not stop_event.is_set():
        try:
            line = ser.readline().decode('utf-8', errors='ignore')
            if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                msg = pynmea2.parse(line)
                with gps_lock:
                    if msg.is_valid:
                        current_latitude = msg.latitude
                        current_longitude = msg.longitude
                        speed_knots = msg.spd_over_grnd
                        current_speed_kmh = speed_knots * 1.852 if speed_knots is not None else 0
                        is_gps_valid = True
                        if last_status != 'A':
                            print("Đã có tín hiệu GPS hợp lệ.")
                            last_status = 'A'
                    else:
                        is_gps_valid = False
                        if last_status != 'V':
                            print("GPS chưa có tín hiệu hợp lệ. Đang chờ...")
                            last_status = 'V'
        except pynmea2.ParseError:
            pass
        except serial.SerialException as e:
            print(f"Lỗi Serial: {e}")
            break
        except Exception as e:
            print(f"Lỗi không xác định trong luồng GPS: {e}")
            break
        time.sleep(0.5)
    ser.close()
    print("Đã đóng cổng serial GPS và dừng luồng.")

# --- HÀM CHÍNH VÀ VÒNG LẶP SERVER ---
def main():
    stop_gps_thread = threading.Event()
    gps_thread = threading.Thread(target=read_gps_data, args=(stop_gps_thread,))
    gps_thread.daemon = True
    gps_thread.start()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_ip = get_ip_address()
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("="*40)
    print("SERVER ROBOT - TÍCH HỢP GPS & SERVO")
    print(f"  >> Kết nối LabVIEW tới IP: {my_ip}")
    print(f"  >>                Port: {PORT}")
    print("="*40)
    print("Đang chờ kết nối từ LabVIEW...")
    try:
        while True:
            server_socket.settimeout(1)
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue
            print(f"Đã kết nối bởi {addr}")
            with conn:
                try:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            print(f"Client {addr} đã ngắt kết nối.")
                            break
                        command_str = data.decode('utf-8').strip()
                        print(f"Nhận được: '{command_str}'")
                        try:
                            parts = command_str.split(':')
                            cmd = parts[0].upper()
                            if cmd in ['F', 'B', 'L', 'R']:
                                speed = 0
                                if len(parts) > 1:
                                    speed_str_from_labview = parts[1].replace(',', '.')
                                    speed = int(float(speed_str_from_labview))
                                if cmd == 'F': forward(speed)
                                elif cmd == 'B': backward(speed)
                                elif cmd == 'L': turn_left(speed)
                                elif cmd == 'R': turn_right(speed)
                            elif cmd == 'S':
                                stop()
                            elif cmd == 'SERVO':
                                angle = 0
                                if len(parts) > 1:
                                    angle_str = parts[1].replace(',', '.')
                                    angle = int(float(angle_str))
                                set_servo_angle(angle)
                            elif cmd == 'TEST':
                                test_motors()
                                print("Kiểm tra Servo...")
                                set_servo_angle(0)
                                time.sleep(1)
                                set_servo_angle(90)
                                time.sleep(1)
                                set_servo_angle(180)
                                time.sleep(1)
                                set_servo_angle(90)
                                print("Kiểm tra Servo hoàn tất.")
                            else:
                                print(f"Lệnh không hợp lệ: {cmd}")
                        except (IndexError, ValueError) as e:
                            print(f"Lỗi phân tích lệnh '{command_str}': {e}")
                        with gps_lock:
                            if is_gps_valid:
                                lat = current_latitude
                                lon = current_longitude
                                speed = current_speed_kmh
                                response_str = f"GPS:{lat:.6f},{lon:.6f},{speed:.2f}\n"
                            else:
                                response_str = "GPS:0,0,0\n"
                        try:
                            conn.sendall(response_str.encode('utf-8'))
                        except ConnectionResetError:
                            print(f"Lỗi: Không thể gửi dữ liệu. Client đã đóng kết nối.")
                            break
                except ConnectionResetError:
                    print(f"Client {addr} đã đóng kết nối đột ngột.")
    except KeyboardInterrupt:
        print("\nĐang tắt chương trình...")
    finally:
        print("Dọn dẹp GPIO và đóng server.")
        stop_gps_thread.set()
        gps_thread.join(timeout=2)
        stop()
        pwm_a.stop()
        pwm_b.stop()
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        GPIO.cleanup()
        server_socket.close()

if __name__ == '__main__':
    main()
