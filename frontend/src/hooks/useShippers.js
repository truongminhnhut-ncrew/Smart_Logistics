/**
 * hooks/useShippers.js — State management for 30 shippers + simulation
 */

import { useState, useCallback, useRef } from 'react'

export const useShippers = () => {
  const [shippers, setShippers] = useState(new Map())
  const [selectedShipperId, setSelectedShipperId] = useState(null)
  const [simulationPhase, setSimulationPhase] = useState('IDLE')
  const [dispatchedIds, setDispatchedIds] = useState([])
  const [arrivedAtWarehouse, setArrivedAtWarehouse] = useState([])
  const deliveryHistoryRef = useRef(new Map()) // shipper_id -> completed_count

  // Handle bulk GPS update (all shippers at once)
  const handleBulkUpdate = useCallback((data) => {
    if (!data.shippers) return
    setShippers(prev => {
      const updated = new Map(prev)
      data.shippers.forEach(s => {
        const existing = updated.get(s.shipper_id) || {}
        const completedCount = deliveryHistoryRef.current.get(s.shipper_id) || existing.completed_orders_count || 0
        updated.set(s.shipper_id, { ...existing, ...s, completed_orders_count: completedCount })
      })
      return updated
    })
    if (data.phase) setSimulationPhase(data.phase)
  }, [])

  // Handle single shipper GPS update
  const handleGpsUpdate = useCallback((data) => {
    if (!data.shipper_id) return
    setShippers(prev => {
      const updated = new Map(prev)
      const existing = updated.get(data.shipper_id) || {}
      updated.set(data.shipper_id, { ...existing, ...data })
      return updated
    })
  }, [])

  // Handle initial state from WebSocket connect
  const handleInitialState = useCallback((data) => {
    if (!data.shippers) return
    const map = new Map()
    data.shippers.forEach(s => {
      const completedCount = deliveryHistoryRef.current.get(s.shipper_id) || s.completed_orders_count || 0
      map.set(s.shipper_id, { ...s, completed_orders_count: completedCount })
    })
    setShippers(map)
    if (data.phase) setSimulationPhase(data.phase)
  }, [])

  // Handle dispatch started
  const handleDispatch = useCallback((data) => {
    if (data.shipper_ids) setDispatchedIds(data.shipper_ids)
    setSimulationPhase('DISPATCHING')
  }, [])

  // Handle shipper arrived at warehouse
  const handleShipperArrived = useCallback((data) => {
    if (data.arrived_so_far) setArrivedAtWarehouse(data.arrived_so_far)
    setShippers(prev => {
      const updated = new Map(prev)
      const s = updated.get(data.shipper_id)
      if (s) updated.set(data.shipper_id, { ...s, status: 'AT_WAREHOUSE' })
      return updated
    })
  }, [])

  const handleAllArrived = useCallback(() => {
    setSimulationPhase('WAITING_FOR_ORDER')
  }, [])

  const handleDeliveryAssigned = useCallback((data) => {
    setSimulationPhase('DELIVERING')
    setShippers(prev => {
      const updated = new Map(prev)
      const s = updated.get(data.shipper_id)
      if (s) {
        updated.set(data.shipper_id, {
          ...s,
          status: 'DELIVERING',
          order_id: data.order_id,
          current_order_dest_lat: data.dest_lat ?? s.current_order_dest_lat ?? null,
          current_order_dest_lon: data.dest_lon ?? s.current_order_dest_lon ?? null,
          current_order_destination_text: data.destination_text ?? s.current_order_destination_text ?? null,
        })
      }
      return updated
    })
  }, [])

  const handleDeliveryCompleted = useCallback((data) => {
    setShippers(prev => {
      const updated = new Map(prev)
      const s = updated.get(data.shipper_id)
      if (s) {
        const oldCount = deliveryHistoryRef.current.get(data.shipper_id) || s.completed_orders_count || 0
        const newCount = oldCount + 1
        deliveryHistoryRef.current.set(data.shipper_id, newCount)

        updated.set(data.shipper_id, {
          ...s,
          status: 'DELIVERED',
          order_id: null,
          completed_orders_count: newCount,
          last_completed_order_id: data.order_id || s.order_id || null,
        })
      }
      return updated
    })
  }, [])

  const handleSimulationCompleted = useCallback(() => {
    setSimulationPhase('COMPLETED')
  }, [])

  const handleReset = useCallback(() => {
    setSimulationPhase('IDLE')
    setDispatchedIds([])
    setArrivedAtWarehouse([])
    deliveryHistoryRef.current = new Map()
  }, [])

  const selectedShipper = selectedShipperId ? shippers.get(selectedShipperId) : null
  const shipperList = Array.from(shippers.values())

  return {
    shippers,
    shipperList,
    selectedShipperId,
    setSelectedShipperId,
    selectedShipper,
    simulationPhase,
    setSimulationPhase,
    dispatchedIds,
    setDispatchedIds,
    arrivedAtWarehouse,
    // Event handlers for WebSocket messages
    handleBulkUpdate,
    handleGpsUpdate,
    handleInitialState,
    handleDispatch,
    handleShipperArrived,
    handleAllArrived,
    handleDeliveryAssigned,
    handleDeliveryCompleted,
    handleSimulationCompleted,
    handleReset,
  }
}
