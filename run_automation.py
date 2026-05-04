"""
Smart Logistics - Automation Test Script
Khởi động Backend + Frontend, sau đó chạy Playwright automation.
"""
import subprocess
import time
import sys
import os
import requests

from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def wait_for_server(url, name, timeout=60):
    """Poll URL cho đến khi server sẵn sàng."""
    print(f"  ⏳ Chờ {name} sẵn sàng tại {url}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=3)
            print(f"  ✅ {name} đã sẵn sàng! (HTTP {r.status_code})")
            return True
        except Exception:
            time.sleep(2)
    print(f"  ❌ {name} không khởi động trong {timeout}s")
    return False


def start_backend():
    print("\n[1/2] Khởi động Backend (FastAPI port 8000)...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    return proc


def start_frontend():
    print("[2/2] Khởi động Frontend (Vite port 3000)...")
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )
    return proc


def run_playwright_tests():
    print("\n" + "=" * 60)
    print("  PLAYWRIGHT AUTOMATION TEST")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=600)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        screenshots = []

        def snap(name):
            path = os.path.join(BASE_DIR, f"screenshot_{name}.png")
            page.screenshot(path=path)
            screenshots.append(path)
            print(f"  📸 {path}")

        # ── TEST 1: Tải trang chính ──────────────────────────────────────
        print("\n[TEST 1] Mở trang http://localhost:3000")
        page.goto("http://localhost:3000", wait_until="load", timeout=60000)
        time.sleep(2)
        snap("01_homepage")
        print("  ✅ Trang tải thành công")

        # ── Chờ heading Shippers ─────────────────────────────────────────
        try:
            h = page.locator("h2").filter(has_text="Shippers").first
            h.wait_for(state="visible", timeout=10000)
            print(f"  ✅ Heading: {h.text_content()}")
        except Exception:
            print("  ⚠️  Heading 'Shippers' chưa hiển thị")

        # ── TEST 2: Bắt đầu simulation ───────────────────────────────────
        print("\n[TEST 2] Bắt đầu Simulation")
        btn_start = page.locator("button").filter(has_text="Bắt đầu giao hàng")
        if btn_start.count() > 0:
            btn_start.first.click()
            time.sleep(2)
            snap("02_started")
            print("  ✅ Đã click 'Bắt đầu giao hàng'")
        else:
            print("  ⚠️  Nút 'Bắt đầu giao hàng' không thấy (có thể đang ở phase khác)")

        # ── TEST 3: Tìm 3 shipper gần nhất ──────────────────────────────
        print("\n[TEST 3] Tìm 3 shipper gần kho nhất")
        btn_nearest = page.locator("button").filter(has_text="Tìm 3 shipper")
        try:
            btn_nearest.first.wait_for(state="visible", timeout=5000)
            btn_nearest.first.click()
            time.sleep(3)
            snap("03_nearest")
            print("  ✅ Đã tìm shipper gần nhất")
        except Exception:
            print("  ⚠️  Nút tìm shipper chưa hiển thị")

        # ── TEST 4: Dispatch to Warehouse ────────────────────────────────
        print("\n[TEST 4] Dispatch shippers")
        btn_dispatch = page.locator("button").filter(has_text="Dispatch")
        try:
            btn_dispatch.first.wait_for(state="visible", timeout=5000)
            btn_dispatch.first.click()
            time.sleep(3)
            snap("04_dispatching")
            print("  ✅ Đã dispatch")
        except Exception:
            print("  ⚠️  Nút Dispatch chưa hiển thị")

        # ── TEST 5: Chọn shipper đầu tiên ────────────────────────────────
        print("\n[TEST 5] Chọn shipper đầu tiên")
        items = page.locator("div").filter(has_text="SHIPPER-")
        if items.count() > 0:
            items.first.click()
            time.sleep(2)
            snap("05_shipper_detail")
            print("  ✅ Đã chọn shipper")
        else:
            print("  ⚠️  Không tìm thấy shipper item")

        # ── TEST 6: Tab Stats / Dashboard ───────────────────────────────
        print("\n[TEST 6] Xem Dashboard / Stats")
        btn_stats = page.locator("button").filter(has_text="Stats")
        try:
            btn_stats.first.wait_for(state="visible", timeout=5000)
            btn_stats.first.click()
            time.sleep(2)
            snap("06_dashboard")
            print("  ✅ Đã mở tab Stats")
        except Exception:
            print("  ⚠️  Tab Stats không tìm thấy")

        # ── TEST 7: IncidentPanel ────────────────────────────────────────
        print("\n[TEST 7] Kiểm tra IncidentPanel")
        btn_details = page.locator("button").filter(has_text="Details")
        if btn_details.count() > 0:
            btn_details.first.click()
            time.sleep(1)

        for inc in ["HEAVY_RAIN", "TRAFFIC_JAM", "VEHICLE_BREAKDOWN", "ROAD_BLOCKED", "LOST_CONNECTION"]:
            el = page.locator("button").filter(has_text=inc)
            status = "✅" if el.count() > 0 and el.first.is_visible() else "⚠️ "
            print(f"  {status} Nút sự cố '{inc}'")
        snap("07_incident_panel")

        # ── TEST 8: Chờ delivery modal ───────────────────────────────────
        print("\n[TEST 8] Chờ shippers về Warehouse (tối đa 30s)")
        try:
            page.locator("text=All shippers arrived").wait_for(state="visible", timeout=30000)
            snap("08_delivery_modal")
            print("  ✅ DeliveryModal xuất hiện!")
        except Exception:
            print("  ⚠️  DeliveryModal chưa xuất hiện (bình thường nếu chưa dispatch)")

        # ── TEST 9: Reset ────────────────────────────────────────────────
        print("\n[TEST 9] Reset Simulation")
        btn_reset = page.locator("button").filter(has_text="Reset")
        if btn_reset.count() > 0:
            btn_reset.first.click()
            time.sleep(2)
            snap("09_reset")
            print("  ✅ Đã reset")
        else:
            print("  ⚠️  Nút Reset chưa hiển thị")

        snap("10_final")
        print("\n✅ Hoàn thành tất cả tests!")
        print(f"📂 {len(screenshots)} screenshots đã lưu tại: {BASE_DIR}")
        print("\nTrình duyệt đóng sau 5 giây...")
        time.sleep(5)
        browser.close()


def main():
    backend_proc = None
    frontend_proc = None

    try:
        backend_proc = start_backend()
        frontend_proc = start_frontend()

        # Chờ cả hai server sẵn sàng
        be_ok = wait_for_server("http://localhost:8000/health", "Backend", timeout=60)
        fe_ok = wait_for_server("http://localhost:3000", "Frontend", timeout=90)

        if not fe_ok:
            print("\n❌ Frontend không khởi động. Kiểm tra lỗi bên dưới:")
            # In ra stdout của frontend process (nếu có)
            if frontend_proc and frontend_proc.stdout:
                for line in frontend_proc.stdout:
                    print("  FE:", line.rstrip())
                    if "error" in line.lower():
                        break
            return

        run_playwright_tests()

    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n=> Tắt Backend và Frontend...")
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        print("✅ Xong!")


if __name__ == "__main__":
    main()