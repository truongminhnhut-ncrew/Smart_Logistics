SMART Logistics — Tổng quan & Hướng dẫn nhanh (Tiếng Việt)

Mục đích
--------
Tài liệu này tóm tắt cấu trúc project Smart_Logistics, hướng dẫn thiết lập môi trường, luồng backend/frontend, và các bước quick-start để chạy thử hệ thống mô phỏng giao vận nội bộ. Mục tiêu: giữ lại và bổ sung các file .md hiện có, để bất kỳ ai (kỹ sư hoặc reviewer) nhanh chóng hiểu, cài đặt và chạy hệ thống.

1) Cấu trúc thư mục (top-level)
--------------------------------
- .env.example                     — Mẫu biến môi trường
- docker-compose.yml               — Tổ hợp dịch vụ (backend, frontend, db nếu có)
- README.md                        — Tổng quan (tiếng Anh/đa ngôn ngữ)
- SETUP.md                         — Hướng dẫn cài đặt (chi tiết, có thể bằng EN)
- QUICK_START_VIET.md              — Hướng dẫn nhanh bằng tiếng Việt (nếu có)
- ARCHITECTURE.md                  — Kiến trúc hệ thống (kiến trúc cao cấp)
- API_DOCUMENTATION.md             — Tài liệu REST/WebSocket API
- BACKEND_GUIDE.md                 — Hướng dẫn chi tiết backend
- FRONTEND_GUIDE.md                — Hướng dẫn chi tiết frontend
- DATA_FLOW.md                      — Luồng dữ liệu, event & schemas
- BACKEND_FLOW.md / FRONTEND_FLOW.md — Luồng cụ thể thực thi (tick, routing, dispatch)
- backend/                          — Mã nguồn backend (FastAPI, dịch vụ, models, repos)
- frontend/                         — Ứng dụng frontend (vite/react hoặc tương tự)
- docs/ hoặc Smart_Logistics_DOCS/  — Tài liệu phụ trợ (bằng tiếng Việt)
- run_automation.py                 — Scripts hỗ trợ chạy/migration/sync

2) Tóm tắt các thành phần chính
-------------------------------
- Backend
  - FastAPI-based application
  - Các module chính: routing_engine, simulation_engine, lstm_predictor, repositories (DB)
  - MongoDB (hoặc DB được config trong env) để lưu snapshot shipper & tracking events
  - WebSocket manager để broadcast realtime GPS/events tới frontend
  - File quan trọng: backend/app/application/services/simulation_engine.py (vòng lặp chính), routing_engine.py, lstm_predictor.py, repositories

- Frontend
  - Ứng dụng web (vite + react / đơn trang) hiển thị markers, route polylines, cảnh báo realtime
  - Giao tiếp với backend qua REST (API) và WebSocket cho cập nhật realtime
  - File quan trọng: frontend/src/*, frontend/index.html, package.json / vite.config.js

- Data & Luồng
  - Mô phỏng tạo vị trí shipper (simulation_engine) → cập nhật in-memory → broadcast qua WS → frontend hiển thị
  - Khi dispatch/set_delivery_target → backend gọi routing engine để lấy route (routing_graph/A* offline, fallback OSRM)
  - Tracking events lưu vào MongoDB thông qua TrackingEventRepository
  - Incident detection automatic (speed drop, stop timeout, lost GPS) theo cấu hình trong simulation_engine

3) Hướng dẫn cài đặt nhanh (máy dev, Windows / WSL / Linux)
------------------------------------------------------------
Yêu cầu cơ bản:
- Python 3.10+ (Backend)
- Node 16+ (Frontend)
- Docker & docker-compose (khuyến nghị)
- MongoDB (nếu không dùng docker-compose để phối hợp)

Quick-start (local, không docker)
1. Backend:
   - cd Smart_Logistics/backend
   - python -m venv .venv
   - .venv\\Scripts\\activate (Windows CMD/PowerShell) hoặc source .venv/bin/activate (bash)
   - pip install -r requirements.txt
   - copy ../.env.example -> .env và chỉnh biến môi trường (DB URI, API keys nếu có)
   - uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

2. Frontend:
   - cd Smart_Logistics/frontend
   - npm install
   - npm run dev (hoặc npm run build && npm run preview)

Quick-start (docker-compose)
- Từ thư mục Smart_Logistics:
  - docker-compose up --build
  - Truy cập: frontend trên port (theo docker-compose), backend API tại port 8000 (hoặc cấu hình)

4) Luồng backend (chi tiết ngắn)
--------------------------------
- Startup FastAPI:
  - Khởi tạo các singletons (routing_graph, simulation_engine)
  - simulation_engine.sync_all_to_mongo() (tùy cấu hình)
  - Background task: simulation_engine.run() — vòng lặp tick theo GPS_INTERVAL (1s)
- Vòng tick:
  - Với mỗi shipper: move() theo route_waypoints; auto-detect incidents; gửi event -> upsert snapshot -> ghi tracking event -> broadcast WS
- Dispatch flow:
  - UI → POST /dispatch → backend chọn shipper → gọi _fetch_graph_route() (routing_graph A* hoặc OSRM) → shipper.set_route(waypoints)
- Incident flow:
  - apply_incident() / resolve_incident() update trạng thái shipper và broadcast

5) Luồng frontend (chi tiết ngắn)
---------------------------------
- Kết nối WebSocket tới backend để nhận bulk_gps_update, shipper_arrived, eta_updated, system_alert, customer_notification
- Hiển thị markers, route polylines, trạng thái shipper (DELIVERING, IDLE, DELAYED, ...)
- Gọi API để dispatch/set_delivery_target/apply_incident theo nhu cầu

6) Những file .md hiện có & đề xuất bổ sung
--------------------------------------------
Hiện tại repo đã có nhiều file .md. Tôi sẽ:
- Không xóa file nào (theo yêu cầu).
- Tạo 1 tài liệu tổng hợp bằng Tiếng Việt (tệp này) để làm "single-entry" cho người đọc.
- Kiểm tra & (nếu cần) bổ sung những file .md sau bằng nội dung tiếng Việt ngắn gọn (nếu file hiện có chưa đầy đủ):
  - SETUP.md (bổ sung bước setup Windows/WSL + Docker)
  - BACKEND_GUIDE.md (bổ sung phần chạy dev, script hữu dụng, mô tả services chính)
  - FRONTEND_GUIDE.md (bổ sung cách chạy frontend, cấu trúc thư mục src)
  - API_DOCUMENTATION.md (tóm tắt endpoints quan trọng + trỏ đến file chi tiết)
  - QUICK_START_VIET.md (kiểm tra, bổ sung nếu thiếu)
- Nếu các file đó đã có nội dung tốt, tôi sẽ không overwrite mà chỉ tạo file tóm tắt/link đến file đó.

7) Việc tôi sẽ làm tiếp (theo lựa chọn 1 VI)
--------------------------------------------
- [x] Sinh file tổng hợp Tiếng Việt (Smart_Logistics/SMART_LOGISTICS_OVERVIEW_VIET.md) — đã tạo.
- [ ] Đọc (và nếu cần) bổ sung SETUP.md, BACKEND_GUIDE.md, FRONTEND_GUIDE.md, API_DOCUMENTATION.md bằng tiếng Việt.
- [ ] Báo lại danh sách file .md đã được bổ sung/chỉnh sửa, và hiển thị nội dung tóm tắt của những file tôi tạo/đã thay đổi.
- [ ] Chờ xác nhận của bạn trước khi thực hiện thay đổi tiếp theo (overwrite các file .md hiện có).

8) Ghi chú & bước tiếp theo
---------------------------
- Tôi đã tạo file SMART_LOGISTICS_OVERVIEW_VIET.md tóm tắt toàn bộ hệ thống bằng tiếng Việt (nằm ở thư mục gốc Smart_Logistics).
- Bạn có muốn tôi tiếp tục và mở từng file .md sau để kiểm tra nội dung hiện có và bổ sung (overwrite) bằng phiên bản tiếng Việt chi tiết cho từng file (SETUP.md, BACKEND_GUIDE.md, FRONTEND_GUIDE.md, API_DOCUMENTATION.md, QUICK_START_VIET.md)? Nếu có, xác nhận "Tiếp tục bổ sung các file .md (VI)". Nếu muốn giới hạn danh sách file cần chỉnh, liệt kê tên file.