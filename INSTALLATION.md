# Hướng Dẫn Cài Đặt (Installation Guide)

## 1️⃣ Yêu cầu trước (Prerequisites)
- Docker Desktop + Docker Compose v2
- Node.js 18+ (để phát triển frontend, tùy chọn)
- Python 3.11+ (để phát triển backend, tùy chọn)
- Các cổng mở: `3000` (frontend), `8000` (backend), `27017` (MongoDB), `9092` (Kafka), `6379` (Redis)

## 2️⃣ Cài đặt nhanh bằng Docker (Khuyến nghị)

```bash
# Bước 1: Di chuyển vào thư mục dự án
cd Smart_Logistics

# Bước 2: Sao chép file môi trường (nếu cần)
cp .env.example .env

# Bước 3: Khởi động toàn bộ dịch vụ
docker compose up -d

# Bước 4: Kiểm tra trạng thái container
docker compose ps
```

### Khởi động mô phỏng (Simulator)

```bash
# Chạy mô phỏng GPS (cũng sử dụng Docker)
docker compose --profile simulator up -d simulator
# Hoặc chạy trực tiếp trong container backend
docker compose exec backend python -m data_generator.simulate
```

## 3️⃣ Chạy cục bộ (không dùng Docker cho backend)

### Backend
```bash
# Tạo và kích hoạt virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

# Cài đặt dependencies
pip install -r requirements-local.txt

# Khởi động các service hạ tầng (MongoDB, Kafka, Redis, Zookeeper)
docker compose up -d mongodb kafka redis zookeeper

# Chạy backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # Mở http://localhost:3000
```

## 4️⃣ Kiểm tra nhanh
- Frontend: http://localhost:3000
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- WebSocket UI: ws://localhost:8000/ws
- Health check: `curl http://localhost:8000/health`

## 5️⃣ Các lệnh thường dùng
```bash
# Xem logs
docker compose logs -f
docker compose logs --tail=100 backend

# Dừng & xóa containers
docker compose down
docker compose down -v   # xóa volumes

# Khởi động lại backend
docker compose restart backend

# Rebuild image backend
docker compose build --no-cache backend
docker compose up -d