use('shiptrack');

// Delete existing shippers
db.shippers.deleteMany({});

// Seed 100 shippers
const shippers = [];
for (let i = 1; i <= 100; i++) {
  shippers.push({
    shipper_id: 'SHP-' + String(i).padStart(3, '0'),
    name: 'Shipper ' + i,
    phone_number: '090' + String(Math.floor(Math.random()*1000000)).padStart(6, '0'),
    vehicle_type: i % 2 === 0 ? 'car' : 'motorcycle',
    vehicle_plate: '51' + String(i).padStart(5, '0'),
    current_lat: 10.65 + Math.random() * 0.25,
    current_lon: 106.55 + Math.random() * 0.30,
    current_speed_kmh: 0,
    heading: 0,
    current_status: 'AVAILABLE',
    signal_status: 'ONLINE',
    completed_count: 0,
    total_distance_km: 0,
    last_ping_at: new Date(),
    created_at: new Date(),
    updated_at: new Date()
  });
}

db.shippers.insertMany(shippers);
console.log('✅ Inserted ' + db.shippers.countDocuments() + ' shippers');
