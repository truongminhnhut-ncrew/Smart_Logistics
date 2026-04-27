/**
 * components/MapView.jsx — Leaflet map visualization
 */

import { useEffect, useRef } from 'react'

export const MapView = ({ shippers = [], selectedId }) => {
  const mapRef = useRef(null)

  useEffect(() => {
    // Placeholder for Leaflet map initialization
    // Map will be rendered here with shipper markers
    if (mapRef.current) {
      mapRef.current.textContent = `Map initialized - ${shippers.length} shippers`
    }
  }, [shippers.length])

  return (
    <div ref={mapRef} style={styles.container}>
      <div style={styles.placeholder}>
        🗺️ Leaflet Map (OpenStreetMap - TP.HCM)
        <br />
        <small>{shippers.length} shippers with real-time GPS markers</small>
      </div>
    </div>
  )
}

const styles = {
  container: {
    flex: 1,
    background: 'var(--bg)',
    borderRight: '1px solid var(--border)',
    position: 'relative',
    overflow: 'hidden',
  },
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text2)',
    fontSize: 'var(--font-size-lg)',
  },
}
