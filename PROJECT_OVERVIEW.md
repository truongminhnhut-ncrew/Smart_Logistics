# Tổng Quan Dự Án & Luồng Hoạt Động (Project Overview & Data Flow)

## 🎯 Giới thiệu dự án

**ShipTrack** là một hệ thống theo dõi 100 shipper (nhân viên giao hàng) theo thời gian thực (real-time) dựa trên kiến trúc **Clean Architecture**. Hệ thống mô phỏng việc thu thập dữ liệu tọa độ GPS từ các thiết bị di động, xử lý dữ liệu qua hệ thống hàng đợi và hiển thị trực tiếp lên bảng điều khiển (Dashboard) nền tối (Dark UI) với bản đồ tương tác.

**Tính năng cốt lõi:**
- Theo dõi thời gian thực 100 shipper ảo bằng GPS.
- 100% xử lý Backend không đồng bộ (Async) với **FastAPI**, **Motor** (MongoDB), và **Kafka**.
- Dashboard hiện đại sử dụng **React**, **Vite** và **Leaflet.js**.
- Áp dụng các thuật toán **Haversine** (tính toán khoảng cách, tốc độ) và **Linear Interpolation** (làm mịn đường đi).
- Có cảnh báo shipper dừng quá lâu, trễ hẹn, hoặc mất kết nối (Offline).

---

## 🔄 Luồng hoạt động hệ thống (Data Flow)

Luồng hoạt động của hệ thống từ lúc shipper gửi dữ liệu GPS đến khi hiển thị trên giao diện người dùng được chia thành các bước rõ ràng sau:

### 1. Thu thập dữ liệu GPS (Ingestion)
- **Thiết bị / Simulator** gửi sự kiện GPS mỗi 1 giây.
- **Dữ liệu mẫu:** `{ "shipper_id": "SHP-001", "lat": 10.77695, "lon": 106.70095 }`
- Dữ liệu được gửi qua giao thức WebSocket tới endpoint `ws://backend:8000/ws/ingest`.

### 2. Message Queue (Kafka)
- Backend nhận dữ liệu qua WebSocket và đóng vai trò là **Kafka Producer**, đẩy sự kiện GPS vào topic `gps_stream` trên Kafka.
- Điều này giúp hệ thống lưu trữ tạm thời lượng lớn dữ liệu GPS và xử lý bất đồng bộ, tăng khả năng mở rộng (scaling).

### 3. Xử lý dữ liệu cốt lõi (9 Bước Core Business Logic)
Một **Kafka Consumer** sẽ lấy từng sự kiện trong topic `gps_stream` và đưa qua hàm `process_gps_event()`. Quá trình này gồm 9 bước:

1. **VALIDATE:** Kiểm tra tính hợp lệ của `shipper_id`, tọa độ `lat/lon`, và lọc bỏ các dữ liệu rác (VD: tốc độ > 80km/h vô lý).
2. **CREATE TRACKING EVENT:** Khởi tạo đối tượng sự kiện lưu vết (Tracking Event) với ID duy nhất.
3. **CALCULATE SPEED & HEADING:** Dùng công thức *Haversine* tính toán khoảng cách giữa điểm hiện tại và điểm trước đó để suy ra tốc độ (km/h) và hướng di chuyển (heading).
4. **LINEAR INTERPOLATION:** Áp dụng phép nội suy tuyến tính để tính toán tọa độ làm mịn (smooth lat/lon) giữa các điểm, giúp marker trên bản đồ di chuyển mượt mà hơn.
5. **FETCH & COMPUTE ETA:** Truy vấn đơn hàng hiện tại đang giao của shipper. Tính toán thời gian dự kiến đến nơi (ETA) và số phút bị trễ (Delay).
6. **SAVE TRACKING EVENT:** Lưu sự kiện theo dõi vào collection `tracking_events` của MongoDB. Dữ liệu này chỉ cho phép *Append-only* (chỉ chèn thêm, không sửa xóa) để làm log thanh tra (audit trail).
7. **CASCADE UPDATE:** Cập nhật đồng thời trạng thái mới nhất vào các collection `shippers` và `orders` trong một transaction duy nhất để đảm bảo tính nhất quán dữ liệu.
8. **WEBSOCKET BROADCAST:** Đẩy trạng thái mới nhất này qua WebSocket tới tất cả các client (trình duyệt) đang kết nối.
9. **DECISION ENGINE:** Kiểm tra và đánh giá các luật nghiệp vụ (Rules). Ví dụ: Đứng yên > 2 phút chuyển sang IDLE, Mất tín hiệu chuyển sang OFFLINE.

### 4. Hiển thị UI (Frontend)
- Frontend (React) nhận được thông điệp qua kết nối `ws://localhost:8000/ws`.
- Dữ liệu JSON được phân tích và lưu vào State.
- Bản đồ Leaflet nhận lệnh `marker.setLatLng()` để cập nhật vị trí shipper mà không cần tải lại trang.
- Bảng chi tiết bên phải (Right Panel) và bảng điều khiển tổng quan (Dashboard Stats) cũng được cập nhật ngay lập tức.

---

## 📈 Sơ đồ tóm tắt (Diagram)

```text
[ Simulator / Shipper App ]
           │
           ▼ (WebSocket /ws/ingest)
           │
[ FastAPI Ingestion Route ]
           │
           ▼
[ Kafka Producer (Topic: gps_stream) ]
           │
           ▼
[ Kafka Consumer (shiptrack-consumer) ]
           │
           ▼
[ 9-Step Stream Processor (Clean Architecture Application Layer) ]
           │
           ├─► [ MongoDB Transaction (Update Shippers/Orders, Insert Tracking Event) ]
           │
           ├─► [ Decision Engine (Alerts) ]
           │
           ▼
[ WebSocket Broadcast Manager ]
           │
           ▼ (WebSocket /ws)
           │
[ React Dashboard (Leaflet Map, Stats, Shipper List) ]
```

## Khả năng mở rộng (Performance & Scalability)
- **Tốc độ xử lý:** < 200ms cho quá trình từ gửi GPS đến hiện trên Dashboard.
- **Lưu lượng:** 100 sự kiện/giây (với 100 shipper), có khả năng scale lên 1000+ sự kiện/giây nhờ kiến trúc Kafka event-driven.
- **I/O:** 100% Async / Không bị block bởi các thao tác kết nối CSDL.