/**
 * components/MapView.jsx — Real Leaflet map visualization
 */

import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Warehouse location: 02 Võ Oanh, Bình Thạnh
const WAREHOUSE_LAT = 10.8051
const WAREHOUSE_LON = 106.7144

const INCIDENT_META = {
  TRAFFIC_JAM: { badge: '🚗', color: '#f97316', popup: '⚠️ Kẹt xe — Trễ ~X phút' },
  HEAVY_RAIN: { badge: '🌧️', color: '#7dd3fc', popup: '🌧️ Mưa lớn — Giảm tốc' },
  CUSTOMER_ABSENT: { badge: '👤', color: '#94a3b8', popup: '👤 Khách vắng — Bỏ qua đơn' },
  VEHICLE_BREAKDOWN: { badge: '🔧', color: '#ef4444', popup: '🔧 Hỏng xe — Chờ xử lý' },
  LOST_CONNECTION: { badge: '🔴', color: '#64748b', popup: '🔋 Offline — Tín hiệu cuối' },
}

const getIncidentEntries = (shipper, demoMapIncidents) => {
  const fromDemo = Object.values(demoMapIncidents?.[shipper.shipper_id] || {})
  const fromBackend = shipper.has_incident && shipper.incident_type
    ? [{ type: shipper.incident_type, estimatedDelay: shipper.estimated_delay }]
    : []
  const merged = [...fromDemo, ...fromBackend]
  const seen = new Set()
  return merged.filter((item) => {
    const type = item.type || item.incident_type
    if (!type || seen.has(type)) return false
    seen.add(type)
    return true
  })
}

const statusLabel = (status) => {
  if (status === 'IDLE') return '⏸️ Chờ lệnh'
  if (status === 'HEADING_TO_WAREHOUSE') return '🚚 Về kho'
  if (status === 'AT_WAREHOUSE') return '📦 Nhận hàng'
  if (status === 'DELIVERING') return '🛵 Đang giao'
  if (status === 'DELIVERED') return '✅ Xong'
  if (status === 'VEHICLE_BREAKDOWN') return '🔧 Chờ xử lý'
  if (status === 'LOST_CONNECTION') return '🔴 Offline'
  return status || '—'
}

export const MapView = ({ shippers = [], selectedId, phase, demoScript, demoMapIncidents = {} }) => {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markersRef = useRef(new Map()) // shipper_id -> marker
  const polylinesRef = useRef(new Map()) // shipper_id -> polyline
  const orderMarkersRef = useRef(new Map()) // order_id -> marker
  const warehouseMarkerRef = useRef(null)
  const rainOverlayRef = useRef(null)
  const popupTimersRef = useRef(new Map())
  const pulseCirclesRef = useRef(new Map())

  const hasRain = useMemo(
    () => shippers.some((s) => getIncidentEntries(s, demoMapIncidents).some((i) => (i.type || i.incident_type) === 'HEAVY_RAIN')),
    [shippers, demoMapIncidents]
  )

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
        html: `<div style="background: var(--amber); width: 22px; height: 22px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 12px rgba(0,0,0,0.55); display:flex;align-items:center;justify-content:center;font-size:13px;">🏬</div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      })

      warehouseMarkerRef.current = L.marker([WAREHOUSE_LAT, WAREHOUSE_LON], {
        icon: warehouseIcon
      }).addTo(mapInstance.current).bindPopup('<b>Warehouse</b><br/>02 Võ Oanh, Bình Thạnh')
    }

    return () => {
      popupTimersRef.current.forEach((timer) => clearTimeout(timer))
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!mapInstance.current) return

    if (hasRain && !rainOverlayRef.current) {
      rainOverlayRef.current = L.rectangle(
        [
          [10.755, 106.66],
          [10.835, 106.755],
        ],
        {
          color: '#38bdf8',
          weight: 2,
          fillColor: '#0ea5e9',
          fillOpacity: 0.14,
          dashArray: '9, 8',
          className: 'rain-zone-hatch',
        }
      ).addTo(mapInstance.current).bindPopup('🌧️ Vùng mưa lớn — shipper trong vùng bị giảm tốc')
    } else if (!hasRain && rainOverlayRef.current) {
      rainOverlayRef.current.remove()
      rainOverlayRef.current = null
    }
  }, [hasRain])

  useEffect(() => {
    if (!mapInstance.current) return

    // Update markers
    shippers.forEach(shipper => {
      let marker = markersRef.current.get(shipper.shipper_id)
      const incidents = getIncidentEntries(shipper, demoMapIncidents)
      const incidentTypes = incidents.map((i) => i.type || i.incident_type)
      const primaryIncident = incidentTypes[0]
      const hasOffline = incidentTypes.includes('LOST_CONNECTION') || shipper.status === 'LOST_CONNECTION'
      const hasBreakdown = incidentTypes.includes('VEHICLE_BREAKDOWN') || shipper.status === 'VEHICLE_BREAKDOWN'

      const statusColors = {
        DELIVERING: 'var(--green)',
        HEADING_TO_WAREHOUSE: 'var(--purple)',
        AT_WAREHOUSE: 'var(--blue)',
        IDLE: 'var(--text2)',
        DELIVERED: 'var(--green)',
        DELAYED: '#f97316',
        VEHICLE_BREAKDOWN: '#ef4444',
        LOST_CONNECTION: '#64748b',
        OFFLINE: 'var(--red)',
      }

      const color = INCIDENT_META[primaryIncident]?.color || statusColors[shipper.status] || 'var(--text2)'
      const isSelected = selectedId === shipper.shipper_id
      const size = isSelected ? 30 : 22
      const badgesHtml = incidents.map((incident, index) => {
        const type = incident.type || incident.incident_type
        return `<span style="
          position:absolute;
          top:${-12 - index * 16}px;
          right:${-10 + index * 10}px;
          min-width:18px;
          height:18px;
          border-radius:999px;
          background:#111827;
          border:1px solid #fff;
          display:flex;
          align-items:center;
          justify-content:center;
          font-size:11px;
          box-shadow:0 2px 8px rgba(0,0,0,.35);
        ">${INCIDENT_META[type]?.badge || '⚠️'}</span>`
      }).join('')

      const iconHtml = `
        <div style="position:relative;width:${size}px;height:${size}px;">
          <div style="
            background: ${color};
            width: ${size}px;
            height: ${size}px;
            border-radius: 50%;
            border: 2px solid #fff;
            box-shadow: ${hasBreakdown ? '0 0 0 8px rgba(239,68,68,.25), 0 0 14px rgba(239,68,68,.9)' : '0 0 10px rgba(0,0,0,0.35)'};
            transition: all 0.3s ease, opacity .35s ease, filter .35s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: ${isSelected ? '15px' : '12px'};
            font-weight: bold;
            color: white;
            opacity: ${hasOffline ? 0.3 : 1};
            filter: ${hasOffline ? 'grayscale(1)' : 'none'};
          ">
            ${hasBreakdown ? '🔧' : isSelected ? '🛵' : '●'}
          </div>
          ${badgesHtml}
        </div>
      `

      const icon = L.divIcon({
        className: 'shipper-icon',
        html: iconHtml,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2]
      })

      const popupHtml = `
        <div style="min-width:230px">
          <div><b>${shipper.shipper_id}</b></div>
          <div>Status: ${statusLabel(shipper.status)}</div>
          <div>Speed: ${Number(shipper.speed_kmh || 0).toFixed(1)} km/h</div>
          <div>ETA: ${shipper.eta_minutes != null ? `${shipper.eta_minutes} phút` : '—'}</div>
          <div>Order: ${shipper.order_id || '—'}</div>
          <div>Queue: ${shipper.pending_orders_count || 0} đơn</div>
          <div>Retries (vắng khách): ${shipper.customer_absent_retries || 0}</div>
          ${incidents.length ? `<div style="color:#ef4444;margin-top:4px"><b>⚠️ Map incident:</b> ${incidentTypes.join(', ')}</div>` : ''}
          ${shipper.rain_level ? `<div style="color:#38bdf8">Rain level: ${shipper.rain_level}</div>` : ''}
          ${shipper.last_completed_order_id ? `<div style="margin-top:4px;color:#22c55e">Last done: ${shipper.last_completed_order_id}</div>` : ''}
          ${shipper.completed_orders_count != null ? `<div>Total completed: ${shipper.completed_orders_count}</div>` : ''}
        </div>
      `

      if (marker) {
        marker.setLatLng([shipper.lat, shipper.lon])
        marker.setIcon(icon)
        marker.setPopupContent(popupHtml)
      } else {
        marker = L.marker([shipper.lat, shipper.lon], { icon })
          .addTo(mapInstance.current)
          .bindPopup(popupHtml)
        markersRef.current.set(shipper.shipper_id, marker)
      }

      if (incidents.length) {
        const timerKey = `${shipper.shipper_id}-${primaryIncident}`
        if (!popupTimersRef.current.has(timerKey)) {
          const meta = INCIDENT_META[primaryIncident] || INCIDENT_META.TRAFFIC_JAM
          const delay = incidents[0]?.estimatedDelay || incidents[0]?.estimated_delay || 'X'
          const text = meta.popup.replace('X', delay)
          marker.bindTooltip(text, {
            permanent: true,
            direction: 'right',
            offset: [18, 0],
            className: 'incident-tooltip',
          }).openTooltip()
          const timer = setTimeout(() => {
            marker.closeTooltip()
            popupTimersRef.current.delete(timerKey)
          }, 4500)
          popupTimersRef.current.set(timerKey, timer)
        }
      }

      if (hasBreakdown) {
        let circle = pulseCirclesRef.current.get(shipper.shipper_id)
        if (!circle) {
          circle = L.circle([shipper.lat, shipper.lon], {
            radius: 90,
            color: '#ef4444',
            fillColor: '#ef4444',
            fillOpacity: 0.12,
            weight: 2,
            className: 'breakdown-pulse',
          }).addTo(mapInstance.current)
          pulseCirclesRef.current.set(shipper.shipper_id, circle)
        } else {
          circle.setLatLng([shipper.lat, shipper.lon])
        }
      } else {
        const circle = pulseCirclesRef.current.get(shipper.shipper_id)
        if (circle) {
          circle.remove()
          pulseCirclesRef.current.delete(shipper.shipper_id)
        }
      }

      // ── Draw route polyline if available ──
      if (shipper.route_polyline && shipper.route_polyline.length > 1) {
        const routeColor = INCIDENT_META[primaryIncident]?.color || (shipper.status === 'DELIVERING' ? '#22c55e' :
                           shipper.status === 'HEADING_TO_WAREHOUSE' ? '#a855f7' : '#3b82f6')
        const dashArray = primaryIncident === 'CUSTOMER_ABSENT' ? '3, 8' : '8, 6'
        let polyline = polylinesRef.current.get(shipper.shipper_id)
        if (polyline) {
          polyline.setLatLngs(shipper.route_polyline)
          polyline.setStyle({ color: routeColor, opacity: isSelected ? 0.95 : 0.58, dashArray })
        } else {
          polyline = L.polyline(shipper.route_polyline, {
            color: routeColor,
            weight: isSelected ? 5 : 3,
            opacity: isSelected ? 0.95 : 0.58,
            dashArray,
          }).addTo(mapInstance.current)
          polylinesRef.current.set(shipper.shipper_id, polyline)
        }
        polyline.setStyle({ weight: isSelected ? 5 : 3 })
      } else {
        const existingPolyline = polylinesRef.current.get(shipper.shipper_id)
        if (existingPolyline) {
          existingPolyline.remove()
          polylinesRef.current.delete(shipper.shipper_id)
        }
      }

      // ── Draw Waypoints (Customers) ──
      const waypoints = []
      if (shipper.current_order_dest_lat && shipper.current_order_dest_lon) {
         waypoints.push({
           order_id: shipper.order_id,
           lat: shipper.current_order_dest_lat,
           lon: shipper.current_order_dest_lon,
           is_absent: primaryIncident === 'CUSTOMER_ABSENT'
         })
      }
      if (Array.isArray(shipper.pending_orders)) {
         shipper.pending_orders.forEach(po => {
           waypoints.push({
             order_id: po.order_id,
             lat: po.dest_lat,
             lon: po.dest_lon,
             is_absent: false
           })
         })
      }

      waypoints.forEach(wp => {
        let orderMarker = orderMarkersRef.current.get(wp.order_id)
        const markerColor = wp.is_absent ? '#9ca3af' : '#22c55e'
        const markerIcon = wp.is_absent ? '✕' : '📍'
        const iconHtml = `
          <div style="
            background: ${markerColor};
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: white;
            font-weight: bold;
          ">
            ${markerIcon}
          </div>
        `
        const icon = L.divIcon({
          className: 'order-icon',
          html: iconHtml,
          iconSize: [20, 20],
          iconAnchor: [10, 10]
        })

        if (orderMarker) {
           orderMarker.setLatLng([wp.lat, wp.lon])
           orderMarker.setIcon(icon)
        } else {
           orderMarker = L.marker([wp.lat, wp.lon], { icon }).addTo(mapInstance.current)
           orderMarkersRef.current.set(wp.order_id, orderMarker)
        }
      })
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
    pulseCirclesRef.current.forEach((circle, id) => {
      if (!currentIds.has(id)) {
        circle.remove()
        pulseCirclesRef.current.delete(id)
      }
    })

    // Clean up order markers
    const currentOrderIds = new Set()
    shippers.forEach(s => {
       if (s.order_id) currentOrderIds.add(s.order_id)
       if (Array.isArray(s.pending_orders)) {
           s.pending_orders.forEach(po => currentOrderIds.add(po.order_id))
       }
    })
    orderMarkersRef.current.forEach((marker, id) => {
       if (!currentOrderIds.has(id)) {
           marker.remove()
           orderMarkersRef.current.delete(id)
       }
    })

  }, [shippers, selectedId, demoMapIncidents])

  return (
    <div ref={mapRef} style={styles.container}>
      <style>{`
        .rain-zone-hatch {
          background-image: repeating-linear-gradient(
            135deg,
            rgba(56, 189, 248, .32) 0,
            rgba(56, 189, 248, .32) 6px,
            rgba(14, 165, 233, .08) 6px,
            rgba(14, 165, 233, .08) 14px
          );
        }
        .incident-tooltip {
          background: rgba(15, 23, 42, .92);
          color: #fff;
          border: 1px solid rgba(255,255,255,.35);
          border-radius: 10px;
          box-shadow: 0 10px 28px rgba(0,0,0,.35);
          font-weight: 800;
        }
        .breakdown-pulse {
          animation: breakdownPulse 1s ease-in-out infinite;
        }
        @keyframes breakdownPulse {
          0% { opacity: .25; stroke-width: 1; }
          50% { opacity: .9; stroke-width: 4; }
          100% { opacity: .25; stroke-width: 1; }
        }
      `}</style>
      <div style={styles.phaseOverlay}>
        Phase: <span style={{ color: 'var(--green)' }}>{phase}</span>
      </div>
      <div style={styles.scriptPanel}>
        <div style={styles.scriptStep}>{demoScript?.step || 'Bước 0/9'}</div>
        <div style={styles.scriptText}>{demoScript?.text || 'Đang chờ bắt đầu demo.'}</div>
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
  },
  scriptPanel: {
    position: 'absolute',
    top: 'var(--spacing-md)',
    right: 'var(--spacing-md)',
    zIndex: 1000,
    width: 390,
    maxWidth: 'calc(100% - 32px)',
    background: 'linear-gradient(135deg, rgba(15,23,42,.94), rgba(8,9,11,.88))',
    padding: '14px 16px',
    borderRadius: 14,
    border: '1px solid rgba(34,197,94,.35)',
    boxShadow: '0 18px 45px rgba(0,0,0,.38)',
    backdropFilter: 'blur(8px)',
  },
  scriptStep: {
    color: '#22c55e',
    fontWeight: 900,
    fontSize: 13,
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '.06em',
  },
  scriptText: {
    color: 'var(--text)',
    fontSize: 13,
    lineHeight: 1.45,
    fontWeight: 700,
  },
}