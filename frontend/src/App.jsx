/**
 * App.jsx — Main React application
 *
 * 3-panel layout:
 * - Left: Shipper list
 * - Center: Leaflet map
 * - Right: Shipper details + Dashboard
 */

import { useState, useEffect } from 'react'
import { TopBar } from './components/TopBar'
import { ShipperList } from './components/ShipperList'
import { MapView } from './components/MapView'
import { RightPanel } from './components/RightPanel'
import { Dashboard } from './components/Dashboard'
import { useWebSocket } from './hooks/useWebSocket'
import { useShippers } from './hooks/useShippers'
import { shippersAPI, dashboardAPI } from './services/api'
import './styles/theme.css'

function App() {
  const [showDashboard, setShowDashboard] = useState(false)
  const [stats, setStats] = useState(null)
  const ws = useWebSocket()
  const { shippers, selectedShipperId, setSelectedShipperId, updateShipperLocation, setShippersList, shipper_list } = useShippers()

  // Load initial shippers list
  useEffect(() => {
    const loadShippers = async () => {
      try {
        const response = await shippersAPI.getAll()
        setShippersList(response.data)
      } catch (e) {
        console.error('Failed to load shippers:', e)
      }
    }

    loadShippers()
  }, [])

  // Subscribe to WebSocket GPS updates
  useEffect(() => {
    const unsubscribe = ws.subscribe((message) => {
      if (message.shipper_id) {
        updateShipperLocation(message)
      }
    })

    return unsubscribe
  }, [ws, updateShipperLocation])

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

  const selectedShipper = selectedShipperId ? shippers.get(selectedShipperId) : null

  return (
    <div style={styles.app}>
      <TopBar wsConnected={ws.isConnected} shipperCount={shippers.size} />

      <div style={styles.mainContent}>
        <ShipperList
          shippers={shipper_list}
          selectedId={selectedShipperId}
          onSelect={setSelectedShipperId}
        />

        {showDashboard ? (
          <Dashboard stats={stats} />
        ) : (
          <MapView shippers={shipper_list} selectedId={selectedShipperId} />
        )}

        <div style={styles.rightPanel}>
          <button
            style={styles.tabButton}
            onClick={() => setShowDashboard(!showDashboard)}
          >
            {showDashboard ? 'Map' : 'Dashboard'}
          </button>
          {showDashboard ? (
            <Dashboard stats={stats} />
          ) : (
            <RightPanel shipper={selectedShipper} />
          )}
        </div>
      </div>
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
  rightPanel: {
    position: 'relative',
  },
  tabButton: {
    padding: 'var(--spacing-sm) var(--spacing-md)',
    margin: 'var(--spacing-md)',
    background: 'var(--green)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: 'var(--font-size-sm)',
  },
}

export default App
