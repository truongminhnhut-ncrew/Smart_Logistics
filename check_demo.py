#!/usr/bin/env python3
"""
check_demo.py — Giám sát live tiến trình demo hệ thống giao hàng.

Cách chạy (đảm bảo backend đang lên):
    python Smart_Logistics/check_demo.py

Script poll API mỗi 2 giây, hiển thị liên tục (không cần xóa màn hình):
  - Phase / Bước demo hiện tại
  - Số shipper theo trạng thái
  - Chi tiết shipper đang hoạt động
  - Đơn hàng đang giao / đã giao
  - Điều kiện kết thúc (giao xong + 5 sự cố)
"""

import os
import sys
import time
import signal
import requests

# ── Bật ANSI color trên Windows 10+ ────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

BASE_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Màu ANSI ────────────────────────────────────────────────────────────────
R   = "\033[0m"
B   = "\033[1m"          # bold
GRN = "\033[92m"
YEL = "\033[93m"
RED = "\033[91m"
CYN = "\033[96m"
MAG = "\033[95m"
DIM = "\033[2m"
BLU = "\033[94m"

STATUS_CLR = {
    "IDLE":                 DIM,
    "ROAMING":              DIM,
    "HEADING_TO_WAREHOUSE": MAG,
    "AT_WAREHOUSE":         BLU,
    "DELIVERING":           CYN,
    "DELAYED":              YEL,
    "DELIVERED":            GRN,
    "VEHICLE_BREAKDOWN":    RED,
    "LOST_CONNECTION":      DIM,
    "OFFLINE":              DIM,
}

INCIDENT_LABEL = {
    "TRAFFIC_JAM":       "🚗 Kẹt xe",
    "HEAVY_RAIN":        "🌧️  Mưa lớn",
    "CUSTOMER_ABSENT":   "👤 Khách vắng",
    "VEHICLE_BREAKDOWN": "🔧 Hư xe",
    "LOST_CONNECTION":   "🔴 Mất kết nối",
}

PHASE_MAP = {
    "IDLE":              ("Bước 1-2/9", "⏸️  Khởi tạo — chờ lệnh bắt đầu"),
    "STARTED":           ("Bước 2/9",   "▶️  Đã bắt đầu — đang tìm shipper gần kho"),
    "DISPATCHING":       ("Bước 3-4/9", "🚀 Dispatch — 3 shipper đang di chuyển về kho"),
    "WAITING_FOR_ORDER": ("Bước 5/9",   "📦 Tại kho — hệ thống random 1-3 đơn cho từng shipper"),
    "DELIVERING":        ("Bước 6-7/9", "🛵 Đang giao — shipper xuất phát giao hàng (5 sự cố tự kích hoạt)"),
    "COMPLETED":         ("Bước 9/9",   "✅ Hoàn tất — tất cả đơn đã xong"),
}

running = True


def handle_sig(sig, frame):
    global running
    running = False
    print("\n\n  ⏹  Dừng giám sát.\n")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_sig)


def get(path, timeout=5):
    try:
        r = requests.get(f"{BASE_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def bar(n, max_n=20, ch="█"):
    filled = min(int(n * max_n / max(n, 1)), max_n) if n > 0 else 0
    return ch * filled


def sep(char="─", width=72):
    print(f"  {char * width}")


def main():
    # ── Tiêu đề ──────────────────────────────────────────────────────────
    print()
    print(f"  {B}{'=' * 72}{R}")
    print(f"  {B}  🚚  SMART LOGISTICS — GIÁM SÁT DEMO REALTIME{R}")
    print(f"  {B}{'=' * 72}{R}")
    print(f"  Backend: {BASE_URL}  |  Cập nhật mỗi 2s  |  Ctrl+C để dừng")
    print()

    # ── Kiểm tra kết nối ──────────────────────────────────────────────────
    health = get("/health")
    if health is None:
        print(f"  {RED}❌ Không kết nối được backend tại {BASE_URL}{R}")
        print(f"  Hãy chạy:  cd Smart_Logistics/backend && uvicorn app.main:app --reload --port 8000\n")
        sys.exit(1)
    print(f"  {GRN}✅ Backend online{R} — {health}\n")
    time.sleep(1)

    tick = 0
    seen_incidents = set()           # sự cố đã từng xuất hiện (tích lũy)
    REQUIRED = {"TRAFFIC_JAM", "HEAVY_RAIN", "CUSTOMER_ABSENT", "VEHICLE_BREAKDOWN", "LOST_CONNECTION"}

    while running:
        tick += 1
        ts = time.strftime("%H:%M:%S")

        # ── Lấy dữ liệu ──────────────────────────────────────────────────
        shippers_raw = get("/shippers") or []
        state        = get("/simulation/state") or {}
        orders_snap  = get("/simulation/orders") or {}

        # /shippers trả về list hoặc {"data": [...]}
        if isinstance(shippers_raw, dict):
            shippers = shippers_raw.get("data") or []
        else:
            shippers = shippers_raw

        phase = state.get("phase") or orders_snap.get("phase") or "UNKNOWN"
        sim_tick = state.get("tick") or orders_snap.get("tick") or "?"
        dispatched = state.get("dispatched_ids") or []
        arrived = state.get("arrived_at_warehouse") or []

        step_label, step_desc = PHASE_MAP.get(phase.upper(), (phase, ""))

        # ── Đếm trạng thái ───────────────────────────────────────────────
        cnt = {}
        active = []
        for s in shippers:
            st = str(s.get("status") or "IDLE").upper()
            cnt[st] = cnt.get(st, 0) + 1
            # Tích lũy sự cố đã xuất hiện
            if s.get("has_incident") and s.get("incident_type"):
                seen_incidents.add(s["incident_type"].upper())
            if st not in ("IDLE", "ROAMING"):
                active.append(s)

        total       = len(shippers)
        n_idle      = cnt.get("IDLE", 0) + cnt.get("ROAMING", 0)
        n_heading   = cnt.get("HEADING_TO_WAREHOUSE", 0)
        n_at_wh     = cnt.get("AT_WAREHOUSE", 0)
        n_delivering = cnt.get("DELIVERING", 0) + cnt.get("DELAYED", 0)
        n_delivered = cnt.get("DELIVERED", 0)
        n_broken    = cnt.get("VEHICLE_BREAKDOWN", 0)
        n_offline   = cnt.get("LOST_CONNECTION", 0) + cnt.get("OFFLINE", 0)

        # ── Đơn hàng ─────────────────────────────────────────────────────
        orders = orders_snap.get("orders") or {}
        n_ord_total    = len(orders)
        n_ord_transit  = sum(1 for o in orders.values() if str(o.get("status","")).upper() == "IN_TRANSIT")
        n_ord_assigned = sum(1 for o in orders.values() if str(o.get("status","")).upper() == "ASSIGNED")
        n_ord_done     = sum(1 for o in orders.values() if str(o.get("status","")).upper() in ("DELIVERED", "FAILED", "DELIVERY_FAILED", "DELIVERY_FAILED_ATTEMPT_1"))
        n_ord_pending  = n_ord_total - n_ord_transit - n_ord_assigned - n_ord_done

        # ── In block ──────────────────────────────────────────────────────
        print()
        sep("═")
        print(f"  {B}[{ts}] Tick #{tick} (sim_tick={sim_tick}){R}")
        sep()

        # Bước demo
        print(f"  {B}{CYN}► {step_label}{R}  {step_desc}")
        print(f"  Phase: {B}{phase}{R}"
              f"   |  Đã dispatch: {len(dispatched)} shipper"
              f"   |  Đến kho: {len(arrived)}/{len(dispatched)}")

        sep()

        # Bảng trạng thái shipper
        print(f"  {B}{'TRẠNG THÁI SHIPPER':<32} {'SL':>4}  {'BAR'}{R}")
        def row(label, n, color):
            b = bar(n, max_n=25) if n > 0 else ""
            print(f"  {color}{label:<32}{R} {B}{n:>4}{R}  {color}{b}{R}")

        row("⏸️  Chờ lệnh    (IDLE/ROAM)",   n_idle,      DIM)
        row("🚚 Về kho      (HEADING_WH)",    n_heading,   MAG)
        row("📦 Tại kho     (AT_WH)",         n_at_wh,     BLU)
        row("🛵 Đang giao   (DELIVERING)",    n_delivering, CYN)
        row("✅ Đã giao     (DELIVERED)",     n_delivered, GRN)
        row("🔧 Hư xe       (BREAKDOWN)",     n_broken,    RED)
        row("🔴 Mất kết nối (LOST_CONN)",     n_offline,   DIM)
        sep()
        print(f"  Tổng {B}{total}{R} shipper  |  "
              f"{CYN}Đang giao: {B}{n_delivering}{R}  |  "
              f"{GRN}Đã xong: {B}{n_delivered}{R}")

        # Đơn hàng
        if n_ord_total > 0:
            sep()
            print(f"  {B}ĐƠN HÀNG:{R}  Tổng {n_ord_total}"
                  f"  |  {CYN}Đang giao: {n_ord_transit}{R}"
                  f"  |  {BLU}Đã gán: {n_ord_assigned}{R}"
                  f"  |  {DIM}Chờ: {n_ord_pending}{R}"
                  f"  |  {GRN}Xong: {n_ord_done}{R}")

        # Chi tiết shipper đang hoạt động
        if active:
            sep()
            print(f"  {B}CHI TIẾT SHIPPER ĐANG HOẠT ĐỘNG:{R}")
            hdr = f"  {'ID':<13} {'STATUS':<22} {'ORDER':<13} {'Q':>2} {'SỰ CỐ':<22} {'ETA':>6}"
            print(hdr)
            print(f"  {'─'*13} {'─'*22} {'─'*13} {'─'*2} {'─'*22} {'─'*6}")
            for s in active[:15]:
                sid  = str(s.get("shipper_id") or "?")[:12]
                st   = str(s.get("status") or "?").upper()
                clr  = STATUS_CLR.get(st, "")
                ord_ = str(s.get("order_id") or "—")[:12]
                q    = str(s.get("pending_orders_count") or 0)
                inc  = ""
                if s.get("has_incident") and s.get("incident_type"):
                    inc = INCIDENT_LABEL.get(s["incident_type"].upper(), s["incident_type"])[:21]
                eta_v = s.get("eta_minutes")
                eta  = f"{eta_v:.1f}m" if eta_v is not None else "—"
                print(f"  {sid:<13} {clr}{st:<22}{R} {ord_:<13} {q:>2} {YEL}{inc:<22}{R} {eta:>6}")

        # Sự cố tích lũy
        sep()
        print(f"  {B}SỰ CỐ ĐÃ TRIGGER (tích lũy):{R}")
        for inc_type in REQUIRED:
            seen = inc_type in seen_incidents
            icon = f"{GRN}✅{R}" if seen else f"{YEL}○ {R}"
            label = INCIDENT_LABEL.get(inc_type, inc_type)
            print(f"    {icon}  {label}")

        # Điều kiện kết thúc
        sep()
        all_orders_done = (n_ord_total > 0 and n_ord_done == n_ord_total) or (phase.upper() == "COMPLETED")
        no_active_work  = (n_delivering == 0 and n_heading == 0 and n_at_wh == 0) and n_delivered > 0
        finish_delivery = all_orders_done or no_active_work
        finish_incident = seen_incidents >= REQUIRED

        di = f"{GRN}✅{R}" if finish_delivery else f"{RED}⏳{R}"
        ii = f"{GRN}✅{R}" if finish_incident else f"{YEL}⏳ {len(seen_incidents)}/5{R}"
        print(f"  {B}ĐIỀU KIỆN KẾT THÚC:{R}")
        print(f"    {di}  Tất cả đơn có thể giao đã xong")
        print(f"    {ii}  Đủ 5 sự cố đã biểu diễn")

        if finish_delivery and finish_incident:
            print()
            print(f"  {GRN}{B}🎉 DEMO HOÀN TẤT — Tất cả điều kiện đã thỏa mãn!{R}")
            sep("═")
            break

        print()
        print(f"  {DIM}Ctrl+C để dừng  |  Cập nhật sau 2 giây...{R}")

        time.sleep(2)


if __name__ == "__main__":
    main()