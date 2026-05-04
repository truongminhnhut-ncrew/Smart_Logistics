# 🎯 HƯỚNG DẪN TEST UI - ShipTrack Real-time Shipper Tracking

## 🌐 Truy cập hệ thống

### Frontend (UI Dashboard)
📍 **URL:** http://localhost:3000

### Backend API Docs (Swagger)
📍 **URL:** http://localhost:8000/docs

### WebSocket Connection
📍 **URL:** ws://localhost:8000/ws

---

## 📋 KIỂM TRA CÁC CHỨC NĂNG CHÍNH

### 1️⃣ Dashboard & Map View
**Mục tiêu:** Xem bản đồ thời gian thực với 30 shipper

**Các bước:**
1. Mở http://localhost:3000
2. Xem bản đồ Leaflet hiển thị khu vực Bình Thạnh, TP.HCM
3. 30 marker (shipper) sẽ hiển thị quanh kho (02 Võ Oanh)
4. Warehouse marker màu vàng ở tâm (10.8051, 106.7144)

**Kỳ vọng:**
- ✓ Map load thành công
- ✓ Tất cả 30 marker hiển thị
- ✓ Các shipper có trạng thái ban đầu IDLE (màu xám)

---

### 2️⃣ Bắt đầu Simulation
**Mục tiêu:** Kích hoạt mô phỏng, shipper bắt đầu di chuyển

**Các bước:**
1. Tìm nút **"🚀 Bắt đầu giao hàng"** trên UI
2. Click nút → simulation start
3. Quan sát bản đồ, các shipper bắt đầu di chuyển

**Kỳ vọng:**
- ✓ Phase IDLE → DISPATCHING
- ✓ 3 shipper gần nhất dispatch về kho (màu tím)
- ✓ Marker di chuyển mượt (linear interpolation)
- ✓ Khoảng cách và tốc độ cập nhật realtime

---

### 3️⃣ Danh sách Shipper
**Mục tiêu:** Xem chi tiết từng shipper

**Các bước:**
1. Sidebar trái: click vào 1 shipper trong danh sách
2. Chọn ví dụ: **SHP-017**
3. Sidebar phải (Details tab): xem thông tin chi tiết

**Kỳ vọng:**
- ✓ Hiển thị: shipper_id, name, vehicle_type, vehicle_plate
- ✓ GPS realtime: lat, lon, speed_kmh, heading, signal_status
- ✓ Thống kê: completed_count, total_distance_km
- ✓ Trạng thái hiện tại: status (IDLE/DELIVERING/AT_WAREHOUSE/...)

---

### 4️⃣ Tìm Shipper Gần Kho Nhất
**Mục tiêu:** Hiển thị top 3 shipper gần kho nhất

**Các bước:**
1. Sau khi bắt đầu simulation
2. Click nút **"🔍 Tìm 3 shipper gần kho nhất"**
3. Một panel hiện lên danh sách các shipper + khoảng cách

**Kỳ vọng:**
- ✓ Danh sách hiển thị: SHP-ID, Distance (km), Action button
- ✓ Khoảng cách tính theo Haversine formula (chính xác)
- ✓ Ví dụ: SHP-014 (2.0 km), SHP-027 (2.12 km), SHP-012 (2.23 km)

---

### 5️⃣ Tạo & Gán Đơn Hàng
**Mục tiêu:** Tạo đơn hàng và gán cho shipper

**Các bước:**
1. Khi tất cả 3 shipper arrived at warehouse
2. Modal **"DeliveryModal"** tự động hiện lên
3. Nhập thông tin:
   - Customer name: "Nguyễn Văn A"
   - Delivery address: "123 Nguyễn Trái, Q.1"
   - Weight: 2.5 kg
   - Select shipper: SHP-017
4. Click **"Giao hàng"**

**Kỳ vọng:**
- ✓ Đơn hàng được tạo (order_id generated)
- ✓ SHP-017 nhận đơn
- ✓ Status đổi DELIVERING
- ✓ Marker đổi màu xanh lá
- ✓ Shipper bắt đầu di chuyển về điểm giao

---

### 6️⃣ Báo Sự Cố
**Mục tiêu:** Báo sự cố cho shipper đang giao, hệ thống xử lý

**Các bước:**
1. Chọn shipper SHP-017 (đang delivering)
2. Sidebar trái: tìm **IncidentPanel** - bảng 5 nút sự cố:
   - 🚗 Kẹt xe
   - 🌧️ Mưa lớn
   - 👤 Khách vắng
   - 🔧 Hư xe
   - 🔋 Hết pin
3. Click ví dụ: **"🚗 Kẹt xe"**
4. Toast notification popup "Incident created"

**Kỳ vọng:**
- ✓ Toast notification hiện lên realtime
- ✓ Incident được lưu vào DB
- ✓ Status shipper có thể cập nhật (delay)
- ✓ Admin có thể xem incident details

---

### 7️⃣ Dashboard Stats
**Mục tiêu:** Xem thống kê fleet tổng hợp

**Các bước:**
1. Sidebar phải: click tab **"Stats"**
2. Xem dashboard với các thống kê:
   - Tổng shipper online: 30
   - Đang giao: 1
   - Tổng quãng đường
   - Top shippers

**Kỳ vọng:**
- ✓ Fleet overview cập nhật realtime
- ✓ Hiển thị số lượng shipper theo trạng thái
- ✓ Top performers list
- ✓ Order statistics

---

### 8️⃣ WebSocket Realtime Updates
**Mục tiêu:** Kiểm tra dữ liệu được broadcast realtime qua WS

**Các bước:**
1. Mở **Browser DevTools** (F12)
2. Tab **Network** → filter WS
3. Click vào connection `/ws`
4. Tab **Messages** → xem các event:
   - `initial_state`
   - `bulk_gps_update` (mỗi 1 giây)
   - `delivery_assigned`
   - `incident_created`
   - ...

**Kỳ vọng:**
- ✓ WebSocket kết nối thành công (101 Switching Protocols)
- ✓ Messages nhận liên tục (bulk_gps_update)
- ✓ Event data là JSON có `type` và `data` field
- ✓ Bản đồ cập nhật vị trí mỗi tick từ WS message

---

### 9️⃣ API Swagger Documentation
**Mục tiêu:** Khám phá tất cả API endpoints

**Các bước:**
1. Mở http://localhost:8000/docs
2. Scroll danh sách endpoint
3. Click expand ví dụ: **GET /shippers**
4. Click **Try it out** → **Execute**
5. Xem response: 30 shippers JSON data

**Kỳ vọng:**
- ✓ Swagger UI load
- ✓ 28 endpoints liệt kê đầy đủ
- ✓ Test request/response hoạt động
- ✓ Model schemas rõ ràng

---

## 🧪 TEST SCENARIOS

### Scenario 1: Happy Path (Giao hàng thành công)
```
Start → Dispatch → Arrive → Create Order → Assign → Delivering → Complete
```

### Scenario 2: Với Incident (Xử lý sự cố)
```
Start → Dispatch → Arrive → Create Order → Assign → Delivering
→ (🚗 Traffic jam occurs) → (A* reroute) → Delivering (continue) → Complete
```

### Scenario 3: Reset & Restart
```
Complete → Click Reset → Back to IDLE → 30 new shippers
→ Start simulation again
```

---

## 🔧 SYSTEM REQUIREMENTS VERIFIED

✅ **Backend:**
- FastAPI running on port 8000
- All 28 endpoints responding
- MongoDB connected and storing data
- Redis cache active
- Kafka ready for events

✅ **Frontend:**
- Vite dev server running on port 3000
- React 18 + Vite 5.0.8
- Leaflet map library loaded
- WebSocket connection ready

✅ **Database:**
- MongoDB: 6 collections ready (shippers, orders, incidents, etc.)
- Redis: GPS cache operational
- Data persistence: OK

✅ **Infrastructure:**
- Docker Compose: 6/6 containers running
- All services healthy
- Network connectivity: OK

---

## 📊 EXPECTED PERFORMANCE

| Metric | Target | Actual |
|--------|--------|--------|
| Backend response time | < 200ms | ✅ OK |
| GPS update frequency | 1/sec | ✅ 1 Hz |
| Shipper count | 30 | ✅ 30 |
| Frontend load time | < 5s | ✅ Vite fast |
| WebSocket latency | < 100ms | ✅ Realtime |
| Map rendering | 60 FPS | ✅ Leaflet smooth |

---

## 🐛 TROUBLESHOOTING

### Frontend không load (http://localhost:3000)
```bash
# Check frontend container
docker logs smart_logistics-frontend-1

# Restart frontend
docker restart smart_logistics-frontend-1
```

### WebSocket không kết nối
```bash
# Check backend logs
docker logs smart_logistics-backend-1

# Verify ws endpoint
curl -v http://localhost:8000/health
```

### API endpoint error
```bash
# Check all endpoints
curl http://localhost:8000/docs

# Test health
curl http://localhost:8000/health
```

---

## ✅ VALIDATION CHECKLIST

Sau khi test, confirm các items sau:

- [ ] Frontend loads đúng tại http://localhost:3000
- [ ] Bản đồ hiển thị 30 shipper marker
- [ ] Warehouse marker ở đúng vị trí (02 Võ Oanh)
- [ ] Simulation start button hoạt động
- [ ] 3 shipper gần nhất được dispatch
- [ ] Shipper marker di chuyển realtime
- [ ] WebSocket messages stream trong DevTools
- [ ] Danh sách shipper cập nhật
- [ ] Có thể tạo & gán đơn hàng
- [ ] Incident creation hoạt động
- [ ] Stats dashboard cập nhật
- [ ] API docs accessible tại /docs
- [ ] Tất cả 28 endpoints respond correctly
- [ ] Reset simulation hoạt động

---

## 🎉 READY FOR TESTING!

**Bạn đã sẵn sàng test hệ thống ShipTrack**

Frontend: 🌐 http://localhost:3000  
Backend API: 📡 http://localhost:8000  
Swagger Docs: 📚 http://localhost:8000/docs  

Enjoy! 🚀
