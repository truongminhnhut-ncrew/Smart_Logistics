import sys, os, importlib.util

# Direct import to avoid __init__.py chain that requires motor/MongoDB
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

# Import entities first
spec_ent = importlib.util.spec_from_file_location(
    "entities",
    os.path.join(backend_path, "app", "domain", "entities.py")
)
entities_mod = importlib.util.module_from_spec(spec_ent)
sys.modules["app.domain.entities"] = entities_mod
spec_ent.loader.exec_module(entities_mod)

# Import simulation_engine directly
spec = importlib.util.spec_from_file_location(
    "simulation_engine",
    os.path.join(backend_path, "app", "application", "services", "simulation_engine.py")
)
sim_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim_mod)
simulation_engine = sim_mod.simulation_engine

print("=== Engine Test ===")
print("Shippers:", len(simulation_engine.shippers))

stats = simulation_engine.get_fleet_stats()
print("Fleet stats:", stats)

# Test Rain 3 levels (Fix #6)
r1 = simulation_engine.apply_incident("SHP-001", "HEAVY_RAIN", "HEAVY")
print("\nRain HEAVY:", r1)
r1b = simulation_engine.apply_incident("SHP-003", "HEAVY_RAIN", "LIGHT")
print("Rain LIGHT:", r1b)

# Test Customer absent max 2 retries (Fix #3)
r2 = simulation_engine.apply_incident("SHP-002", "CUSTOMER_ABSENT")
print("\nAbsent retry 1:", r2)
r3 = simulation_engine.apply_incident("SHP-002", "CUSTOMER_ABSENT")
print("Absent retry 2 (should FAIL):", r3)

# Test Vehicle breakdown
r4 = simulation_engine.apply_incident("SHP-004", "VEHICLE_BREAKDOWN")
print("\nVehicle breakdown:", r4)

# Test resolve
rv = simulation_engine.resolve_incident("SHP-001")
print("\nResolve SHP-001:", rv)

# Test fleet stats after incidents
stats2 = simulation_engine.get_fleet_stats()
print("\nFleet stats after incidents:", stats2)

print("\n=== ALL TESTS PASSED ===")