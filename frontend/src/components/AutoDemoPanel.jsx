import { useEffect, useRef, useState } from 'react'
import { dashboardAPI, shippersAPI, simulationAPI } from '../services/api'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const DEMO_STEPS = [
  { id: 'initial', label: '1. Trạng thái ban đầu', text: 'Tất cả shipper đứng yên trên bản đồ, hiển thị trạng thái ⏸️ Chờ lệnh.' },
  { id: 'start', label: '2. Bắt đầu giao hàng', text: 'Reset dữ liệu cũ và khởi động simulation giao hàng.' },
  { id: 'nearest', label: '3. Tìm 3 shipper gần kho', text: 'Hệ thống tính khoảng cách Haversine để ưu tiên shipper tối ưu gần kho.' },
  { id: 'dispatch', label: '4. Dispatch về kho', text: '3 shipper được điều phối di chuyển về kho 02 Võ Oanh, Bình Thạnh.' },
  { id: 'warehouse-orders', label: '5. Tự động nhận đơn', text: 'Khi từng shipper đến kho, hệ thống random 1–3 đơn và hiển thị ngay trong detail panel.' },
  { id: 'delivery', label: '6. Xuất phát giao hàng', text: 'Sau khi nhận đơn, shipper tự động đi qua từng waypoint khách hàng.' },
  { id: 'incidents', label: '7. Biểu diễn 5 sự cố', text: 'Tự động lần lượt trigger: kẹt xe, mưa lớn, khách vắng, hư xe, mất kết nối.' },
  { id: 'dashboard', label: '8. Dashboard realtime', text: 'Chuyển sang dashboard để quan sát số liệu vận hành realtime.' },
  { id: 'finish', label: '9. Kết thúc đúng điều kiện', text: 'Demo chỉ hoàn tất khi giao xong toàn bộ đơn có thể giao và đủ 5 sự cố đã xuất hiện.' },
]

const INCIDENT_SEQUENCE = [
  {
    type: 'TRAFFIC_JAM',
    script: (s, order) => `Shipper ${s.shipper_id} gặp kẹt xe tại vị trí hiện tại — tốc độ giảm còn ~30%, ETA đơn ${order || s.order_id || 'đang giao'} bị đẩy lùi ~8 phút.`,
    resolveAfter: 6500,
  },
  {
    type: 'HEAVY_RAIN',
    rainLevel: 'HEAVY',
    script: (s) => `Khu vực Bình Thạnh đang có mưa lớn — tất cả shipper trong vùng bị ảnh hưởng tốc độ, badge 🌧️ và overlay mưa xuất hiện trên map.`,
    resolveAfter: 6500,
  },
  {
    type: 'CUSTOMER_ABSENT',
    script: (s, order) => `Shipper ${s.shipper_id} không gặp khách tại địa chỉ giao — đơn ${order || s.order_id || 'hiện tại'} ghi nhận 'Khách vắng', tiếp tục đơn kế tiếp.`,
    resolveAfter: 4500,
  },
  {
    type: 'VEHICLE_BREAKDOWN',
    script: (s) => `Shipper ${s.shipper_id} hỏng xe tại vị trí hiện tại — hệ thống dispatch shipper gần nhất tiếp quản các đơn còn lại.`,
    resolveAfter: null,
  },
  {
    type: 'LOST_CONNECTION',
    script: (s) => `Shipper ${s.shipper_id} mất kết nối — hệ thống giữ vị trí cuối cùng, marker mờ 30% và chờ tín hiệu phục hồi.`,
    resolveAfter: 6500,
  },
]

const normalizeStatus = (value) => String(value || '').toUpperCase()

const emitScript = (stepIndex, text) => {
  window.dispatchEvent(new CustomEvent('demo_script_update', {
    detail: { step: `Bước ${stepIndex}/9`, text },
  }))
}

const emitIncidentVisual = (shipperId, incidentType, active, meta = {}) => {
  window.dispatchEvent(new CustomEvent('demo_incident_visual', {
    detail: { shipperId, incidentType, active, meta },
  }))
}

const waitForCondition = async (predicate, { timeoutMs = 120000, intervalMs = 1000, cancelledRef }) => {
  const startedAt = Date.now()
  while (!cancelledRef.current && Date.now() - startedAt < timeoutMs) {
    const value = await predicate()
    if (value) return value
    await sleep(intervalMs)
  }
  throw new Error('Timeout khi chờ điều kiện demo')
}

const chooseDeliveringShipper = async (excludeIds = new Set()) => {
  const res = await shippersAPI.getAll()
  const list = res.data || []
  return (
    list.find((s) => s.shipper_id && !excludeIds.has(s.shipper_id) && s.order_id && normalizeStatus(s.status) === 'DELIVERING') ||
    list.find((s) => s.shipper_id && !excludeIds.has(s.shipper_id) && s.order_id) ||
    list.find((s) => s.shipper_id && !excludeIds.has(s.shipper_id))
  )
}

const getSimulationOrders = async () => {
  try {
    const res = await simulationAPI.getOrdersSnapshot()
    return res.data?.orders || {}
  } catch {
    return {}
  }
}

const isBusinessFinished = (shippers, ordersSnapshot, representedIncidents) => {
  const dispatched = shippers.filter((s) =>
    ['DELIVERING', 'AT_WAREHOUSE', 'HEADING_TO_WAREHOUSE', 'DELAYED', 'LOST_CONNECTION'].includes(normalizeStatus(s.status)) ||
    s.order_id ||
    (s.pending_orders_count || 0) > 0
  )
  const hasMovableWork = dispatched.some((s) =>
    normalizeStatus(s.status) !== 'VEHICLE_BREAKDOWN' && (s.order_id || (s.pending_orders_count || 0) > 0 || ['DELIVERING', 'HEADING_TO_WAREHOUSE', 'AT_WAREHOUSE', 'DELAYED'].includes(normalizeStatus(s.status)))
  )
  const orderValues = Object.values(ordersSnapshot || {})
  const allKnownOrdersClosed = orderValues.length === 0 || orderValues.every((o) =>
    ['DELIVERED', 'FAILED', 'DELIVERY_FAILED', 'DELIVERY_FAILED_ATTEMPT_1'].includes(normalizeStatus(o.status))
  )
  return !hasMovableWork && allKnownOrdersClosed && representedIncidents.size >= 5
}

export const AutoDemoPanel = ({
  shippers = [],
  onNearestFetched,
  onDispatch,
  onSelectShipper,
  onShowStats,
}) => {
  const [running, setRunning] = useState(false)
  const [demoStatus, setDemoStatus] = useState('idle')
  const [steps, setSteps] = useState(DEMO_STEPS.map((step) => ({ ...step, status: 'pending', note: '' })))
  const [currentMessage, setCurrentMessage] = useState('Đang chuẩn bị auto demo...')
  const [explanations, setExplanations] = useState([])
  const cancelledRef = useRef(false)
  const autoStartedRef = useRef(false)
  const representedIncidentsRef = useRef(new Set())

  const updateStep = (id, status, note = '') => {
    setSteps((prev) => prev.map((step) => (step.id === id ? { ...step, status, note } : step)))
  }

  const addExplanation = (text, stepId = null, stepIndex = null) => {
    setExplanations((prev) => [...prev.slice(-10), text])
    setCurrentMessage(text)
    if (stepId) updateStep(stepId, 'running', text)
    if (stepIndex) emitScript(stepIndex, text)
  }

  const markDone = (id, note = 'OK') => updateStep(id, 'done', note)

  const deliveringCount = shippers.filter(s => ['DELIVERING', 'DELAYED'].includes(String(s.status || '').toUpperCase())).length
  const deliveredCount = shippers.filter(s => String(s.status || '').toUpperCase() === 'DELIVERED').length

  const applyIncidentVisualFirst = async (shipper, incident, orderId) => {
    representedIncidentsRef.current.add(incident.type)
    emitIncidentVisual(shipper.shipper_id, incident.type, true, {
      estimatedDelay: incident.type === 'TRAFFIC_JAM' ? 8 : incident.type === 'HEAVY_RAIN' ? 6 : 0,
      orderId,
    })
    addExplanation(incident.script(shipper, orderId), 'incidents', 7)

    try {
      await simulationAPI.applyIncident({
        shipper_id: shipper.shipper_id,
        incident_type: incident.type,
        rain_level: incident.rainLevel || 'MEDIUM',
      })
    } catch (e) {
      addExplanation(`⚠️ Backend không nhận ${incident.type} cho ${shipper.shipper_id}; vẫn giữ visual demo trên map: ${e.message}`, 'incidents', 7)
    }

    if (incident.resolveAfter) {
      await sleep(incident.resolveAfter)
      try {
        await simulationAPI.resolveIncident(shipper.shipper_id)
      } catch {
        // visual fallback vẫn resolve
      }
      emitIncidentVisual(shipper.shipper_id, incident.type, false)
      addExplanation(`✅ ${incident.type} của ${shipper.shipper_id} đã resolve — badge biến mất, màu đường/icon phục hồi.`, 'incidents', 7)
    }
  }

  const runDemo = async () => {
    if (running) return

    cancelledRef.current = false
    representedIncidentsRef.current = new Set()
    setRunning(true)
    setDemoStatus('running')
    setSteps(DEMO_STEPS.map((step) => ({ ...step, status: 'pending', note: '' })))
    setExplanations([])

    try {
      updateStep('initial', 'running')
      emitScript(1, DEMO_STEPS[0].text)
      addExplanation('⏸️ Trạng thái ban đầu: toàn bộ shipper chờ lệnh trên bản đồ.', 'initial')
      await dashboardAPI.getOverview()
      markDone('initial', 'Backend OK, fleet sẵn sàng')

      await sleep(600)
      updateStep('start', 'running')
      emitScript(2, DEMO_STEPS[1].text)
      addExplanation('Reset trạng thái cũ và bắt đầu giao hàng.', 'start')
      await simulationAPI.reset()
      await sleep(500)
      await simulationAPI.start()
      markDone('start', 'Simulation STARTED')

      await sleep(700)
      updateStep('nearest', 'running')
      emitScript(3, DEMO_STEPS[2].text)
      const nearest = await simulationAPI.getNearest(3)
      const nearestList = nearest.data?.nearest || []
      onNearestFetched(nearestList)
      const ids = nearestList.map((item) => item.shipper_id).filter(Boolean)
      if (ids[0]) onSelectShipper(ids[0])
      markDone('nearest', `Tìm được ${ids.length} shipper: ${ids.join(', ')}`)

      await sleep(700)
      updateStep('dispatch', 'running')
      emitScript(4, DEMO_STEPS[3].text)
      if (ids.length) {
        try {
          await onDispatch(ids)
        } catch {
          // /start có thể đã auto-dispatch; vẫn tiếp tục flow
        }
      }
      markDone('dispatch', `Dispatch ${ids.length || 3} shipper về kho`)

      updateStep('warehouse-orders', 'running')
      emitScript(5, DEMO_STEPS[4].text)
      addExplanation('Đang chờ shipper đến kho; backend sẽ tự random 1–3 đơn cho từng shipper và phát sự kiện delivery_assigned.', 'warehouse-orders')
      const withOrders = await waitForCondition(async () => {
        const res = await shippersAPI.getAll()
        const assigned = (res.data || []).filter((s) => s.order_id || (s.pending_orders_count || 0) > 0)
        return assigned.length > 0 ? assigned : null
      }, { timeoutMs: 180000, intervalMs: 1000, cancelledRef })
      const selected = withOrders[0]
      if (selected?.shipper_id) onSelectShipper(selected.shipper_id)
      window.dispatchEvent(new CustomEvent('close_delivery_modal'))
      markDone('warehouse-orders', `${withOrders.length} shipper đã nhận đơn tự động`)

      updateStep('delivery', 'running')
      emitScript(6, DEMO_STEPS[5].text)
      addExplanation('Shipper tự động xuất phát giao hàng theo route/waypoint khách hàng; tốc độ demo đã được tăng ở engine.', 'delivery')
      await sleep(2500)
      markDone('delivery', 'Đã vào pha DELIVERING')

      updateStep('incidents', 'running')
      emitScript(7, DEMO_STEPS[6].text)
      const usedShippers = new Set()
      for (const incident of INCIDENT_SEQUENCE) {
        if (cancelledRef.current) return
        const shipper = await chooseDeliveringShipper(incident.type === 'VEHICLE_BREAKDOWN' ? new Set() : usedShippers)
        if (!shipper?.shipper_id) throw new Error(`Không tìm được shipper để trigger ${incident.type}`)
        usedShippers.add(shipper.shipper_id)
        onSelectShipper(shipper.shipper_id)

        let orderId = shipper.order_id
        if (incident.type === 'CUSTOMER_ABSENT') {
          const nearCustomer = await waitForCondition(async () => {
            const candidate = await chooseDeliveringShipper(new Set())
            if (!candidate?.order_id) return null
            const eta = Number(candidate.eta_minutes ?? 99)
            return normalizeStatus(candidate.status) === 'DELIVERING' && eta <= 2.5 ? candidate : null
          }, { timeoutMs: 90000, intervalMs: 1000, cancelledRef }).catch(() => shipper)
          orderId = nearCustomer.order_id
          await applyIncidentVisualFirst(nearCustomer, incident, orderId)
        } else {
          await applyIncidentVisualFirst(shipper, incident, orderId)
        }

        await sleep(900)
      }
      markDone('incidents', `Đã biểu diễn đủ ${representedIncidentsRef.current.size}/5 sự cố`)

      updateStep('dashboard', 'running')
      emitScript(8, DEMO_STEPS[7].text)
      onShowStats(true)
      const fleetStats = await dashboardAPI.getFleetStats()
      markDone('dashboard', `Fleet stats OK: ${fleetStats.status || 'ready'}`)

      updateStep('finish', 'running')
      emitScript(9, DEMO_STEPS[8].text)
      addExplanation('Đang theo dõi điều kiện kết thúc: tất cả đơn có thể giao đã xong và đủ 5 sự cố đã xuất hiện.', 'finish')

      const final = await waitForCondition(async () => {
        const [shipperRes, orderSnapshot] = await Promise.all([shippersAPI.getAll(), getSimulationOrders()])
        const shippers = shipperRes.data || []
        const done = isBusinessFinished(shippers, orderSnapshot, representedIncidentsRef.current)
        if (!done) {
          const active = shippers.filter((s) => s.order_id || (s.pending_orders_count || 0) > 0).length
          updateStep('finish', 'running', `Đang chờ: active shipper/order=${active}, incidents=${representedIncidentsRef.current.size}/5`)
        }
        return done ? { shippers, orderSnapshot } : null
      }, { timeoutMs: 12 * 60 * 1000, intervalMs: 2000, cancelledRef })

      markDone('finish', `Hoàn tất: incidents=${representedIncidentsRef.current.size}/5`)
      setDemoStatus('done')
      addExplanation(`✅ Demo hoàn tất thật sự: giao xong toàn bộ đơn có thể giao và đã biểu diễn đủ ${representedIncidentsRef.current.size}/5 sự cố.`, 'finish', 9)
      return final
    } catch (error) {
      const message = error?.response?.data?.detail || error?.message || 'Unknown error'
      setDemoStatus('error')
      addExplanation(`❌ Demo chưa thể đánh dấu hoàn tất: ${message}`)
      setSteps((prev) =>
        prev.map((step) => (step.status === 'running' ? { ...step, status: 'error', note: message } : step))
      )
    } finally {
      setRunning(false)
    }
  }

  useEffect(() => {
    if (!autoStartedRef.current) {
      autoStartedRef.current = true
      runDemo()
    }

    return () => {
      cancelledRef.current = true
    }
  }, [])

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <div>
          <div style={styles.title}>🧪 Auto Demo / 9 luồng giao hàng</div>
          <div style={styles.subtitle}>
            Tự động chạy tuần tự, cập nhật script realtime và trigger 5 sự cố trực quan trên map.
          </div>
        </div>
        <div style={styles.badge(demoStatus)}>
          {demoStatus === 'done'
            ? 'Demo hoàn tất'
            : demoStatus === 'error'
              ? 'Demo lỗi'
              : 'Đang chạy 9 bước'}
        </div>
      </div>

      <div style={styles.scriptHeader}>
        <div style={styles.messageBanner}>{currentMessage}</div>
        <div style={styles.liveStats}>
          <div style={styles.statItem}>🛵 Đang giao: <span style={styles.statVal}>{deliveringCount}</span></div>
          <div style={styles.statItem}>✅ Đã giao: <span style={styles.statVal}>{deliveredCount}</span></div>
        </div>
      </div>

      <div style={styles.steps}>
        {steps.map((step, index) => (
          <div key={step.id} style={styles.step(step.status)}>
            <span style={styles.status}>{statusIcon(step.status)}</span>
            <div>
              <div style={styles.stepLabel}>Bước {index + 1}/9 — {step.label.replace(/^\d+\.\s*/, '')}</div>
              <div style={styles.description}>{step.text}</div>
              {step.note && <div style={styles.note}>{step.note}</div>}
            </div>
          </div>
        ))}
      </div>

      <div style={styles.log}>
        {explanations.slice(-7).map((item, idx) => (
          <div key={`${item}-${idx}`} style={styles.logItem}>{item}</div>
        ))}
      </div>
    </div>
  )
}

const statusIcon = (status) => {
  if (status === 'done') return '✅'
  if (status === 'running') return '▶️'
  if (status === 'error') return '❌'
  return '○'
}

const styles = {
  panel: {
    background: 'var(--bg2)',
    borderBottom: '1px solid var(--border)',
    padding: '10px 14px',
    maxHeight: 260,
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    fontWeight: 900,
    fontSize: 14,
    color: 'var(--text)',
  },
  subtitle: {
    color: 'var(--text2)',
    fontSize: 12,
    marginTop: 2,
  },
  badge: (status) => ({
    padding: '6px 10px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 900,
    color: status === 'done' ? '#052e16' : status === 'error' ? '#fee2e2' : '#04111f',
    background: status === 'done' ? '#22c55e' : status === 'error' ? '#ef4444' : '#38bdf8',
    whiteSpace: 'nowrap',
  }),
  scriptHeader: {
    display: 'flex',
    gap: 12,
    alignItems: 'center',
    marginBottom: 8,
  },
  messageBanner: {
    flex: 1,
    padding: '8px 12px',
    borderRadius: 10,
    background: 'rgba(56,189,248,.12)',
    border: '1px solid rgba(56,189,248,.35)',
    color: '#38bdf8',
    fontSize: 13,
    fontWeight: 900,
  },
  liveStats: {
    display: 'flex',
    gap: 12,
    background: 'var(--bg3)',
    padding: '6px 12px',
    borderRadius: 10,
    border: '1px solid var(--border)',
  },
  statItem: {
    fontSize: 12,
    fontWeight: 800,
    color: 'var(--text2)',
  },
  statVal: {
    color: 'var(--text)',
    marginLeft: 4,
  },
  steps: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: 6,
  },
  step: (status) => ({
    display: 'flex',
    gap: 7,
    padding: 7,
    borderRadius: 8,
    background: status === 'running' ? 'rgba(56,189,248,.12)' : status === 'done' ? 'rgba(34,197,94,.10)' : status === 'error' ? 'rgba(239,68,68,.12)' : 'var(--bg)',
    border: `1px solid ${status === 'running' ? 'rgba(56,189,248,.35)' : status === 'done' ? 'rgba(34,197,94,.25)' : status === 'error' ? 'rgba(239,68,68,.35)' : 'var(--border)'}`,
    minHeight: 58,
  }),
  status: { fontSize: 13, lineHeight: '16px' },
  stepLabel: { color: 'var(--text)', fontSize: 11, fontWeight: 900 },
  description: { color: 'var(--text2)', fontSize: 10, lineHeight: 1.3, marginTop: 2 },
  note: { color: '#93c5fd', fontSize: 10, marginTop: 3, fontWeight: 700 },
  log: {
    marginTop: 8,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  logItem: {
    fontSize: 11,
    color: 'var(--text2)',
    paddingLeft: 8,
    borderLeft: '2px solid rgba(148,163,184,.25)',
  },
}