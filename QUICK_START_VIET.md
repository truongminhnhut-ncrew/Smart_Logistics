# Hướng dẫn nhanh (Tiếng Việt) — Smart_Logistics

Phiên bản tóm tắt để nhanh chóng chạy project trên máy phát triển hoặc Docker.

---

## Yêu cầu trước
- Docker + Docker Compose (v2)
- Node.js 18+ (cho frontend, tùy chọn)
- Python 3.11+ (cho backend, tùy chọn)
- Cổng mở: 3000 (frontend), 8000 (backend), 27017 (MongoDB), 9092 (Kafka), 6379 (Redis)

---

## 1) Chạy toàn bộ bằng Docker (khuyến nghị)
1. Mở terminal, chuyển tới thư mục project:
   cd Smart_Logistics

2. Sao chép file môi trường (nếu cần):
   cp .env.example .env

3. Chạy tất cả dịch vụ:
   docker compose up -d

4. Kiểm tra trạng thái container:
   docker compose ps

5. Xem log backend (nếu cần debug):
   docker compose logs -f backend

6. Khởi động mô phỏng (nếu dùng profile simulator):
   docker compose --profile simulator up -d simulator
   hoặc để xem output:
   docker compose --profile simulator up simulator

---

## 2) Chạy cục bộ phục vụ phát triển (không dùng Docker cho backend)

Backend:
1. Tạo và kích hoạt virtualenv:
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate  # macOS/Linux

2. Cài dependencies:
   pip install -r requirements-local.txt

3. Chạy MongoDB/Kafka/Redis bằng Docker (phần infra):
   docker compose up -d mongodb kafka redis zookeeper

4. Chạy backend:
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Frontend:
1. Cài dependencies:
   cd frontend
   npm install

2. Chạy dev server:
   npm run dev
   Mở trình duyệt: http://localhost:3000

Simulator (tùy chọn):
1. Từ thư mục project:
   cd backend
   python -m data_generator.simulate

---

## 3) URL hữu ích
- Frontend: http://localhost:3000
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- WebSocket (UI): ws://localhost:8000/ws
- WebSocket (ingest): ws://localhost:8000/ws/ingest
- Health check: http://localhost:8000/health

---

## 4) Các lệnh thường dùng
- Xem logs:
  docker compose logs -f
  docker compose logs --tail=100 backend

- Dừng & xóa containers:
  docker compose down
  docker compose down -v  # xóa volumes

- Khởi động lại backend:
  docker compose restart backend

- Rebuild image backend:
  docker compose build --no-cache backend
  docker compose up -d

---

## 5) Kiểm tra nhanh khi gặp lỗi thường gặp
- Backend không khởi động / lỗi import:
  - Kiểm tra log: docker compose logs backend
  - Kiểm tra lỗi indent/syntax (thường trong simulation_engine.py nếu log báo IndentationError)
- Frontend hiển thị 0/100 online:
  - Kiểm tra simulator đang chạy
  - Kiểm tra kết nối WebSocket trong DevTools (Network → WS)
- Không thấy tracking events trong DB:
  - Kiểm tra collection `tracking_events` và index TTL
  - Kiểm tra logs Kafka / repository lỗi

---

## 6) Gợi ý debug nhanh
- Xem log backend trong 200 dòng gần nhất:
  docker compose logs backend --tail=200
- Mở shell trong container backend:
  docker compose exec backend bash
- Chạy API trực tiếp:
  curl http://localhost:8000/shippers

---

Tập tin tham khảo:
- SETUP.md — Hướng dẫn chi tiết (bằng tiếng Anh)
- BACKEND_FLOW.md — Luồng xử lý backend
- FRONTEND_FLOW.md — Luồng và thành phần frontend
- DATA_FLOW.md — Pipeline 9 bước xử lý GPS