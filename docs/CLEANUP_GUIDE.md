# CLEANUP_GUIDE — Hướng dẫn clean folder Smart_Logistics

## Mục tiêu

Giữ project dễ đọc, dễ chạy, tài liệu tập trung và không xoá nhầm file runtime.

## Nguyên tắc

1. Không xoá code/config khi chưa backup hoặc commit git.
2. Tài liệu `.md` nên gom vào `Smart_Logistics/docs/`.
3. Root folder chỉ nên giữ các file entry point cần thiết.
4. File `.env` thật không được commit; chỉ giữ `.env.example`.
5. Không xoá `package-lock.json`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`.

## Cấu trúc root đề xuất

```txt
Smart_Logistics/
├── README.md
├── SETUP.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements-local.txt
├── run_automation.py
├── backend/
├── frontend/
└── docs/
```

## File nên giữ ở root

| File/folder | Lý do |
|---|---|
| `README.md` | Entry point của project |
| `SETUP.md` | Hướng dẫn setup nhanh |
| `docker-compose.yml` | Chạy full stack |
| `.env.example` | Mẫu biến môi trường |
| `.gitignore` | Chặn commit file rác/secret |
| `requirements-local.txt` | Dependency local nếu cần |
| `run_automation.py` | Script automation nếu đang dùng |
| `backend/` | Backend source code |
| `frontend/` | Frontend source code |
| `docs/` | Tài liệu chi tiết |

## Tài liệu nên đưa vào `docs/`

```txt
ARCHITECTURE.md
BACKEND_GUIDE.md
FRONTEND_GUIDE.md
DATA_FLOW.md
API_DOCUMENTATION.md
CLEAN_ARCHITECTURE_ASSESSMENT.md
CLEAN_ARCHITECTURE_OVERVIEW.md
BACKEND_FLOW.md
FRONTEND_FLOW.md
QUICK_START_VIET.md
SMART_LOGISTICS_OVERVIEW_VIET.md
project.md
CLAUDE.md
```

Nếu muốn root gọn hơn, có thể move bằng PowerShell sau khi backup:

```powershell
Move-Item Smart_Logistics\ARCHITECTURE.md Smart_Logistics\docs\
Move-Item Smart_Logistics\BACKEND_GUIDE.md Smart_Logistics\docs\
Move-Item Smart_Logistics\FRONTEND_GUIDE.md Smart_Logistics\docs\
Move-Item Smart_Logistics\DATA_FLOW.md Smart_Logistics\docs\
Move-Item Smart_Logistics\API_DOCUMENTATION.md Smart_Logistics\docs\
Move-Item Smart_Logistics\CLEAN_ARCHITECTURE_ASSESSMENT.md Smart_Logistics\docs\
Move-Item Smart_Logistics\CLEAN_ARCHITECTURE_OVERVIEW.md Smart_Logistics\docs\
Move-Item Smart_Logistics\BACKEND_FLOW.md Smart_Logistics\docs\
Move-Item Smart_Logistics\FRONTEND_FLOW.md Smart_Logistics\docs\
Move-Item Smart_Logistics\QUICK_START_VIET.md Smart_Logistics\docs\
Move-Item Smart_Logistics\SMART_LOGISTICS_OVERVIEW_VIET.md Smart_Logistics\docs\
Move-Item Smart_Logistics\project.md Smart_Logistics\docs\
Move-Item Smart_Logistics\CLAUDE.md Smart_Logistics\docs\
```

## File/folder không nên xoá

```txt
Smart_Logistics/backend/app/
Smart_Logistics/backend/data_generator/
Smart_Logistics/backend/scripts/
Smart_Logistics/backend/Dockerfile
Smart_Logistics/backend/requirements.txt

Smart_Logistics/frontend/src/
Smart_Logistics/frontend/package.json
Smart_Logistics/frontend/package-lock.json
Smart_Logistics/frontend/Dockerfile
Smart_Logistics/frontend/vite.config.js
Smart_Logistics/frontend/index.html

Smart_Logistics/docker-compose.yml
Smart_Logistics/.env.example
```

## File có thể archive nếu không cần

```txt
Smart_Logistics_DOCS/
```

Folder `Smart_Logistics_DOCS` là bản tài liệu ngoài project. Nếu đã copy/gom đủ tài liệu vào `Smart_Logistics/docs/`, có thể archive folder này ra nơi khác thay vì xoá ngay.

## Lệnh kiểm tra sau khi clean

### Docker compose config

```powershell
cd Smart_Logistics
docker compose config
```

### Backend compile check

```powershell
cd Smart_Logistics\backend
python -m compileall app
```

### Frontend build

```powershell
cd Smart_Logistics\frontend
npm run build
```

## Ghi chú kỹ thuật cần xử lý sau

- `backend/app/presentation/api/routers/simulation.py` hiện có dấu hiệu duplicate endpoint:
  - `POST /simulation/incident/apply`
  - `POST /simulation/incident/resolve/{shipper_id}`
- Nên thống nhất incident flow giữa:
  - `/incidents`
  - `/simulation/incident/*`
- Nên tách constants warehouse ra config.
- Nên thêm test cho `simulation_engine.py`.