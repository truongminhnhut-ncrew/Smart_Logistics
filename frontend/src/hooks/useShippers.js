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

  // Handle bulk GPS update (all shippers at once)
  const handleBulkUpdate = useCallback((data) => {
    if (!data.shippers) return
    setShippers(prev => {
      const updated = new Map(prev)
      data.shippers.forEach(s => {
        const existing = updated.get(s.shipper_id) || {}
        updated.set(s.shipper_id, { ...existing, ...s })
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
    data.shippers.forEach(s => map.set(s.shipper_id, s))
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
      if (s) updated.set(data.shipper_id, { ...s, status: 'DELIVERING', order_id: data.order_id })
      return updated
    })
  }, [])

  const handleDeliveryCompleted = useCallback((data) => {
    setShippers(prev => {
      const updated = new Map(prev)
      const s = updated.get(data.shipper_id)
      if (s) updated.set(data.shipper_id, { ...s, status: 'DELIVERED', order_id: null })
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
