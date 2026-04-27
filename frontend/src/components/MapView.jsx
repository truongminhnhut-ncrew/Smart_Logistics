/**
 * components/MapView.jsx — Leaflet map visualization
 */

import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default markers
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIconRetina from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIconRetina,
  shadowUrl: markerShadow,
})

export const MapView = ({ shippers = [], selectedId, compact = false }) => {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markersRef = useRef({})

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return

    // TP.HCM center coordinates
    const center = [10.7769, 106.6966]

    // Create map
    const map = L.map(mapRef.current).setView(center, 13)

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    mapInstance.current = map
  }, [])

  // Update markers as shippers change
  useEffect(() => {
    if (!mapInstance.current) return

    // Add or update markers
    shippers.forEach((shipper) => {
      // Handle both API format (current_lat) and WebSocket format (lat)
      const lat = shipper.lat !== undefined ? shipper.lat : shipper.current_lat
      const lon = shipper.lon !== undefined ? shipper.lon : shipper.current_lon

      if (!lat || !lon) return

      const { shipper_id, signal_status = 'ONLINE', current_speed_kmh = 0, heading = 0 } = shipper
      const speed_kmh = shipper.speed_kmh !== undefined ? shipper.speed_kmh : current_speed_kmh
      const hd = shipper.heading !== undefined ? shipper.heading : heading

      const isOnline = signal_status === 'ONLINE'
      const isSelected = shipper_id === selectedId

      // Determine marker color based on status
      let markerColor = '#00e5a0' // green for online
      if (!isOnline) markerColor = '#ff4757' // red for offline
      if (isSelected) markerColor = '#4a9eff' // blue for selected

      if (markersRef.current[shipper_id]) {
        // Update existing marker position (smooth animation)
        const marker = markersRef.current[shipper_id]
        marker.setLatLng([lat, lon])

        // Update icon color if status changed
        marker.setIcon(
          L.icon({
            iconUrl: `data:image/svg+xml;base64,${btoa(`
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${markerColor}" width="32" height="32">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-4-9h8v2h-8z"/>
              </svg>
            `)}`,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -16],
          })
        )

        // Update popup with latest data
        marker.setPopupContent(`
          <div style="font-size:12px; width:150px">
            <b>${shipper_id}</b><br/>
            Status: ${signal_status}<br/>
            Speed: ${speed_kmh.toFixed(1)} km/h<br/>
            Heading: ${hd.toFixed(0)}°<br/>
            Lat: ${lat.toFixed(4)}<br/>
            Lon: ${lon.toFixed(4)}
          </div>
        `)
      } else {
        // Create new marker
        const marker = L.marker([lat, lon], {
          icon: L.icon({
            iconUrl: `data:image/svg+xml;base64,${btoa(`
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${markerColor}" width="32" height="32">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-4-9h8v2h-8z"/>
              </svg>
            `)}`,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -16],
          }),
        })
          .bindPopup(`
            <div style="font-size:12px; width:150px">
              <b>${shipper_id}</b><br/>
              Status: ${signal_status}<br/>
              Speed: ${speed_kmh.toFixed(1)} km/h<br/>
              Heading: ${hd.toFixed(0)}°<br/>
              Lat: ${lat.toFixed(4)}<br/>
              Lon: ${lon.toFixed(4)}
            </div>
          `)
          .addTo(mapInstance.current)

        markersRef.current[shipper_id] = marker
      }
    })
  }, [shippers, selectedId])

  return (
    <div ref={mapRef} style={styles.container(compact)} />
  )
}

const styles = {
  container: (compact) => ({
    flex: 1,
    minHeight: compact ? 280 : 0,
    background: 'var(--bg)',
    borderRight: compact ? 'none' : '1px solid var(--border)',
    borderBottom: compact ? '1px solid var(--border)' : 'none',
    position: 'relative',
    overflow: 'hidden',
    width: '100%',
    height: '100%',
  }),
}
