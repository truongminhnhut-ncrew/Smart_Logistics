/**
 * components/MapView.jsx — Real Leaflet map visualization
 */

import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Warehouse location: 02 Võ Oanh, Bình Thạnh
const WAREHOUSE_LAT = 10.8051
const WAREHOUSE_LON = 106.7144

export const MapView = ({ shippers = [], selectedId, phase }) => {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markersRef = useRef(new Map()) // shipper_id -> marker
  const polylinesRef = useRef(new Map()) // shipper_id -> polyline
  const warehouseMarkerRef = useRef(null)

  useEffect(() => {
    // Initialize map
    if (!mapInstance.current && mapRef.current) {
      mapInstance.current = L.map(mapRef.current).setView([10.776, 106.700], 13)

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstance.current)

      // Add Warehouse Marker
      const warehouseIcon = L.divIcon({
        className: 'warehouse-icon',
        html: `<div style="background: var(--amber); width: 16px; height: 16px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      })

      warehouseMarkerRef.current = L.marker([WAREHOUSE_LAT, WAREHOUSE_LON], {
        icon: warehouseIcon
      }).addTo(mapInstance.current).bindPopup('<b>Warehouse</b><br/>02 Võ Oanh, Bình Thạnh')
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!mapInstance.current) return

    // Update markers
    shippers.forEach(shipper => {
      let marker = markersRef.current.get(shipper.shipper_id)

      const statusColors = {
        DELIVERING: 'var(--green)',
        HEADING_TO_WAREHOUSE: 'var(--purple)',
        AT_WAREHOUSE: 'var(--blue)',
        IDLE: 'var(--text2)',
        DELIVERED: 'var(--green)',
        OFFLINE: 'var(--red)',
      }

      const color = statusColors[shipper.status] || 'var(--text2)'
      const isSelected = selectedId === shipper.shipper_id

      const iconHtml = `
        <div style="
          background: ${color};
          width: ${isSelected ? '24px' : '12px'};
          height: ${isSelected ? '24px' : '12px'};
          border-radius: 50%;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(0,0,0,0.3);
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 8px;
          font-weight: bold;
          color: white;
        ">
          ${isSelected ? '🛵' : ''}
        </div>
      `

      const icon = L.divIcon({
        className: 'shipper-icon',
        html: iconHtml,
        iconSize: isSelected ? [24, 24] : [12, 12],
        iconAnchor: isSelected ? [12, 12] : [6, 6]
      })

      if (marker) {
        marker.setLatLng([shipper.lat, shipper.lon])
        marker.setIcon(icon)
      } else {
        marker = L.marker([shipper.lat, shipper.lon], { icon })
          .addTo(mapInstance.current)
          .bindPopup(`<b>${shipper.shipper_id}</b><br/>Status: ${shipper.status}<br/>Speed: ${shipper.speed_kmh} km/h`)
        markersRef.current.set(shipper.shipper_id, marker)
      }

      // ── Draw route polyline if available ──
      if (shipper.route_polyline && shipper.route_polyline.length > 1) {
        const routeColor = shipper.status === 'DELIVERING' ? '#22c55e' :
                           shipper.status === 'HEADING_TO_WAREHOUSE' ? '#a855f7' : '#3b82f6'
        let polyline = polylinesRef.current.get(shipper.shipper_id)
        if (polyline) {
          polyline.setLatLngs(shipper.route_polyline)
          polyline.setStyle({ color: routeColor, opacity: isSelected ? 0.9 : 0.4 })
        } else {
          polyline = L.polyline(shipper.route_polyline, {
            color: routeColor,
            weight: isSelected ? 4 : 2,
            opacity: isSelected ? 0.9 : 0.4,
            dashArray: '8, 6',
          }).addTo(mapInstance.current)
          polylinesRef.current.set(shipper.shipper_id, polyline)
        }
        // Update weight for selected
        polyline.setStyle({ weight: isSelected ? 4 : 2 })
      } else {
        // Remove polyline if no route
        const existingPolyline = polylinesRef.current.get(shipper.shipper_id)
        if (existingPolyline) {
          existingPolyline.remove()
          polylinesRef.current.delete(shipper.shipper_id)
        }
      }

      if (isSelected) {
        // Optionally center map on selected shipper
        // mapInstance.current.panTo([shipper.lat, shipper.lon])
      }
    })

    // Clean up markers and polylines for shippers not in list
    const currentIds = new Set(shippers.map(s => s.shipper_id))
    markersRef.current.forEach((marker, id) => {
      if (!currentIds.has(id)) {
        marker.remove()
        markersRef.current.delete(id)
      }
    })
    polylinesRef.current.forEach((polyline, id) => {
      if (!currentIds.has(id)) {
        polyline.remove()
        polylinesRef.current.delete(id)
      }
    })
  }, [shippers, selectedId])

  return (
    <div ref={mapRef} style={styles.container}>
      <div style={styles.phaseOverlay}>
        Phase: <span style={{ color: 'var(--green)' }}>{phase}</span>
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
  phaseOverlay: {
    position: 'absolute',
    top: 'var(--spacing-md)',
    left: 'var(--spacing-md)',
    zIndex: 1000,
    background: 'rgba(8, 9, 11, 0.8)',
    padding: 'var(--spacing-sm) var(--spacing-md)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    fontSize: 'var(--font-size-sm)',
    fontWeight: 'bold',
  }
}
