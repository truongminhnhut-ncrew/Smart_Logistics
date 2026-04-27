@app.post("/simulation/start-delivery")
async def start_delivery(db=Depends(get_db)):
    """Tìm top 3 shipper gần 02 Võ Oanh nhất và gọi về kho"""
    wh_lat, wh_lon = 10.803723, 106.711854
    shipper_repo = ShipperRepository(db)
    
    # Tìm shipper IDLE
    shippers = await shipper_repo.find_all()
    # Sắp xếp theo khoảng cách Haversine tới kho
    shippers.sort(key=lambda s: ((s['current_lat']-wh_lat)**2 + (s['current_lon']-wh_lon)**2))
    
    top_3 = shippers[:3]
    for s in top_3:
        await db.shippers.update_one(
            {"shipper_id": s["shipper_id"]},
            {"$set": {
                "current_status": "MOVING_TO_WH", 
                "target_lat": wh_lat, 
                "target_lon": wh_lon,
                "updated_at": datetime.utcnow()
            }}
        )
    
    return {"status": "success", "calling_shippers": [s["shipper_id"] for s in top_3]}

@app.post("/incidents")
async def create_incident(incident_data: dict, db=Depends(get_db)):
    """Đổ dữ liệu sự cố vào và phát thông báo khẩn cấp"""
    incident_data["status"] = "ACTIVE"
    incident_data["created_at"] = datetime.utcnow()
    if "incident_id" not in incident_data:
        incident_data["incident_id"] = f"INC-{int(datetime.utcnow().timestamp())}"
    
    await db.incidents.insert_one(incident_data)
    
    await ws_manager.broadcast({
        "type": "ALERT",
        "alert_type": incident_data.get("type", "GENERAL_ISSUE"),
        "shipper_id": incident_data.get("shipper_id"),
        "message": f"Sự cố mới: {incident_data.get('type')} tại shipper {incident_data.get('shipper_id')}",
        "data": incident_data
    })
    return {"status": "created"}

@app.patch("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, db=Depends(get_db)):
    """Nút 'Hết sự cố'"""
    await db.incidents.update_one(
        {"incident_id": incident_id},
        {"$set": {"status": "RESOLVED", "resolved_at": datetime.utcnow()}}
    )
    return {"status": "resolved"}