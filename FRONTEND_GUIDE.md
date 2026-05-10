# Frontend Development Guide

## Frontend Overview

The frontend is a modern web application built with React/Next.js, providing an intuitive dashboard for real-time logistics tracking.

## Technology Stack

- **Framework**: React 18 / Next.js
- **Language**: JavaScript / TypeScript
- **Styling**: CSS / Tailwind CSS / Material-UI
- **State Management**: Redux / Context API / Zustand
- **HTTP Client**: Axios / Fetch API
- **Real-time**: WebSocket
- **Map**: Leaflet.js
- **Build Tool**: Vite
- **Package Manager**: npm / yarn

## Folder Structure

```
frontend/
├── src/
│   ├── components/              # React components
│   │   ├── TopBar.jsx           # Header
│   │   ├── ShipperList.jsx      # Left panel (250px)
│   │   ├── MapView.jsx          # Center map (Leaflet)
│   │   ├── RightPanel.jsx       # Right panel (272px)
│   │   ├── Dashboard.jsx        # Stats dashboard
│   │   ├── common/              # Shared components
│   │   ├── forms/               # Form components
│   │   └── modals/              # Modal dialogs
│   ├── hooks/                   # Custom React hooks
│   │   ├── useWebSocket.js      # WebSocket connection
│   │   ├── useShippers.js       # Shipper state
│   │   ├── useFetch.js          # Data fetching
│   │   └── useAuth.js           # Authentication
│   ├── services/                # API communication
│   │   ├── api.js               # REST API client
│   │   └── websocket.js         # WebSocket service
│   ├── styles/                  # Global styles
│   │   ├── theme.css            # CSS variables
│   │   ├── layout.css           # Layout styles
│   │   └── responsive.css       # Responsive design
│   ├── utils/                   # Utility functions
│   │   ├── formatters.js        # Data formatting
│   │   └── constants.js         # App constants
│   ├── App.jsx                  # Root component
│   └── main.jsx                 # Entry point
├── public/                      # Static assets
│   ├── images/
│   └── icons/
├── index.html                   # HTML template
├── package.json                 # Dependencies
├── vite.config.js               # Vite configuration
├── Dockerfile
└── .env
```

## Core Modules

### 1. Components (`src/components/`)

**TopBar.jsx**
- Logo and branding
- Status indicators
- Clock/time display
- Navigation buttons

**ShipperList.jsx**
- Left panel (fixed 250px width)
- List of 100 shippers
- Search and filter
- Status color indicators
- Click to select shipper

**MapView.jsx**
- Center panel (flex)
- Leaflet map integration
- Shipper markers/pins
- Tracking trails
- Map controls

**RightPanel.jsx**
- Right panel (fixed 272px)
- Selected shipper details
- Order information
- ETA and status
- Contact info

**Dashboard.jsx**
- Statistics cards
- Active shipper count
- Total distance traveled
- Top performers list
- Performance metrics

### 2. Hooks (`src/hooks/`)

**useWebSocket.js**
```javascript
const { shippers, connected } = useWebSocket(wsUrl)
// Auto-reconnect, handle disconnect
```

**useShippers.js**
```javascript
const { shippers, selected, selectShipper } = useShippers()
// State management for 100 shippers
```

**useFetch.js**
```javascript
const { data, loading, error } = useFetch(url, options)
// Generic data fetching hook
```

### 3. Services (`src/services/`)

**api.js**
```javascript
// Shipper API
getShippers()
getShipperById(id)
getShipperHistory(id)

// Order API
getOrders()
createOrder(data)
assignOrder(orderId, shipperId)
completeOrder(orderId)

// Dashboard API
getStats()
getFleetStats()
getTrackingEvents()
```

**websocket.js**
```javascript
// WebSocket connection
connect(url)
disconnect()
on(event, callback)
emit(event, data)
```

### 4. Styles (`src/styles/`)

**theme.css** - CSS Variables
```css
--bg: #08090b           /* Main background */
--bg2: #0f1115          /* Panels */
--bg3: #161a20          /* Hover states */
--border: #1c2028
--text: #cdd6e0         /* Main text */
--text2: #5f7080        /* Secondary text */
--green: #00e5a0        /* Accent (DELIVERING) */
--amber: #f5a623        /* Warning (IDLE) */
--red: #ff4757          /* Danger (OFFLINE) */
--blue: #4a9eff         /* Info (AVAILABLE) */
```

## UI Layout

```
┌────────────────────────────────────────────────┐
│ TopBar (46px)                                  │
├─────────────┬─────────────────────┬────────────┤
│ ShipperList │    MapView          │ RightPanel │
│   250px     │    (flex: 1)         │   272px    │
│             │                     │            │
│  - Scroll   │  - Leaflet map      │ - Detail   │
│  - Search   │  - Markers          │ - Order    │
│  - Filter   │  - Trails           │ - Stats    │
└─────────────┴─────────────────────┴────────────┘
```

## API Integration

### Configuration
```javascript
// src/config.js
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'
export const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws'
```

### API Client Setup
```javascript
// src/services/api.js
import axios from 'axios'

const client = axios.create({
  baseURL: API_BASE_URL,
})

client.interceptors.response.use(
  response => response.data,
  error => Promise.reject(error)
)
```

### WebSocket Integration
```javascript
// src/hooks/useWebSocket.js
const ws = new WebSocket(WS_URL)

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  updateShipper(message)
}
```

## Shipper Status Colors

| Status | Color | Indicator |
|--------|-------|-----------|
| DELIVERING | `--green` (#00e5a0) | 🟢 Live |
| IDLE | `--amber` (#f5a623) | 🟡 Idle |
| OFFLINE | `--red` (#ff4757) | 🔴 Lost |
| AVAILABLE | `--blue` (#4a9eff) | 🔵 Available |
| ASSIGNED | `--purple` | 🟣 Assigned |

## Running the Frontend

### Development Mode
```bash
cd frontend
npm install
npm run dev

# Runs on http://localhost:3000
```

### Build for Production
```bash
npm run build
npm run preview
```

### Docker
```bash
docker compose up frontend
```

## Environment Configuration

Create `.env.local`:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development
```

## Testing

```bash
# Run tests
npm test

# With coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

## Performance Optimization

- Code splitting and lazy loading
- Memoization with `React.memo`
- Virtual scrolling for large lists
- Leaflet marker update (no re-render)
- Image optimization

## Debugging

### Browser DevTools
- React DevTools extension
- Network tab for API calls
- WebSocket inspection

### Common Issues

**Q: Map not showing markers**  
A: Check WebSocket connection in Network tab

**Q: "0/100 online" shippers**  
A: Simulator may not be running

**Q: Slow performance**  
A: Check React DevTools Profiler

## Key Features

### Real-time Tracking
- Live GPS updates via WebSocket
- Marker position updates
- No page refresh needed

### Interactive Map
- Leaflet.js with OpenStreetMap
- Zoom and pan controls
- Marker clustering
- Route visualization

### Dashboard Statistics
- Active shipper count
- Total distance traveled
- Top performers
- Performance metrics

### Responsive Design
- Mobile-friendly layout
- Tablet optimization
- Desktop full-screen

For setup instructions, see [SETUP.md](SETUP.md)
For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)
For backend guide, see [BACKEND_GUIDE.md](BACKEND_GUIDE.md)
For API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)