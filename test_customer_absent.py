"""
Test CUSTOMER_ABSENT fix - không cần dependencies
"""
import sys
import math

# Mock objects
class VirtualShipper:
    def __init__(self, shipper_id, lat, lon):
        self.shipper_id = shipper_id
        self.lat = lat
        self.lon = lon
        self.status = "IDLE"
        self.order_id = None
        self.target_lat = None
        self.target_lon = None
        self.customer_absent_retries = 0
        self.pending_orders = []
        self.route_waypoints = []
        self.route_index = 0
        self.route_polyline = []

    def distance_to(self, lat, lon):
        """Haversine distance in km."""
        radius_km = 6371.0
        dlat = math.radians(lat - self.lat)
        dlon = math.radians(lon - self.lon)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(self.lat))
            * math.cos(math.radians(lat))
            * math.sin(dlon / 2) ** 2
        )
        return radius_km * 2 * math.asin(math.sqrt(a))

# Simulate engine
class TestEngine:
    def __init__(self):
        self.shippers = {}
        self._orders = {}

    def find_nearby_orders(self, shipper_id, exclude_order_id=None, radius_km=3.0):
        shipper = self.shippers.get(shipper_id)
        if not shipper:
            return []

        nearby = []
        for order_id, order_info in self._orders.items():
            if exclude_order_id and order_id == exclude_order_id:
                continue
            if order_info.get("shipper_id") and order_info["shipper_id"] != shipper_id:
                continue
            if order_info.get("status") in ("DELIVERED", "FAILED"):
                continue

            dest_lat = order_info.get("dest_lat")
            dest_lon = order_info.get("dest_lon")
            if dest_lat is None or dest_lon is None:
                continue

            dist_km = shipper.distance_to(dest_lat, dest_lon)
            if dist_km <= radius_km:
                nearby.append({
                    "order_id": order_id,
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon,
                    "distance_km": dist_km,
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

    def apply_incident_customer_absent(self, shipper_id):
        """Apply CUSTOMER_ABSENT - FIX VERSION"""
        shipper = self.shippers.get(shipper_id)
        if not shipper:
            return {"error": "Shipper not found"}

        shipper.customer_absent_retries += 1
        current_order = shipper.order_id
        current_dest = (shipper.target_lat, shipper.target_lon)

        CUSTOMER_ABSENT_MAX_RETRIES = 2

        if shipper.customer_absent_retries >= CUSTOMER_ABSENT_MAX_RETRIES:
            # Attempt 2: Đơn FAILED, shipper IDLE
            if current_order and current_order in self._orders:
                self._orders[current_order]["status"] = "FAILED"
            shipper.status = "IDLE"
            shipper.target_lat = None
            shipper.target_lon = None
            shipper.order_id = None
            shipper.route_waypoints = []
            shipper.route_index = 0
            shipper.route_polyline = []
            return {
                "shipper_id": shipper_id,
                "attempt": shipper.customer_absent_retries,
                "action": f"Attempt {shipper.customer_absent_retries}: Order FAILED, shipper IDLE",
                "status": shipper.status,
                "order_id": shipper.order_id
            }
        else:
            # Attempt 1: Tìm đơn gần 3km
            if current_order:
                self._orders[current_order]["status"] = "DELIVERY_FAILED_ATTEMPT_1"
                shipper.pending_orders.append({
                    "order_id": current_order,
                    "dest_lat": current_dest[0],
                    "dest_lon": current_dest[1],
                })

            nearby = self.find_nearby_orders(shipper_id, exclude_order_id=current_order, radius_km=3.0)

            if nearby:
                # Có đơn gần → gán shipper
                next_order = nearby[0]
                order_id = next_order["order_id"]
                dest_lat = next_order["dest_lat"]
                dest_lon = next_order["dest_lon"]

                shipper.status = "DELIVERING"
                shipper.target_lat = dest_lat
                shipper.target_lon = dest_lon
                shipper.order_id = order_id
                self._orders[order_id]["shipper_id"] = shipper_id

                return {
                    "shipper_id": shipper_id,
                    "attempt": shipper.customer_absent_retries,
                    "action": f"Attempt {shipper.customer_absent_retries}: Found nearby order {order_id} ({next_order['distance_km']:.1f}km away)",
                    "status": shipper.status,
                    "order_id": shipper.order_id,
                    "nearby_distance_km": next_order["distance_km"]
                }
            else:
                # Không có đơn gần → IDLE
                shipper.status = "IDLE"
                shipper.target_lat = None
                shipper.target_lon = None
                shipper.order_id = None
                shipper.route_waypoints = []
                shipper.route_index = 0
                shipper.route_polyline = []

                return {
                    "shipper_id": shipper_id,
                    "attempt": shipper.customer_absent_retries,
                    "action": f"Attempt {shipper.customer_absent_retries}: No nearby orders, shipper IDLE",
                    "status": shipper.status,
                    "order_id": shipper.order_id
                }

# Run tests
print("=" * 70)
print("[TEST] Customer Absent with Rerouting (Attempt 1 finds nearby order)")
print("=" * 70)

engine = TestEngine()

# Setup: Create shipper + orders
shipper = VirtualShipper("SHP-001", 10.77695, 106.70095)
shipper.status = "DELIVERING"
shipper.order_id = "TEST-ORDER-1"
shipper.target_lat = 10.77900
shipper.target_lon = 106.70200

engine.shippers["SHP-001"] = shipper
engine._orders["TEST-ORDER-1"] = {
    "shipper_id": "SHP-001",
    "dest_lat": 10.77900,
    "dest_lon": 106.70200,
    "status": "IN_TRANSIT"
}

# Add nearby order (2km away)
engine._orders["TEST-ORDER-2"] = {
    "shipper_id": None,
    "dest_lat": 10.78000,
    "dest_lon": 106.70300,
    "status": "PENDING"
}

print("\n[1] Before incident:")
print(f"  Status: {shipper.status}")
print(f"  Order: {shipper.order_id}")
print(f"  Retries: {shipper.customer_absent_retries}")

print("\n[2] Applying CUSTOMER_ABSENT incident...")
result = engine.apply_incident_customer_absent("SHP-001")
print(f"  Action: {result['action']}")

print("\n[3] After incident:")
print(f"  Status: {shipper.status}")
print(f"  Order: {shipper.order_id}")
print(f"  Retries: {shipper.customer_absent_retries}")

print("\n[SUMMARY]")
print("=" * 70)
# Check assertions
tests_pass = True

# Test 1: Status should be DELIVERING (found nearby order)
if shipper.status != "DELIVERING":
    print(f"[FAIL] Status should be DELIVERING, got {shipper.status}")
    tests_pass = False
else:
    print(f"[PASS] Status = {shipper.status}")

# Test 2: Order should be TEST-ORDER-2 (the nearby order)
if shipper.order_id != "TEST-ORDER-2":
    print(f"[FAIL] Order should be TEST-ORDER-2, got {shipper.order_id}")
    tests_pass = False
else:
    print(f"[PASS] Order = {shipper.order_id}")

# Test 3: Retries should be 1
if shipper.customer_absent_retries != 1:
    print(f"[FAIL] Retries should be 1, got {shipper.customer_absent_retries}")
    tests_pass = False
else:
    print(f"[PASS] Retries = {shipper.customer_absent_retries}")

print("\n" + "=" * 70)
if tests_pass:
    print("[SUCCESS] ALL TESTS PASSED!")
else:
    print("[FAILED] SOME TESTS FAILED!")
print("=" * 70)

# Test 2: Attempt 2 (should fail completely)
print("\n\n[TEST 2] Customer Absent - Attempt 2 (max retries)")
print("=" * 70)

print("\n[1] Applying 2nd CUSTOMER_ABSENT incident...")
result2 = engine.apply_incident_customer_absent("SHP-001")
print(f"  Action: {result2['action']}")

print("\n[2] After 2nd incident:")
print(f"  Status: {shipper.status}")
print(f"  Order: {shipper.order_id}")
print(f"  Retries: {shipper.customer_absent_retries}")

print("\n[SUMMARY]")
print("=" * 70)
tests2_pass = True

if shipper.status != "IDLE":
    print(f"[FAIL] Status should be IDLE, got {shipper.status}")
    tests2_pass = False
else:
    print(f"[PASS] Status = {shipper.status}")

if shipper.order_id is not None:
    print(f"[FAIL] Order should be None, got {shipper.order_id}")
    tests2_pass = False
else:
    print(f"[PASS] Order = None")

if shipper.customer_absent_retries != 2:
    print(f"[FAIL] Retries should be 2, got {shipper.customer_absent_retries}")
    tests2_pass = False
else:
    print(f"[PASS] Retries = {shipper.customer_absent_retries}")

# Check if original order is in pending_orders
if len(shipper.pending_orders) > 0 and shipper.pending_orders[0]["order_id"] == "TEST-ORDER-1":
    print(f"[PASS] TEST-ORDER-1 in pending_orders (from attempt 1)")
else:
    print(f"[FAIL] TEST-ORDER-1 should be in pending_orders")
    tests2_pass = False

# Check if current order (TEST-ORDER-2) is FAILED
if engine._orders["TEST-ORDER-2"]["status"] == "FAILED":
    print(f"[PASS] TEST-ORDER-2 status = FAILED (current order on attempt 2)")
else:
    print(f"[FAIL] TEST-ORDER-2 should be FAILED, got {engine._orders['TEST-ORDER-2']['status']}")
    tests2_pass = False

print("\n" + "=" * 70)
if tests2_pass:
    print("[SUCCESS] ALL TESTS PASSED!")
else:
    print("[FAILED] SOME TESTS FAILED!")
print("=" * 70)
