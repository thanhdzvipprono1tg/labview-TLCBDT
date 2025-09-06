# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import socket
import time
import serial
import pynmea2
import threading
import sys
import pigpio # Thêm thư viện pigpio

# --- CẤU HÌNH CHÂN GPIO (theo chuẩn BCM) ---
ENA = 12
IN1 = 23
IN2 = 24
ENB = 13
IN3 = 27
IN4 = 22
SERVO_PIN = 18 # Chân điều khiển động cơ servo

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
    
    # Chuyển đổi góc thành độ rộng xung (pulse width)
    # Công thức: pulse_width = 500 + (angle / 180.0) * 2000
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
                        #print(f"Tọa độ: Vĩ độ {current_latitude:.6f}, Kinh độ {current_longitude:.6f}")
                        #print(f"Tốc độ: {current_speed_kmh:.2f} km/h")
                        #print("-" * 30)

                    else:
                        is_gps_valid = False
                        if last_status != 'V':
                            print("GPS chưa có tín hiệu hợp lệ. Đang chờ...")
                            last_status = 'V'
                        
        except pynmea2.ParseError as e:
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
    # Khởi tạo và bắt đầu luồng đọc GPS
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
    print(f"  >> Kết nối LabVIEW tới IP: {my_ip}")
    print(f"  >>                Port: {PORT}")
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
                        
                        # --- Xử lý lệnh điều khiển ---
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
                                set_servo_angle(90) # Đặt lại về giữa
                                print("Kiểm tra Servo hoàn tất.")
                            else: 
                                print(f"Lệnh không hợp lệ: {cmd}")
                        except (IndexError, ValueError) as e:
                            print(f"Lỗi phân tích lệnh '{command_str}': {e}")
                        
                        # --- Gửi dữ liệu GPS về LabVIEW ---
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
                            #print(f"Đã gửi về LabVIEW: {response_str.strip()}")
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
        pi.set_servo_pulsewidth(SERVO_PIN, 0) # Tắt tín hiệu servo
        pi.stop() # Dừng daemon pigpio
        GPIO.cleanup()
        server_socket.close()

if __name__ == '__main__':
    main()