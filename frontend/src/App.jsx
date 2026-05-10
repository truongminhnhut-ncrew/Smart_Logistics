/**
 * App.jsx — Main React application with simulation state machine
 */

import { useState, useEffect } from 'react'
import { TopBar } from './components/TopBar'
import { ShipperList } from './components/ShipperList'
import { MapView } from './components/MapView'
import { RightPanel } from './components/RightPanel'
import { Dashboard } from './components/Dashboard'
import { SimulationControls } from './components/SimulationControls'
import { DeliveryModal } from './components/DeliveryModal'
import { NotificationToast } from './components/NotificationToast'
import { AutoDemoPanel } from './components/AutoDemoPanel'

import { useWebSocket } from './hooks/useWebSocket'
import { useShippers } from './hooks/useShippers'
import { dashboardAPI, shippersAPI, simulationAPI } from './services/api'
import './styles/theme.css'

function App() {
  const [showDashboard, setShowDashboard] = useState(false)
  const [stats, setStats] = useState(null)
  const [activeIncident, setActiveIncident] = useState(null)
  const [systemAlert, setSystemAlert] = useState(null)
  const [customerNotice, setCustomerNotice] = useState(null)
  const [etaUpdate, setEtaUpdate] = useState(null)
  const [showDeliveryModal, setShowDeliveryModal] = useState(false)
  const [nearestShippers, setNearestShippers] = useState([])
  const [deliveryModalShipperIds, setDeliveryModalShipperIds] = useState([])
  const [demoScript, setDemoScript] = useState({
    step: 'Bước 0/9',
    text: 'Trạng thái ban đầu: tất cả shipper đứng yên trên bản đồ, ⏸️ Chờ lệnh.',
  })
  const [demoMapIncidents, setDemoMapIncidents] = useState({})

  const ws = useWebSocket()
  const { 
    shipperList, 
    selectedShipperId, 
    setSelectedShipperId, 
    selectedShipper,
    simulationPhase,
    dispatchedIds,
    arrivedAtWarehouse,
    handleInitialState,
    handleBulkUpdate,
    handleDispatch,
    handleShipperArrived,
    handleAllArrived,
    handleDeliveryAssigned,
    handleDeliveryCompleted,
    handleSimulationCompleted,
    handleReset
  } = useShippers()

  // Subscribe to WebSocket events
  useEffect(() => {
    console.log('[App] Initializing data and subscriptions...');
    
    // Fallback: Fetch initial state via REST
    const fetchInitialData = async () => {
      try {
        const res = await shippersAPI.getAll();
        console.log('[App] Fetched initial shippers via API:', res.data.length);
        handleInitialState({ shippers: res.data });
      } catch (e) {
        console.warn('[App] Initial fetch failed, waiting for WS...', e);
      }
    };
    fetchInitialData();

    const unsubs = [
      ws.on('initial_state', (data) => {
        console.log('[WS] Initial state received:', data);
        handleInitialState(data);
      }),
      ws.on('bulk_gps_update', (data) => {
        handleBulkUpdate(data);
      }),
      ws.on('dispatch_started', handleDispatch),
      ws.on('shipper_arrived', handleShipperArrived),
      ws.on('all_arrived_at_warehouse', (data) => {
        handleAllArrived()
        const fromEvent = data?.arrived_so_far || data?.shipper_ids || []
        const atWarehouseNow = shipperList
          .filter((s) => String(s?.status || '').toUpperCase() === 'AT_WAREHOUSE')
          .map((s) => s.shipper_id)
        const modalIds = [...new Set([...(fromEvent || []), ...dispatchedIds, ...atWarehouseNow].filter(Boolean))]
        setDeliveryModalShipperIds(modalIds)
        setShowDeliveryModal(modalIds.length > 0)
      }),
      ws.on('delivery_assigned', handleDeliveryAssigned),
      ws.on('delivery_completed', handleDeliveryCompleted),
      ws.on('simulation_completed', handleSimulationCompleted),
      ws.on('simulation_reset', handleReset),
      ws.on('incident_created', (data) => {
        setActiveIncident(data)
      }),
      ws.on('incident_applied', (data) => {
        setActiveIncident(data)
        setDemoMapIncidents((prev) => ({
          ...prev,
          [data.shipper_id]: {
            ...(prev[data.shipper_id] || {}),
            [data.incident_type]: {
              type: data.incident_type,
              estimatedDelay: data.estimated_delay,
              location: data.location,
              startedAt: Date.now(),
              active: true,
            },
          },
        }))
      }),
      ws.on('incident_resolved', (data) => {
        setDemoMapIncidents((prev) => {
          const next = { ...prev }
          if (next[data.shipper_id]) delete next[data.shipper_id]
          return next
        })
      }),
      ws.on('system_alert', (data) => {
        setSystemAlert(data)
      }),
      ws.on('customer_notification', (data) => {
        setCustomerNotice(data)
      }),
      ws.on('eta_updated', (data) => {
        setEtaUpdate(data)
      })
    ]

    return () => unsubs.forEach(unsub => unsub())
  }, [ws, handleInitialState, handleBulkUpdate, handleDispatch, handleShipperArrived, handleAllArrived, handleDeliveryAssigned, handleDeliveryCompleted, handleSimulationCompleted, handleReset, dispatchedIds, shipperList])

  useEffect(() => {
    if (showDeliveryModal) return

    const atWarehouseIds = shipperList
      .filter((s) => String(s?.status || '').toUpperCase() === 'AT_WAREHOUSE')
      .map((s) => s.shipper_id)
      .filter(Boolean)

    if ((simulationPhase === 'WAITING_FOR_ORDER' || atWarehouseIds.length > 0) && atWarehouseIds.length > 0) {
      setDeliveryModalShipperIds(atWarehouseIds)
      setShowDeliveryModal(true)
    }
  }, [simulationPhase, shipperList, showDeliveryModal])

  useEffect(() => {
    const handleCloseModal = () => setShowDeliveryModal(false)
    const handleDemoScript = (event) => setDemoScript(event.detail)
    const handleDemoIncident = (event) => {
      const { shipperId, incidentType, active = true, meta = {} } = event.detail || {}
      if (!shipperId || !incidentType) return
      setDemoMapIncidents((prev) => {
        const next = { ...prev }
        if (!active) {
          if (next[shipperId]) {
            delete next[shipperId][incidentType]
            if (Object.keys(next[shipperId]).length === 0) delete next[shipperId]
          }
          return next
        }
        next[shipperId] = {
          ...(next[shipperId] || {}),
          [incidentType]: { type: incidentType, active, startedAt: Date.now(), ...meta },
        }
        return next
      })
    }

    window.addEventListener('close_delivery_modal', handleCloseModal)
    window.addEventListener('demo_script_update', handleDemoScript)
    window.addEventListener('demo_incident_visual', handleDemoIncident)
    return () => {
      window.removeEventListener('close_delivery_modal', handleCloseModal)
      window.removeEventListener('demo_script_update', handleDemoScript)
      window.removeEventListener('demo_incident_visual', handleDemoIncident)
    }
  }, [])

  // Load dashboard stats
  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await dashboardAPI.getOverview()
        setStats(response.data)
      } catch (e) {
        console.error('Failed to load stats:', e)
      }
    }

    loadStats()
    const interval = setInterval(loadStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleDispatchAction = async (ids) => {
    try {
      await simulationAPI.dispatch(ids)
      setNearestShippers([])
    } catch (e) {
      console.error('Dispatch failed:', e)
    }
  }

  return (
    <div style={styles.app}>
      <TopBar wsConnected={ws.isConnected} shipperCount={shipperList.length} />
      
      <SimulationControls 
        phase={simulationPhase} 
        onNearestFetched={setNearestShippers}
        onDispatch={handleDispatchAction}
      />

      <AutoDemoPanel
        shippers={shipperList}
        onNearestFetched={setNearestShippers}
        onDispatch={handleDispatchAction}
        onSelectShipper={setSelectedShipperId}
        onShowStats={setShowDashboard}
      />

      {nearestShippers.length > 0 && (
        <div style={styles.nearestPanel}>
          <span>Found {nearestShippers.length} nearest shippers:</span>
          <div style={styles.nearestList}>
            {nearestShippers.map(s => (
              <div key={s.shipper_id} style={styles.nearestItem}>
                {s.shipper_id} ({s.distance_km}km)
              </div>
            ))}
          </div>
          <button 
            style={styles.dispatchBtn}
            onClick={() => handleDispatchAction(nearestShippers.map(s => s.shipper_id))}
          >
            🚚 Dispatch to Warehouse
          </button>
        </div>
      )}

      <div style={styles.mainContent}>
        <ShipperList
          shippers={shipperList}
          selectedId={selectedShipperId}
          onSelect={setSelectedShipperId}
        />

        <div style={styles.centerPanel}>
          <MapView 
            shippers={shipperList} 
            selectedId={selectedShipperId} 
            phase={simulationPhase}
            demoScript={demoScript}
            demoMapIncidents={demoMapIncidents}
          />
        </div>

        <div style={styles.rightPanel}>
          <div style={styles.panelTabs}>
            <button 
              style={styles.panelTab(!showDashboard)} 
              onClick={() => setShowDashboard(false)}
            >
              Details
            </button>
            <button 
              style={styles.panelTab(showDashboard)} 
              onClick={() => setShowDashboard(true)}
            >
              Stats
            </button>
          </div>

          <div style={styles.panelContent}>
            {showDashboard ? (
              <Dashboard stats={stats} />
            ) : (
              <RightPanel shipper={selectedShipper} />
            )}
          </div>
          
        </div>
      </div>

      {showDeliveryModal && (
        <DeliveryModal 
          shipperIds={deliveryModalShipperIds.length > 0 ? deliveryModalShipperIds : dispatchedIds}
          onClose={() => setShowDeliveryModal(false)} 
        />
      )}


      <NotificationToast 
        incident={activeIncident} 
        onClear={() => setActiveIncident(null)} 
      />

      <NotificationToast
        incident={
          systemAlert
            ? {
                shipper_id: systemAlert.shipper_id,
                incident_type: `SYSTEM_ALERT: ${systemAlert.suspected_incident}`,
                description: systemAlert.message,
              }
            : null
        }
        onClear={() => setSystemAlert(null)}
      />

      <NotificationToast
        incident={
          customerNotice
            ? {
                shipper_id: customerNotice.shipper_id,
                incident_type: `CUSTOMER_NOTICE (Order ${customerNotice.order_id})`,
                description: `${customerNotice.message} | ETA mới: ${customerNotice.new_eta_minutes} phút`,
              }
            : null
        }
        onClear={() => setCustomerNotice(null)}
      />

      <NotificationToast
        incident={
          etaUpdate
            ? {
                shipper_id: etaUpdate.shipper_id,
                incident_type: 'ETA_UPDATED',
                description: `ETA: ${etaUpdate.old_eta_minutes} → ${etaUpdate.new_eta_minutes} phút (Δ ${etaUpdate.delta_minutes})`,
              }
            : null
        }
        onClear={() => setEtaUpdate(null)}
      />
    </div>
  )
}

const styles = {
  app: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: 'var(--bg)',
    color: 'var(--text)',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  centerPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
  },
  rightPanel: {
    width: '300px',
    display: 'flex',
    flexDirection: 'column',
    borderLeft: '1px solid var(--border)',
    background: 'var(--bg2)',
  },
  panelTabs: {
    display: 'flex',
    background: 'var(--bg)',
    borderBottom: '1px solid var(--border)',
  },
  panelTab: (active) => ({
    flex: 1,
    padding: 'var(--spacing-md)',
    background: active ? 'var(--bg2)' : 'transparent',
    border: 'none',
    color: active ? 'var(--green)' : 'var(--text2)',
    cursor: 'pointer',
    fontSize: 'var(--font-size-sm)',
    fontWeight: 'bold',
  }),
  panelContent: {
    flex: 1,
    overflow: 'auto',
  },
  nearestPanel: {
    padding: 'var(--spacing-md)',
    background: 'var(--bg3)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--spacing-lg)',
    fontSize: 'var(--font-size-sm)',
  },
  nearestList: { display: 'flex', gap: 'var(--spacing-md)' },
  nearestItem: { color: 'var(--green)', fontWeight: 'bold' },
  dispatchBtn: {
    padding: 'var(--spacing-xs) var(--spacing-md)',
    background: 'var(--green)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontWeight: 'bold',
    marginLeft: 'auto'
  },
}

export default App
