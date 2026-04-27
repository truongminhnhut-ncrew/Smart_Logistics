/**
 * App.jsx — Main React application
 *
 * 3-panel layout:
 * - Left: Shipper list (250px)
 * - Center: Leaflet map (flex: 1)
 * - Right: Dashboard stats + Shipper details (272px)
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
  const [stats, setStats] = useState(null)
  const [windowWidth, setWindowWidth] = useState(window.innerWidth)
  const ws = useWebSocket()
  const { shippers, selectedShipperId, setSelectedShipperId, updateShipperLocation, setShippersList, shipper_list } = useShippers()

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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

  // Subscribe to WebSocket messages
  useEffect(() => {
    const unsubscribe = ws.subscribe((message) => {
      // Handle init snapshot
      if (message.type === 'init' && message.shippers) {
        console.log('[App] Received init snapshot with', message.shippers.length, 'shippers')
        setShippersList(message.shippers)
      }
      // Handle location updates
      else if (message.shipper_id) {
        updateShipperLocation(message)
      }
    })

    return unsubscribe
  }, [ws, updateShipperLocation, setShippersList])

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
  const isCompact = windowWidth < 1180
  const isMobile = windowWidth < 768
  const rightPanelWidth = isMobile ? '100%' : isCompact ? 320 : 360

  return (
    <div style={styles.app}>
      <TopBar
        wsConnected={ws.isConnected}
        shipperCount={stats?.fleet?.online_count ?? shippers.size}
        totalShippers={stats?.fleet?.total_shippers ?? shippers.size}
      />

      <div style={styles.mainContent(isMobile)}>
        {/* LEFT PANEL: Shipper List */}
        <ShipperList
          shippers={shipper_list}
          selectedId={selectedShipperId}
          onSelect={setSelectedShipperId}
          compact={isCompact}
          mobile={isMobile}
        />

        {/* CENTER PANEL: Map (Always visible) */}
        <MapView shippers={shipper_list} selectedId={selectedShipperId} compact={isMobile} />

        {/* RIGHT PANEL: Dashboard + Details */}
        <div style={styles.rightPanel(isMobile, rightPanelWidth)}>
          <Dashboard stats={stats} compact={isCompact} />
          <RightPanel shipper={selectedShipper} />
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
  mainContent: (isMobile) => ({
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    gap: 0,
    flexDirection: isMobile ? 'column' : 'row',
  }),
  rightPanel: (isMobile, width) => ({
    width,
    minWidth: isMobile ? 0 : width,
    maxWidth: isMobile ? '100%' : width,
    borderLeft: isMobile ? 'none' : '1px solid var(--border)',
    borderTop: isMobile ? '1px solid var(--border)' : 'none',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg)',
  }),
}

export default App
