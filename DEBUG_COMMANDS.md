# 🔍 ShipTrack Debug Commands

> Để kiểm tra tại sao shipper không hiển thị trên bản đồ.

---

## **1️⃣ Kiểm tra Docker Compose Services**

### Check tất cả services đã khởi động không
```bash
cd C:\Users\USER\OneDrive\Desktop\Everyhing_tosave\PussyU\smart-log\Smart_Logistics
docker compose ps
```
✅ Kỳ vọng: Tất cả 6 services (zookeeper, kafka, mongodb, redis, backend, frontend) phải `Up`

### Check logs backend
```bash
docker compose logs -f backend
```
✅ Kỳ vọng: Thấy `[GPS] Processed N messages ✅` và không lỗi

### Check logs frontend
```bash
docker compose logs -f frontend
```
✅ Kỳ vọng: `npm run dev` chạy bình thường, không lỗi

---

## **2️⃣ Kiểm tra MongoDB Collections**

### Kết nối tới MongoDB shell
```bash
docker exec -it smart_logistics-mongodb-1 mongosh
```

### Kiểm tra xem có shippers không
```javascript
use shiptrack
db.shippers.countDocuments()
db.shippers.find().limit(1)
```
✅ Kỳ vọng: Có >= 1 shipper, có fields: `shipper_id, current_lat, current_lon`

### Kiểm tra tracking events
```javascript
db.tracking_events.countDocuments()
db.tracking_events.find().sort({timestamp: -1}).limit(1)
```
✅ Kỳ vọng: Có tracking events, với timestamp gần đây (không phải ngày xưa)

### Kiểm tra orders
```javascript
db.orders.countDocuments()
db.orders.find().limit(1)
```
✅ Kỳ vọng: Có >= 1 order

### Thoát MongoDB shell
```
exit
```

---

## **3️⃣ Kiểm tra WebSocket Connections**

### Check backend health endpoint
```bash
curl http://localhost:8000/health
```
✅ Kỳ vọng:
```json
{
  "status": "ok",
  "ws_ingest_connections": > 0,   # Simulator kết nối
  "ws_client_connections": > 0    # Frontend kết nối
}
```

### Check WebSocket client endpoint
```bash
# Mở terminal + chạy lệnh này (sẽ block, Ctrl+C để thoát)
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: random" \
  -H "Sec-WebSocket-Version: 13" \
  http://localhost:8000/ws
```

---

## **4️⃣ Kiểm tra API Endpoints**

### Get tất cả shippers
```bash
curl http://localhost:8000/shippers | jq
```
✅ Kỳ vọng: Array của shippers với GPS coordinates

### Get dashboard stats
```bash
curl http://localhost:8000/stats | jq
```
✅ Kỳ vọng: `in_transit`, `delivered`, `pending`, `total_distance_km`, etc.

---

## **5️⃣ Kiểm tra Simulator**

### Run simulator (nếu chưa chạy)
```bash
docker compose --profile simulator up simulator
```

### Check logs simulator
```bash
docker compose logs -f simulator
```
✅ Kỳ vọng: Thấy `Shipper SHP-XXX: (lat, lon)` được gửi

---

## **6️⃣ Kiểm tra Kafka Topics**

### List tất cả topics
```bash
docker exec -it smart_logistics-kafka-1 kafka-topics \
  --bootstrap-server kafka:29092 --list
```

### Check gps_stream topic messages
```bash
docker exec -it smart_logistics-kafka-1 kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic gps_stream \
  --from-beginning \
  --max-messages 10
```
✅ Kỳ vọng: Thấy GPS messages từ 100 shippers

---

## **7️⃣ Kiểm tra Frontend Network**

### Mở Dev Tools (F12) → Console tab

### Copy + paste lệnh này vào console:
```javascript
// Check WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('✅ WebSocket Connected');
ws.onerror = (e) => console.error('❌ WebSocket Error:', e);
ws.onmessage = (e) => console.log('📨 Message:', JSON.parse(e.data));

// Check API
fetch('http://localhost:8000/shippers')
  .then(r => r.json())
  .then(d => console.log('✅ API Shippers:', d.length, 'items'))
  .catch(e => console.error('❌ API Error:', e));
```

---

## **8️⃣ Fix Lỗi Phổ Biến**

| Vấn đề | Nguyên nhân | Fix |
|---|---|---|
| `ws_ingest_connections: 0` | Simulator không chạy | `docker compose --profile simulator up` |
| `ws_client_connections: 0` | Frontend không kết nối WS | Check CORS, check fe.html URL config |
| `db.shippers.countDocuments() = 0` | Init DB chưa chạy | `docker compose down -v && up` |
| Shippers trên bản đồ không cập nhật | Broadcast lỗi | Check `backend logs` có lỗi không |
| Frontend Network Error | Backend không chạy | Check `docker compose ps` |

---

## **9️⃣ Nếu tất cả bình thường nhưng vẫn không thấy shippers:**

### Kiểm tra 3 thứ:
1. **WebSocket handshake:** frontend `/ws` endpoint có accept connection không?
2. **Broadcast payload format:** payload có structure đúng không?
3. **Frontend render logic:** useWebSocket hook có process message không?

### Xem logs chi tiết:
```bash
docker compose logs backend | grep -i "broadcast\|error"
```

---

**👉 Chạy các lệnh này từ trên xuống, report cho mình kết quả!**
