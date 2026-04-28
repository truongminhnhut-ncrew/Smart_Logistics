/**
 * components/NotificationToast.jsx — Toast notification for incidents
 */

import { useEffect, useState } from 'react'

export const NotificationToast = ({ incident, onClear }) => {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (incident) {
      setVisible(true)
      const timer = setTimeout(() => {
        setVisible(false)
        setTimeout(onClear, 300) // Wait for animation
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [incident, onClear])

  if (!incident) return null

  return (
    <div style={{
      ...styles.toast,
      transform: visible ? 'translateX(0)' : 'translateX(120%)',
      opacity: visible ? 1 : 0
    }}>
      <div style={styles.header}>
        <span style={styles.icon}>⚠️</span>
        <span style={styles.title}>SỰ CỐ MỚI</span>
        <button onClick={() => setVisible(false)} style={styles.closeBtn}>×</button>
      </div>
      <div style={styles.body}>
        <b>{incident.shipper_id}</b>: {incident.incident_type}
        <div style={styles.desc}>{incident.description}</div>
      </div>
    </div>
  )
}

const styles = {
  toast: {
    position: 'fixed',
    bottom: 'var(--spacing-xl)',
    right: 'var(--spacing-xl)',
    width: '300px',
    background: 'var(--bg2)',
    borderLeft: '4px solid var(--red)',
    borderRadius: 'var(--radius-md)',
    boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
    zIndex: 3000,
    transition: 'all 0.3s cubic-bezier(0.68, -0.55, 0.27, 1.55)',
    padding: 'var(--spacing-md)',
    color: 'var(--text)',
  },
  header: { display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' },
  icon: { fontSize: '18px' },
  title: { fontWeight: 'bold', fontSize: 'var(--font-size-sm)', color: 'var(--red)', flex: 1 },
  closeBtn: { background: 'none', border: 'none', color: 'var(--text2)', cursor: 'pointer', fontSize: '20px' },
  body: { fontSize: 'var(--font-size-sm)' },
  desc: { marginTop: 'var(--spacing-xs)', color: 'var(--text2)', fontStyle: 'italic' }
}
