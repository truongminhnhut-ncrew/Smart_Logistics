// MongoDB initialization script
// Runs automatically on MongoDB startup in Docker

const db = db.getSiblingDB('shiptrack');

// ── CREATE COLLECTIONS ──────────────────────
db.createCollection('shippers');
db.createCollection('orders');
db.createCollection('tracking_events');
db.createCollection('warehouses');

// ── CREATE INDEXES ──────────────────────────

// Shippers: PK on shipper_id
db.shippers.createIndex({ shipper_id: 1 }, { unique: true });
db.shippers.createIndex({ signal_status: 1 });
db.shippers.createIndex({ current_status: 1 });
db.shippers.createIndex({ last_ping_at: 1 });

// Orders: PK on order_id
db.orders.createIndex({ order_id: 1 }, { unique: true });
db.orders.createIndex({ assigned_shipper_id: 1 });
db.orders.createIndex({ current_status: 1 });
db.orders.createIndex({ warehouse_id: 1 });
db.orders.createIndex({ promised_delivery_at: 1 });

// TrackingEvents: Append-only with TTL
db.tracking_events.createIndex({ shipper_id: 1, timestamp: -1 });
db.tracking_events.createIndex({ order_id: 1 });
// TTL index: auto-delete after 7 days (timestamp only - no duplicate!)
db.tracking_events.createIndex(
  { timestamp: 1 },
  { expireAfterSeconds: 604800 }  // 7 days
);

// Warehouses: PK on warehouse_id
db.warehouses.createIndex({ warehouse_id: 1 }, { unique: true });

// ── SEED WAREHOUSE DATA ──────────────────────
db.warehouses.insertMany([
  {
    warehouse_id: 'WH-HCMC-01',
    name: 'HCMC Central Warehouse',
    lat: 10.776930,
    lon: 106.700981,
    address: 'Landmark 81, District 1, HCMC',
    phone_number: '0283827899',
    active_orders: 0,
    max_orders_pending: 100,
    created_at: new Date(),
    updated_at: new Date(),
  },
  {
    warehouse_id: 'WH-HN-01',
    name: 'Hanoi Warehouse',
    lat: 21.034733,
    lon: 105.804260,
    address: 'Hanoi, Vietnam',
    phone_number: '0243827899',
    active_orders: 0,
    max_orders_pending: 100,
    created_at: new Date(),
    updated_at: new Date(),
  },
]);

print('✅ ShipTrack database initialized successfully!');
print('  - Collections: shippers, orders, tracking_events, warehouses');
print('  - Indexes created on all PK fields');
print('  - TTL index (7 days) on tracking_events');
print('  - Seed data: 2 warehouses inserted');
