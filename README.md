# Remote Delivery Vehicle

Dự án xe giao hàng điều khiển từ xa sử dụng Raspberry Pi, tích hợp GPS để lấy vị trí và tốc độ, camera để truyền video trực tiếp, và động cơ servo để mở khay hàng. Hệ thống giao tiếp với giao diện LabVIEW qua mạng TCP để điều khiển từ xa.

## Tính năng

- **Điều khiển từ xa**: Di chuyển xe (tiến, lùi, rẽ trái, rẽ phải, dừng) qua giao diện LabVIEW.
- **Theo dõi GPS**: Hiển thị vĩ độ, kinh độ, và tốc độ thời gian thực.
- **Điều khiển khay hàng**: Mở/đóng khay hàng bằng động cơ servo.
- **Truyền video trực tiếp**: Xem video từ camera USB hoặc Raspberry Pi.
- **Chế độ kiểm tra**: Tự động kiểm tra động cơ và servo.

## Yêu cầu phần cứng

- Raspberry Pi (khuyến nghị Raspberry Pi 4).
- Module GPS (ví dụ: NEO-M8N, kết nối qua UART).
- Camera USB hoặc Raspberry Pi Camera.
- Động cơ DC với driver L298N.
- Động cơ servo để mở khay hàng.
- Nguồn điện (pin hoặc adapter).

## Yêu cầu phần mềm

- **Raspberry Pi**:
  - Hệ điều hành Raspberry Pi OS (phiên bản mới nhất).
  - Cài đặt thư viện Python:

    ```bash
    pip install RPi.GPIO pigpio pynmea2
    ```
  - Kích hoạt daemon `pigpiod`:

    ```bash
    sudo systemctl enable pigpiod
    sudo systemctl start pigpiod
    ```
  - Truyền video (ví dụ: sử dụng `mjpg-streamer`):

    ```bash
    sudo apt-get install mjpg-streamer
    ```
- **LabVIEW**:
  - LabVIEW 2018 trở lên.
  - NI-VISA để giao tiếp TCP.

## Cài đặt

1. **Cấu hình phần cứng**:

   - Kết nối động cơ DC với driver L298N, sử dụng chân GPIO (BCM): ENA=12, IN1=23, IN2=24, ENB=13, IN3=27, IN4=22.
   - Kết nối động cơ servo vào chân GPIO 18.
   - Kết nối module GPS qua cổng UART (`/dev/ttyAMA0`).
   - Kết nối camera (USB hoặc Raspberry Pi Camera).
   - Tắt console serial trong `/boot/cmdline.txt` và bật UART trong `/boot/config.txt`.

2. **Cấu hình phần mềm**:

   - Tải repository:

     ```bash
     https://github.com/thanhdzvipprono1tg/labview-TLCBDT.git
     ```

     Sao chép file `lastversion.py` vào Raspberry Pi.
   - Chạy mã Python:

     ```bash
     python3 lastversion.py
     ```
   - Ghi lại địa chỉ IP và cổng (mặc định: 65432) hiển thị trên terminal.

3. **Truyền video**:

   - Khởi động `mjpg-streamer`:

     ```bash
     mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080"
     ```
   - Truy cập video tại: `http://<IP_Raspberry_Pi>:8080/?action=stream`.

4. **Giao diện LabVIEW**:

   - Mở file `colab.vi` (trong thư mục `labview/`) bằng LabVIEW.
   - Nhập IP và cổng của Raspberry Pi.
   - Sử dụng giao diện để điều khiển xe, thay đổi góc servo, xem dữ liệu GPS, và hiển thị video.

## Hướng dẫn sử dụng

- **Lệnh điều khiển** (gửi từ LabVIEW):
  - Tiến: `F:<tốc_độ>` (tốc độ: 0-255)
  - Lùi: `B:<tốc_độ>`
  - Rẽ trái: `L:<tốc_độ>`
  - Rẽ phải: `R:<tốc_độ>`
  - Dừng: `S`
  - Servo: `SERVO:<góc>` (góc: 0-180)
  - Kiểm tra: `TEST`
- **Dữ liệu GPS** (nhận từ Raspberry Pi):
  - Định dạng: `GPS:<vĩ_độ>,<kinh_độ>,<tốc_độ_km/h>\n`
  - GPS không hợp lệ: `GPS:0,0,0\n`
- **Video trực tiếp**:
  - Xem trong LabVIEW qua WebBrowser control hoặc trình duyệt tại URL stream.

## Giao diện LabVIEW

File `colab.vi` cung cấp:

- Nút điều khiển xe (tiến, lùi, rẽ trái, rẽ phải, dừng).
- Thanh trượt/ô nhập để điều chỉnh tốc độ (0-255) và góc servo (0-180).
- Hiển thị vĩ độ, kinh độ, tốc độ từ dữ liệu GPS.
- WebBrowser control để xem video stream.

**Lưu ý**: File `.vi` không được cung cấp do định dạng nhị phân của LabVIEW. Bạn có thể tạo giao diện dựa trên:

- Sử dụng `TCP Open Connection` để kết nối với Raspberry Pi.
- Phân tích chuỗi GPS (`GPS:<vĩ_độ>,<kinh_độ>,<tốc_độ>`).
- Tích hợp WebBrowser control để hiển thị video stream.

## Lưu ý

- Đảm bảo Raspberry Pi và máy chạy LabVIEW cùng mạng LAN.
- Kiểm tra kết nối GPS và camera trước khi chạy.
- Điều chỉnh chân GPIO hoặc thông số PWM nếu dùng phần cứng khác.
- Nếu gặp lỗi serial/GPS, kiểm tra cấu hình UART.

## Đóng góp

Mọi ý tưởng cải tiến đều được hoan nghênh! Vui lòng gửi pull request hoặc báo lỗi qua GitHub Issues.
# ---End---
