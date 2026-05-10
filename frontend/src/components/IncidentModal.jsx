/**
 * components/IncidentModal.jsx — Form to report an incident
 */

import { useState } from 'react'
import { incidentsAPI } from '../services/api'

export const IncidentModal = ({ shippers = [], onClose }) => {
  const [shipperId, setShipperId] = useState(shippers[0]?.shipper_id || '')
  const [type, setType] = useState('TRAFFIC_JAM')
  const [description, setDescription] = useState('')
  const [rainLevel, setRainLevel] = useState('MEDIUM')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await incidentsAPI.create({
        shipper_id: shipperId,
        incident_type: type,
        rain_level: type === 'HEAVY_RAIN' ? rainLevel : undefined,
        description: description
      })
      onClose()
    } catch (err) {
      console.error('Failed to report incident:', err)
      alert('Báo cáo sự cố thất bại!')
    } finally {
      setLoading(false)
    }
  }

  const incidentTypes = [
    { value: 'TRAFFIC_JAM', label: 'Kẹt xe (Traffic Jam)' },
    { value: 'HEAVY_RAIN', label: 'Mưa lớn (Heavy Rain)' },
    { value: 'CUSTOMER_ABSENT', label: 'Khách vắng mặt (Customer Absent)' },
    { value: 'VEHICLE_BREAKDOWN', label: 'Hư xe (Vehicle Breakdown)' },
    { value: 'LOST_CONNECTION', label: 'Mất kết nối GPS (Lost Connection)' },
  ]

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h3 style={styles.title}>⚠️ Báo cáo sự cố</h3>
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Chọn Shipper</label>
            <select 
              value={shipperId} 
              onChange={(e) => setShipperId(e.target.value)}
              style={styles.input}
              required
            >
              {shippers.map(s => (
                <option key={s.shipper_id} value={s.shipper_id}>{s.shipper_id} - {s.status}</option>
              ))}
            </select>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Loại sự cố</label>
            <select 
              value={type} 
              onChange={(e) => setType(e.target.value)}
              style={styles.input}
              required
            >
              {incidentTypes.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {type === 'HEAVY_RAIN' && (
            <div style={styles.field}>
              <label style={styles.label}>Mức độ mưa</label>
              <select
                value={rainLevel}
                onChange={(e) => setRainLevel(e.target.value)}
                style={styles.input}
              >
                <option value="LIGHT">LIGHT</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HEAVY">HEAVY</option>
              </select>
            </div>
          )}

          <div style={styles.field}>
            <label style={styles.label}>Mô tả chi tiết</label>
            <textarea 
              value={description} 
              onChange={(e) => setDescription(e.target.value)}
              style={{...styles.input, height: '80px'}}
              placeholder="Nhập chi tiết sự cố..."
            />
          </div>

          <div style={styles.actions}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>Hủy</button>
            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? 'Đang gửi...' : 'Gửi báo cáo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
  },
  modal: {
    background: 'var(--bg2)',
    padding: 'var(--spacing-xl)',
    borderRadius: 'var(--radius-lg)',
    width: '400px',
    border: '1px solid var(--border)',
    boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
  },
  title: { marginTop: 0, marginBottom: 'var(--spacing-lg)', fontSize: 'var(--font-size-lg)' },
  form: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' },
  field: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xs)' },
  label: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)' },
  input: {
    padding: 'var(--spacing-sm)',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text)',
    fontSize: 'var(--font-size-base)',
    fontFamily: 'inherit'
  },
  actions: { display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-md)' },
  cancelBtn: {
    padding: 'var(--spacing-sm) var(--spacing-lg)',
    background: 'transparent',
    color: 'var(--text2)',
    border: 'none',
    cursor: 'pointer',
  },
  submitBtn: {
    padding: 'var(--spacing-sm) var(--spacing-lg)',
    background: 'var(--red)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  }
}
