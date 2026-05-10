# Backend Flow — Smart Logistics

This document describes the backend runtime flow, where to find each component in the repository, and how the 9‑step GPS processing maps to source files.

## High-level flow

1. WebSocket /ws/ingest or HTTP API receives incoming GPS payloads (simulator or device).
2. Presentation layer hands the raw payload to the Application layer (SimulationEngine / GPS processor).
3. Application layer validates, enriches, computes speed/heading/ETA, and persists events.
4. Infrastructure layer performs DB writes (MongoDB), publishes/consumes Kafka messages, uses Redis for cache, calls routing (in-memory graph or OSRM).
5. Presentation layer broadcasts updates via WebSocket to frontend clients.

## Important files and locations

- Entrypoint: backend/app/main.py
- Routers (presentation): backend/app/presentation/api/routers/
  - shippers.py, orders.py, dashboard.py
- WebSocket manager/handlers: backend/app/presentation/websocket/ (or presentation/websocket in repo)
- Application services: backend/app/application/services/
  - simulation_engine.py — SimulationEngine, GPS pipeline orchestration
  - gps_processor.py (if present) — lower-level pipeline step helpers
  - order_service.py — order lifecycle and ETA helpers
  - alert_service.py — decision rules and alert persistence
- Domain entities: backend/app/domain/ (entities, value objects)
- Infrastructure:
  - MongoDB repositories: backend/app/infrastructure/repositories/
  - Kafka producer/consumer: backend/app/infrastructure/kafka/
  - Redis cache wrapper: backend/app/infrastructure/cache/redis_cache.py
  - Routing: backend/app/infrastructure/routing/
    - routing_graph.py — in-memory graph + A* routing
    - osrm_client.py — public OSRM fallback route fetch
- Simulator generator: backend/data_generator/simulate.py

## 9-step GPS processing → source mapping

The conceptual 9 steps and where they are implemented:

1. VALIDATE
   - Description: sanity checks (lat/lon ranges, speed limits, shipper_id)
   - Likely implemented in: simulation_engine.py -> process_gps_event() or gps_processor.validate()

2. CREATE TRACKING EVENT
   - Create append-only TrackingEvent object (UUID, timestamp)
   - Implemented in: domain entities + simulation_engine/gps_processor

3. CALCULATE SPEED & HEADING
   - Haversine formula, time delta based speed; bearing calculation for heading
   - Implemented in: gps_processor.calculate_speed_heading() or utility functions under backend/app/utils/

4. INTERPOLATE (LINEAR SMOOTHING)
   - Smooth GPS between previous and current points
   - Implemented in: gps_processor.interpolate() or simulation_engine helper

5. FETCH & COMPUTE ETA
   - Query order_service for assigned order; compute remaining distance (routing_graph / OSRM) and ETA.
   - Implemented in: order_service.get_active_order(), routing_graph.get_route_distance(), osrm_client.fetch_route()

6. SAVE TRACKING EVENT (Append-only)
   - Insert into tracking_events collection (MongoDB) — use repository pattern
   - Implemented in: infrastructure/repositories/tracking_repository.py

7. CASCADE UPDATE (atomic-ish)
   - Update shippers collection (current_lat/lon, status, last_ping), update orders collection (eta/status)
   - Implemented in: shipper_repository.update(), order_repository.update()
   - Note: Look for transactions or two-phase patterns if using multi-doc updates

8. WEBSOCKET BROADCAST
   - Broadcast normalized payload to all connected clients
   - Implemented in: presentation.websocket.manager.broadcast() / router websocket handlers

9. DECISION ENGINE (alerts)
   - Evaluate rules (offline > timeout, ETA delay thresholds, stationary alerts) and persist alerts
   - Implemented in: alert_service.evaluate() and infrastructure repositories for alerts collection

## Routing behavior (short summary)

- Primary: in-memory routing graph (routing_graph.py) using A*/Dijkstra for local offline routes (fast).
- Fallback: OSRM public API (osrm_client.py) when in-memory graph fails or route missing.
- Look for functions named: get_route(), get_node_coordinate(), get_route_geometry()

## Runtime notes and known issues

- Check simulation_engine.py: backend logs previously showed an IndentationError in simulation_engine.py around line ~269. If the backend fails to import, inspect that file for stray indentation or incomplete dict/brace.
- When debugging routing issues, verify OSRM calls are reachable (router.project-osrm.org) or the code includes a fallback.
- To inspect logs inside Docker Compose:
  - docker compose logs backend --tail=200
  - If running native:
    - uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Troubleshooting checklist

- Import error / IndentationError on startup:
  - Open backend/app/application/services/simulation_engine.py and search for syntax/indentation problems (unclosed braces, extra indentation).
- WebSocket not receiving messages:
  - Verify simulator connects to ws://backend:8000/ws/ingest
  - Check broker topic: gps_stream on Kafka
- Tracking events missing in DB:
  - Check tracking_events collection indexes and TTL scripts (scripts/ or initialization files)
  - Inspect repository insert errors in backend logs
- Routing returns no route:
  - Confirm routing_graph built at startup or OSRM reachable; check logs indicating routing_graph initialization

## Developer quick links (file references)
- Simulator entrypoint: backend/data_generator/simulate.py
- Simulation engine: backend/app/application/services/simulation_engine.py
- Routing graph: backend/app/infrastructure/routing/routing_graph.py
- OSRM client: backend/app/infrastructure/routing/osrm_client.py
- Websocket manager: backend/app/presentation/websocket/manager.py (or handlers.py)
- Repositories: backend/app/infrastructure/repositories/

---

If you want, I can now:
- Create a complementary FRONTEND_FLOW.md that maps React components/hooks to the data flow, or
- Generate a short Vietnamese QUICK-START guide extracted from SETUP.md.