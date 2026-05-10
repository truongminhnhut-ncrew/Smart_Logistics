# Frontend Flow — Smart Logistics

This document maps the React frontend structure to the runtime data flow, lists important components/hooks, and gives quick dev-run instructions.

## High-level flow

1. Frontend connects to backend WebSocket: `ws://localhost:8000/ws` (for UI) and `ws://localhost:8000/ws/ingest` (simulator → ingest).
2. WebSocket messages are received by a custom hook (`useWebSocket`) and dispatched to state (Redux or Context).
3. UI components consume state and render:
   - Map (Leaflet) updates markers
   - Shipper list updates
   - Detail panel shows selected shipper & history
4. User actions (assign order, complete order) call REST API endpoints (`/orders`, `/shippers`) via frontend API client.
5. Real-time updates are driven by backend broadcasts; frontend reacts and re-renders accordingly.

## Project structure (important files)

```
frontend/
├── package.json
├── src/
│   ├── App.jsx                    # Root component
│   ├── main.jsx                   # App bootstrap
│   ├── components/
│   │   ├── MapView.jsx            # Leaflet map wrapper + marker logic
│   │   ├── ShipperList.jsx        # Left panel list of shippers
│   │   ├── RightPanel.jsx         # Details / order panel
│   │   └── Dashboard.jsx          # Stats & charts
│   ├── hooks/
│   │   └── useWebSocket.js        # WebSocket connection, reconnection logic
│   ├── services/
│   │   ├── api.js                 # REST API client (fetch / axios)
│   │   └── websocketService.js    # Optional wrapper over raw WebSocket
│   ├── store/                     # Redux (or Context) state management
│   │   ├── shippersSlice.js
│   │   └── store.js
│   └── utils/
│       └── geo.js                 # Haversine, bearing, interpolation helpers
└── vite.config.js
```

## Key components & responsibilities

- MapView.jsx
  - Initialize Leaflet map and tile layer
  - Maintain marker objects keyed by shipper id
  - Expose methods: setView, highlightShipper
  - On state change: update marker positions using marker.setLatLng()

- ShipperList.jsx
  - Shows list of shippers with status badges (DELIVERING, IDLE, OFFLINE)
  - Click selects shipper (dispatches to store)

- RightPanel.jsx
  - Shows selected shipper details, last N tracking events, assigned order
  - Buttons for actions (assign, mark complete) that call REST API

- Dashboard.jsx
  - Aggregated stats: active shippers, total km, top performers
  - Uses periodic polling or state-derived aggregates updated from WebSocket

## Hooks & State

- useWebSocket(url, onMessage)
  - Handles connection, automatic reconnect with backoff
  - Parses incoming JSON and calls onMessage(payload)

- Redux store (recommended)
  - shippers slice:
    - byId: { "SHP-001": { id, lat, lon, status, speed_kmh, last_ping } }
    - allIds: []
    - selected: current selected shipper
  - orders slice: cached order details
  - stats slice: aggregates updated from messages

## WebSocket message format (example)

```
{
  "event_id": "uuid-12345",
  "shipper_id": "SHP-001",
  "lat": 10.77695,
  "lon": 106.70095,
  "smooth_lat": 10.77691,
  "smooth_lon": 106.70093,
  "speed_kmh": 32.5,
  "heading": 45.3,
  "eta_minutes": 15,
  "delay_minutes": 2,
  "order_status": "IN_TRANSIT",
  "shipper_status": "DELIVERING",
  "signal_status": "ONLINE"
}
```

Frontend should normalize and store relevant fields for fast lookup.

## Dev & Run instructions (quick)

1. Install deps
   - cd frontend
   - npm install

2. Start dev server
   - npm run dev
   - Open http://localhost:3000

3. Build for production
   - npm run build
   - Serve dist with a static server or Docker image

4. When running with backend in Docker Compose, ensure:
   - CORS origins include `http://localhost:3000`
   - WebSocket URL points to backend host (ws://localhost:8000/ws)

## Error handling & common issues

- Blank UI / "0/100 online":
  - Ensure simulator is running: `docker compose logs simulator`
  - Check browser console for WebSocket errors (CORS, connection refused)
  - Confirm backend `ws` endpoint is reachable: `curl http://localhost:8000/health`

- Markers not updating:
  - Verify WebSocket payloads arrive in useWebSocket
  - Confirm MapView uses marker.setLatLng() rather than re-creating markers constantly
  - Check coordinate precision (use 6 decimal places)

## Performance tips

- Batch UI updates: debounce Redux updates when receiving many messages per second.
- Use Leaflet marker clusters only when many markers (1000+).
- Keep WebSocket message minimal — remove heavy fields or compress if needed.

## Where to extend / find code

- WebSocket hook: frontend/src/hooks/useWebSocket.js
- Map logic: frontend/src/components/MapView.jsx
- REST client: frontend/src/services/api.js
- State: frontend/src/store/

---

For a Vietnamese quick-start or a printed checklist, tell me and I will generate SMART_LOGISTICS/QUICK_START_VIET.md next.