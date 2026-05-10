# Smart Logistics API Documentation

Complete REST API reference for Smart Logistics system.

## Base Configuration

- **Base URL**: `http://localhost:8000` (development) | `https://api.smartlogistics.com` (production)
- **API Version**: v1
- **Content-Type**: `application/json`
- **Authentication**: JWT Bearer Token

## Authentication Endpoints

### Register User
```http
POST /api/auth/register HTTP/1.1
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "role": "dispatcher"
}

Response (201 Created):
{
  "id": "user-123",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "dispatcher",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Login
```http
POST /api/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-123",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "dispatcher"
  }
}
```

### Logout
```http
POST /api/auth/logout HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "message": "Successfully logged out"
}
```

### Get Current User
```http
GET /api/auth/me HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "user-123",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "dispatcher",
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Shipment Endpoints

### List Shipments
```http
GET /api/shipments?status=in-transit&skip=0&limit=10 HTTP/1.1
Authorization: Bearer {token}

Query Parameters:
- status: pending | in-transit | delivered | cancelled
- skip: number (pagination offset)
- limit: number (pagination limit, max 100)
- sort: field name
- order: asc | desc

Response (200 OK):
{
  "items": [
    {
      "id": "ship-001",
      "user_id": "user-123",
      "origin": {
        "id": "loc-001",
        "latitude": 10.5,
        "longitude": 20.3,
        "address": "123 Main St, Ho Chi Minh"
      },
      "destination": {
        "id": "loc-002",
        "latitude": 11.2,
        "longitude": 21.1,
        "address": "456 Oak Ave, Hanoi"
      },
      "status": "in-transit",
      "vehicle_id": "vehicle-001",
      "weight": 5.5,
      "dimensions": {
        "length": 30,
        "width": 20,
        "height": 15
      },
      "priority": "high",
      "estimated_delivery": "2024-01-16T15:00:00Z",
      "actual_delivery": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 45,
  "skip": 0,
  "limit": 10
}
```

### Create Shipment
```http
POST /api/shipments HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "origin": {
    "latitude": 10.5,
    "longitude": 20.3,
    "address": "123 Main St"
  },
  "destination": {
    "latitude": 11.2,
    "longitude": 21.1,
    "address": "456 Oak Ave"
  },
  "weight": 5.5,
  "dimensions": {
    "length": 30,
    "width": 20,
    "height": 15
  },
  "priority": "high",
  "notes": "Fragile items - handle with care"
}

Response (201 Created):
{
  "id": "ship-001",
  "status": "pending",
  ...shipment object
}
```

### Get Shipment Details
```http
GET /api/shipments/{shipment_id} HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "ship-001",
  ...shipment object
}
```

### Update Shipment
```http
PUT /api/shipments/{shipment_id} HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "in-transit",
  "priority": "normal",
  "notes": "Updated notes"
}

Response (200 OK):
{
  "id": "ship-001",
  ...updated shipment object
}
```

### Delete Shipment
```http
DELETE /api/shipments/{shipment_id} HTTP/1.1
Authorization: Bearer {token}

Response (204 No Content)
```

### Get Shipment Status Timeline
```http
GET /api/shipments/{shipment_id}/status HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "shipment_id": "ship-001",
  "timeline": [
    {
      "status": "pending",
      "timestamp": "2024-01-15T10:30:00Z",
      "notes": "Shipment created"
    },
    {
      "status": "picked_up",
      "timestamp": "2024-01-15T11:00:00Z",
      "notes": "Picked up by vehicle v-001"
    },
    {
      "status": "in-transit",
      "timestamp": "2024-01-15T11:30:00Z",
      "notes": "On the way to destination"
    }
  ]
}
```

## Vehicle Endpoints

### List Vehicles
```http
GET /api/vehicles?status=available&skip=0&limit=10 HTTP/1.1
Authorization: Bearer {token}

Query Parameters:
- status: available | in-use | maintenance
- skip: pagination offset
- limit: pagination limit

Response (200 OK):
{
  "items": [
    {
      "id": "vehicle-001",
      "registration_number": "ABC-1234",
      "type": "van",
      "capacity": 100,
      "current_location": {
        "latitude": 10.567,
        "longitude": 20.456
      },
      "status": "in-use",
      "driver_id": "driver-001",
      "last_updated": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 15,
  "skip": 0,
  "limit": 10
}
```

### Create Vehicle
```http
POST /api/vehicles HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "registration_number": "ABC-1234",
  "type": "van",
  "capacity": 100,
  "driver_id": "driver-001"
}

Response (201 Created):
{
  "id": "vehicle-001",
  ...vehicle object
}
```

### Get Vehicle Details
```http
GET /api/vehicles/{vehicle_id} HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "vehicle-001",
  ...vehicle object
}
```

### Update Vehicle
```http
PUT /api/vehicles/{vehicle_id} HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "maintenance",
  "driver_id": "driver-002"
}

Response (200 OK):
{
  "id": "vehicle-001",
  ...updated vehicle object
}
```

### Get Vehicle Location History
```http
GET /api/vehicles/{vehicle_id}/location-history?start=2024-01-15&end=2024-01-16 HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "vehicle_id": "vehicle-001",
  "history": [
    {
      "latitude": 10.5,
      "longitude": 20.3,
      "timestamp": "2024-01-15T10:00:00Z"
    },
    ...
  ]
}
```

## Route Endpoints

### List Routes
```http
GET /api/routes?status=active&skip=0&limit=10 HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "items": [
    {
      "id": "route-001",
      "vehicle_id": "vehicle-001",
      "waypoints": [
        {
          "location_id": "loc-001",
          "latitude": 10.5,
          "longitude": 20.3,
          "order": 1
        },
        {
          "location_id": "loc-002",
          "latitude": 11.2,
          "longitude": 21.1,
          "order": 2
        }
      ],
      "distance": 150.5,
      "estimated_duration": 3600,
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 8,
  "skip": 0,
  "limit": 10
}
```

### Create Route
```http
POST /api/routes HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "vehicle_id": "vehicle-001",
  "waypoints": [
    {
      "location_id": "loc-001",
      "order": 1
    },
    {
      "location_id": "loc-002",
      "order": 2
    }
  ]
}

Response (201 Created):
{
  "id": "route-001",
  ...route object
}
```

### Optimize Route
```http
POST /api/routes/{route_id}/optimize HTTP/1.1
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "route-001",
  "optimized_waypoints": [...],
  "distance": 140.2,
  "estimated_duration": 3200
}
```

## Real-time WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws')

// Send authentication
ws.send(JSON.stringify({
  action: 'authenticate',
  token: 'your-jwt-token'
}))
```

### Subscribe to Events
```javascript
// Subscribe to shipment updates
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'shipments',
  filter: { status: 'in-transit' }
}))

// Subscribe to vehicle locations
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'vehicles',
  vehicle_ids: ['vehicle-001', 'vehicle-002']
}))
```

### Incoming Events
```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  
  // Shipment update
  if (message.event === 'shipment:updated') {
    console.log('Shipment updated:', message.data)
  }
  
  // Vehicle location update
  if (message.event === 'vehicle:location_updated') {
    console.log('Vehicle location:', message.data)
  }
  
  // New notification
  if (message.event === 'notification:new') {
    console.log('Notification:', message.data)
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": {
    "weight": "Must be a positive number"
  }
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Shipment not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "request_id": "req-12345"
}
```

## Rate Limiting

- **Limit**: 1000 requests per hour per user
- **Headers**:
  ```
  X-RateLimit-Limit: 1000
  X-RateLimit-Remaining: 999
  X-RateLimit-Reset: 1642204800
  ```

## Pagination

All list endpoints support pagination:
- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items to return (default: 10, max: 100)

Response includes:
- `items`: Array of results
- `total`: Total number of items
- `skip`: Current offset
- `limit`: Current limit

## Filtering & Sorting

Endpoints support query parameters for filtering and sorting:
- Status filters: `?status=pending&status=in-transit`
- Date ranges: `?created_after=2024-01-01&created_before=2024-01-31`
- Sorting: `?sort=created_at&order=desc`

For detailed setup instructions, see [SETUP.md](SETUP.md)
For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)