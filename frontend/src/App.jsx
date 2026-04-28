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
import { IncidentModal } from './components/IncidentModal'
import { NotificationToast } from './components/NotificationToast'

import { useWebSocket } from './hooks/useWebSocket'
import { useShippers } from './hooks/useShippers'
import { dashboardAPI, shippersAPI, simulationAPI } from './services/api'
import './styles/theme.css'

function App() {
  const [showDashboard, setShowDashboard] = useState(false)
  const [stats, setStats] = useState(null)
  const [activeIncident, setActiveIncident] = useState(null)
  const [showDeliveryModal, setShowDeliveryModal] = useState(false)
  const [showIncidentModal, setShowIncidentModal] = useState(false)
  const [nearestShippers, setNearestShippers] = useState([])

  const ws = useWebSocket()
  const { 
    shipperList, 
    selectedShipperId, 
    setSelectedShipperId, 
    selectedShipper,
    simulationPhase,
    dispatchedIds,
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
        setShowDeliveryModal(true)
      }),
      ws.on('delivery_assigned', handleDeliveryAssigned),
      ws.on('delivery_completed', handleDeliveryCompleted),
      ws.on('simulation_completed', handleSimulationCompleted),
      ws.on('simulation_reset', handleReset),
      ws.on('incident_created', (data) => {
        setActiveIncident(data)
      })
    ]

    return () => unsubs.forEach(unsub => unsub())
  }, [ws, handleInitialState, handleBulkUpdate, handleDispatch, handleShipperArrived, handleAllArrived, handleDeliveryAssigned, handleDeliveryCompleted, handleSimulationCompleted, handleReset])

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
          
          <button 
            style={styles.incidentBtn}
            onClick={() => setShowIncidentModal(true)}
          >
            ⚠️ Report Incident
          </button>
        </div>
      </div>

      {showDeliveryModal && (
        <DeliveryModal 
          shipperIds={dispatchedIds} 
          onClose={() => setShowDeliveryModal(false)} 
        />
      )}

      {showIncidentModal && (
        <IncidentModal 
          shippers={shipperList.filter(s => s.status === 'DELIVERING')} 
          onClose={() => setShowIncidentModal(false)} 
        />
      )}

      <NotificationToast 
        incident={activeIncident} 
        onClear={() => setActiveIncident(null)} 
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
  incidentBtn: {
    margin: 'var(--spacing-md)',
    padding: 'var(--spacing-sm)',
    background: 'var(--red)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  }
}

export default App
