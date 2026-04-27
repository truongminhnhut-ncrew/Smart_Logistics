/**
 * hooks/useShippers.js — State management for 100 shippers
 *
 * Manages shipper data, updates GPS positions in real-time
 */

import { useState, useCallback } from 'react'

export const useShippers = () => {
  const [shippers, setShippers] = useState(new Map())
  const [selectedShipperId, setSelectedShipperId] = useState(null)

  // Update shipper GPS position from WebSocket
  const updateShipperLocation = useCallback((event) => {
    if (!event.shipper_id) return

    setShippers(prev => {
      const updated = new Map(prev)
      const shipper = updated.get(event.shipper_id) || {}

      updated.set(event.shipper_id, {
        ...shipper,
        shipper_id: event.shipper_id,
        current_lat: event.lat,
        current_lon: event.lon,
        lat: event.lat,
        lon: event.lon,
        current_speed_kmh: event.speed_kmh,
        speed_kmh: event.speed_kmh,
        heading: event.heading,
        signal_status: 'ONLINE',
        eta_minutes: event.eta_minutes,
        order_id: event.order_id,
        order_status: event.order_status,
        delay_minutes: event.delay_minutes,
        timestamp: event.timestamp,
      })

      return updated
    })
  }, [])

  // Set initial shippers list
  const setShippersList = useCallback((shippersList) => {
    const map = new Map()
    shippersList.forEach(s => {
      map.set(s.shipper_id, s)
    })
    setShippers(map)
  }, [])

  return {
    shippers,
    selectedShipperId,
    setSelectedShipperId,
    updateShipperLocation,
    setShippersList,
    shipper_list: Array.from(shippers.values()),
  }
}
