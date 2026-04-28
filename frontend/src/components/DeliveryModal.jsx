/**
 * components/DeliveryModal.jsx — Form to assign delivery orders
 */

import { useState } from 'react'
import { simulationAPI } from '../services/api'

export const DeliveryModal = ({ shipperIds = [], onClose }) => {
  const [selectedShipper, setSelectedShipper] = useState(shipperIds[0] || '')
  const [destLat, setDestLat] = useState('10.776')
  const [destLon, setDestLon] = useState('106.700')
  const [destText, setDestText] = useState('Hồ Chí Minh City')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await simulationAPI.assignDelivery({
        shipper_id: selectedShipper,
        dest_lat: parseFloat(destLat),
        dest_lon: parseFloat(destLon),
        destination_text: destText
      })
      onClose()
    } catch (err) {
      console.error('Failed to assign delivery:', err)
      alert('Giao lệnh thất bại!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h3 style={styles.title}>📦 Giao lệnh vận chuyển</h3>
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Chọn Shipper</label>
            <select 
              value={selectedShipper} 
              onChange={(e) => setSelectedShipper(e.target.value)}
              style={styles.input}
              required
            >
              {shipperIds.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Địa chỉ giao hàng</label>
            <input 
              type="text" 
              value={destText} 
              onChange={(e) => setDestText(e.target.value)}
              style={styles.input}
              placeholder="Ví dụ: 123 Lê Lợi, Quận 1"
              required
            />
          </div>

          <div style={styles.row}>
            <div style={styles.field}>
              <label style={styles.label}>Vĩ độ (Lat)</label>
              <input 
                type="number" 
                step="0.000001"
                value={destLat} 
                onChange={(e) => setDestLat(e.target.value)}
                style={styles.input}
                required
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Kinh độ (Lon)</label>
              <input 
                type="number" 
                step="0.000001"
                value={destLon} 
                onChange={(e) => setDestLon(e.target.value)}
                style={styles.input}
                required
              />
            </div>
          </div>

          <div style={styles.actions}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>Hủy</button>
            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? 'Đang gửi...' : 'Xác nhận giao hàng'}
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
  row: { display: 'flex', gap: 'var(--spacing-md)' },
  label: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)' },
  input: {
    padding: 'var(--spacing-sm)',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text)',
    fontSize: 'var(--font-size-base)',
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
    background: 'var(--green)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  }
}
