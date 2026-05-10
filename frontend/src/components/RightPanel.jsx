/**
 * components/RightPanel.jsx — Shipper detail panel with Orders & Incidents tabs
 */

import { useState, useEffect } from 'react'
import { incidentsAPI, simulationAPI } from '../services/api'
import IncidentPanel from './IncidentPanel'

// Status color map — 9 trạng thái theo TONGQUAN.md mục 13
const STATUS_COLORS = {
  IDLE: '#94a3b8',
  ASSIGNED: '#60a5fa',
  HEADING_TO_WAREHOUSE: '#f59e0b',
  AT_WAREHOUSE: '#a78bfa',
  DELIVERING: '#22c55e',
  DELIVERED: '#10b981',
  DELAYED: '#f97316',
  VEHICLE_BREAKDOWN: '#ef4444',
  LOST_CONNECTION: '#6b7280',
  OFFLINE: '#475569',
}

const formatDestination = (order) => {
  if (order?.dest_lat != null && order?.dest_lon != null) {
    return `${Number(order.dest_lat).toFixed(5)}, ${Number(order.dest_lon).toFixed(5)}`
  }
  return '—'
}

const formatMoney = (value) => {
  const amount = Number(value)
  if (!Number.isFinite(amount) || amount <= 0) return '—'
  return amount.toLocaleString('vi-VN', { style: 'currency', currency: 'VND' })
}

const formatOrderStatus = (status, isCurrent) => {
  const normalized = String(status || '').toUpperCase()

  if (normalized.includes('FAILED') || normalized === 'CUSTOMER_ABSENT') return '❌ Khách vắng'
  if (normalized === 'DELIVERED') return '✅ Đã giao'
  if (isCurrent || normalized === 'IN_TRANSIT' || normalized === 'DELIVERING') return '🚚 Đang giao'
  if (normalized === 'ASSIGNED' || normalized === 'PENDING') return '📦 Chưa giao'

  return normalized || '📦 Chưa giao'
}

export const RightPanel = ({ shipper = null }) => {
  const [activeTab, setActiveTab] = useState('orders')
  const [incidents, setIncidents] = useState([])
  const [ordersSnapshot, setOrdersSnapshot] = useState({})

  useEffect(() => {
    if (shipper && activeTab === 'incidents') {
      const fetchIncidents = async () => {
        try {
          const res = await incidentsAPI.getByShipper(shipper.shipper_id)
          setIncidents(res.data)
        } catch (e) {
          console.error('Failed to fetch incidents:', e)
        }
      }
      fetchIncidents()
    }
  }, [shipper, activeTab])

  useEffect(() => {
    if (!shipper) return undefined

    const fetchOrdersSnapshot = async () => {
      try {
        const res = await simulationAPI.getOrdersSnapshot()
        setOrdersSnapshot(res.data?.orders || {})
      } catch (e) {
        console.error('Failed to fetch simulation orders:', e)
      }
    }

    fetchOrdersSnapshot()
    const timer = setInterval(fetchOrdersSnapshot, 1500)
    return () => clearInterval(timer)
  }, [shipper])

  if (!shipper) {
    return (
      <div style={styles.container}>
        <p style={styles.placeholder}>Select a shipper to view details</p>
      </div>
    )
  }

  const knownOrders = Object.entries(ordersSnapshot || {})
    .filter(([, order]) => order.shipper_id === shipper.shipper_id)
    .map(([orderId, order]) => ({ order_id: orderId, ...order }))

  const currentOrder = shipper.order_id
    ? knownOrders.find((order) => order.order_id === shipper.order_id) || { order_id: shipper.order_id, status: shipper.status }
    : null

  const queuedOrders = Array.isArray(shipper.pending_orders)
    ? shipper.pending_orders.map((order) => ({
        ...order,
        ...(ordersSnapshot?.[order.order_id] || {}),
        order_id: order.order_id,
      }))
    : []

  const visibleOrders = [
    ...(currentOrder ? [currentOrder] : []),
    ...queuedOrders.filter((order) => order.order_id !== currentOrder?.order_id),
    ...knownOrders.filter(
      (order) => order.order_id !== currentOrder?.order_id && !queuedOrders.some((q) => q.order_id === order.order_id),
    ),
  ]

  const handleResolve = async (incidentId) => {
    try {
      await incidentsAPI.resolve(incidentId)
      setIncidents((prev) => prev.map((inc) => (inc.incident_id === incidentId ? { ...inc, status: 'RESOLVED' } : inc)))
    } catch (e) {
      console.error('Failed to resolve incident:', e)
    }
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>{shipper.shipper_id}</h3>
      <div
        style={{
          ...styles.statusBadge(shipper.status),
          color: STATUS_COLORS[shipper.status] || '#94a3b8',
          borderColor: STATUS_COLORS[shipper.status] || '#334155',
        }}
      >
        {shipper.has_incident ? `⚠️ ${shipper.status}` : shipper.status}
      </div>

      {/* IncidentPanel — 5 nút sự cố */}
      <IncidentPanel selectedShipper={shipper.shipper_id} onIncidentApplied={() => {}} />

      <div style={styles.tabs}>
        <button style={styles.tab(activeTab === 'orders')} onClick={() => setActiveTab('orders')}>
          Orders
        </button>
        <button style={styles.tab(activeTab === 'incidents')} onClick={() => setActiveTab('incidents')}>
          Incidents
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'orders' ? (
          <div style={styles.tabContent}>
            <div style={styles.section}>
              <div style={styles.label}>Order ID (đang giao)</div>
              <div style={styles.value}>{shipper.order_id || 'None'}</div>
            </div>

            <div style={styles.section}>
              <div style={styles.label}>Danh sách đơn tự động nhận tại kho</div>
              <div style={styles.value}>
                {visibleOrders.length} đơn · Queue: {shipper.pending_orders_count != null ? shipper.pending_orders_count : 0}
              </div>

              {visibleOrders.length > 0 ? (
                <div style={styles.orderList}>
                  {visibleOrders.map((o, idx) => (
                    <div key={`${o.order_id || 'order'}-${idx}`} style={styles.orderCard(o.status, o.order_id === shipper.order_id)}>
                      <div style={styles.orderHeader}>
                        <span style={styles.orderId}>{o.order_id || `ORDER-${idx + 1}`}</span>
                        <span style={styles.orderStatus(o.status, o.order_id === shipper.order_id)}>
                          {formatOrderStatus(o.status, o.order_id === shipper.order_id)}
                        </span>
                      </div>
                      <div style={styles.orderLine}>👤 Khách: {o.customer_name || o.customer || `Khách ${idx + 1}`}</div>
                      <div style={styles.orderLine}>
                        📍 Địa chỉ: {o.address || o.destination_text || o.dest_address || o.current_order_destination_text || formatDestination(o)}
                      </div>
                      <div style={styles.orderLine}>💰 Tổng tiền: {formatMoney(o.total_amount || o.amount || o.cod_amount)}</div>
                      {o.attempt != null ? <div style={styles.orderMeta}>attempt: {o.attempt}</div> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={styles.emptyOrders}>Chưa có đơn — khi shipper tới kho hệ thống sẽ random 1–3 đơn và hiển thị tại đây.</div>
              )}
            </div>

            <div style={styles.section}>
              <div style={styles.label}>Điểm giao (lat, lon)</div>
              <div style={styles.value}>
                {shipper.current_order_dest_lat != null && shipper.current_order_dest_lon != null
                  ? `${Number(shipper.current_order_dest_lat).toFixed(5)}, ${Number(shipper.current_order_dest_lon).toFixed(5)}`
                  : '—'}
              </div>
              {shipper.current_order_destination_text ? (
                <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text2)' }}>{shipper.current_order_destination_text}</div>
              ) : null}
            </div>

            <div style={styles.section}>
              <div style={styles.label}>Số đơn đã giao</div>
              <div style={styles.value}>{shipper.completed_orders_count || 0}</div>
              {shipper.last_completed_order_id ? (
                <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text2)' }}>Đơn gần nhất: {shipper.last_completed_order_id}</div>
              ) : null}
            </div>

            <div style={styles.section}>
              <div style={styles.label}>Current Speed</div>
              <div style={styles.value}>{shipper.speed_kmh} km/h</div>
            </div>

            <div style={styles.section}>
              <div style={styles.label}>ETA</div>
              <div style={styles.value}>{shipper.eta_minutes != null ? `${shipper.eta_minutes} phút` : '—'}</div>
            </div>

            <div style={styles.section}>
              <div style={styles.label}>Position</div>
              <div style={styles.value}>
                {shipper.lat?.toFixed(5)}, {shipper.lon?.toFixed(5)}
              </div>
            </div>

            {shipper.has_incident && (
              <div
                style={{
                  background: '#7f1d1d',
                  padding: 8,
                  borderRadius: 6,
                  marginTop: 8,
                  fontSize: 11,
                  color: '#fca5a5',
                }}
              >
                ⚠️ Sự cố: {shipper.incident_type}
              </div>
            )}
          </div>
        ) : (
          <div style={styles.tabContent}>
            {incidents.length === 0 ? (
              <div style={styles.placeholder}>No incidents recorded</div>
            ) : (
              incidents.map((inc) => (
                <div key={inc.incident_id} style={styles.incidentCard(inc.status)}>
                  <div style={styles.incidentHeader}>
                    <span style={styles.incidentType}>{inc.incident_type}</span>
                    <span style={styles.incidentId}>{inc.incident_id}</span>
                  </div>
                  <div style={styles.incidentDesc}>{inc.description}</div>
                  {inc.status === 'ACTIVE' && (
                    <button style={styles.resolveBtn} onClick={() => handleResolve(inc.incident_id)}>
                      Resolve
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const styles = {
  container: {
    width: '272px',
    borderLeft: '1px solid var(--border)',
    padding: 'var(--spacing-lg)',
    overflow: 'auto',
    background: 'var(--bg2)',
    display: 'flex',
    flexDirection: 'column',
  },
  title: { fontSize: 'var(--font-size-lg)', marginBottom: 'var(--spacing-xs)', margin: 0 },
  statusBadge: (status) => ({
    fontSize: '10px',
    padding: '2px 8px',
    borderRadius: '10px',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    width: 'fit-content',
    marginBottom: 'var(--spacing-lg)',
    color: status === 'DELIVERING' ? 'var(--green)' : 'var(--text2)',
  }),
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border)',
    marginBottom: 'var(--spacing-md)',
  },
  tab: (active) => ({
    flex: 1,
    padding: 'var(--spacing-sm)',
    background: 'none',
    border: 'none',
    borderBottom: active ? '2px solid var(--green)' : 'none',
    color: active ? 'var(--text)' : 'var(--text2)',
    cursor: 'pointer',
    fontSize: 'var(--font-size-sm)',
    fontWeight: active ? 'bold' : 'normal',
  }),
  content: { flex: 1 },
  tabContent: {},
  section: { marginBottom: 'var(--spacing-md)' },
  label: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)', marginBottom: '2px' },
  value: { fontSize: 'var(--font-size-base)' },
  placeholder: {
    color: 'var(--text2)',
    textAlign: 'center',
    marginTop: 'var(--spacing-xl)',
    fontSize: 'var(--font-size-sm)',
  },
  orderList: {
    marginTop: 6,
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  orderCard: (status, isCurrent) => ({
    border: `1px solid ${
      String(status || '').toUpperCase() === 'DELIVERED'
        ? '#10b981'
        : String(status || '').toUpperCase().includes('FAILED') || String(status || '').toUpperCase() === 'CUSTOMER_ABSENT'
          ? '#6b7280'
          : isCurrent
            ? '#22c55e'
            : 'var(--border)'
    }`,
    background: 'var(--bg)',
    borderRadius: 6,
    padding: 8,
    fontSize: 11,
    color: 'var(--text2)',
  }),
  orderHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 8,
    marginBottom: 4,
  },
  orderId: { color: 'var(--text)', fontWeight: 700 },
  orderStatus: (status, isCurrent) => ({
    color:
      String(status || '').toUpperCase() === 'DELIVERED'
        ? '#10b981'
        : String(status || '').toUpperCase().includes('FAILED') || String(status || '').toUpperCase() === 'CUSTOMER_ABSENT'
          ? '#9ca3af'
          : isCurrent
            ? '#22c55e'
            : 'var(--text2)',
    fontWeight: 600,
  }),
  orderLine: { marginTop: 2 },
  orderMeta: { marginTop: 4, fontSize: 10, opacity: 0.85 },
  emptyOrders: { marginTop: 4, fontSize: 11, color: 'var(--text2)' },
  incidentCard: (status) => ({
    background: 'var(--bg)',
    padding: 'var(--spacing-md)',
    borderRadius: 'var(--radius-md)',
    border: `1px solid ${status === 'ACTIVE' ? 'var(--red)' : 'var(--border)'}`,
    marginBottom: 'var(--spacing-sm)',
    opacity: status === 'RESOLVED' ? 0.6 : 1,
  }),
  incidentHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' },
  incidentType: { fontSize: '12px', fontWeight: 'bold', color: 'var(--red)' },
  incidentId: { fontSize: '10px', color: 'var(--text2)' },
  incidentDesc: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)', marginBottom: 'var(--spacing-sm)' },
  resolveBtn: {
    width: '100%',
    padding: 'var(--spacing-xs)',
    background: 'var(--green)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontSize: '11px',
    fontWeight: 'bold',
  },
}