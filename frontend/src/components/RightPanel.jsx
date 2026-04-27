/**
 * components/RightPanel.jsx — Shipper detail panel
 */

export const RightPanel = ({ shipper = null }) => {
  if (!shipper) {
    return (
      <div style={styles.container}>
        <p style={styles.placeholder}>Select a shipper to view details</p>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>{shipper.shipper_id}</h3>

      <div style={styles.section}>
        <div style={styles.label}>Name</div>
        <div style={styles.value}>{shipper.name || '-'}</div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>Status</div>
        <div style={{ ...styles.value, ...styles.status(shipper.current_status) }}>
          {shipper.current_status}
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>Location</div>
        <div style={styles.value}>
          {shipper.current_lat?.toFixed(6)}, {shipper.current_lon?.toFixed(6)}
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>Speed</div>
        <div style={styles.value}>{shipper.current_speed_kmh?.toFixed(1) || 0} km/h</div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>ETA (Order)</div>
        <div style={styles.value}>
          {shipper.eta_minutes ? `${shipper.eta_minutes} min` : '-'}
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>Completed Orders</div>
        <div style={styles.value}>{shipper.completed_count || 0}</div>
      </div>

      <div style={styles.section}>
        <div style={styles.label}>Total Distance</div>
        <div style={styles.value}>{shipper.total_distance_km?.toFixed(1) || 0} km</div>
      </div>
    </div>
  )
}

const styles = {
  container: {
    padding: 'var(--spacing-lg)',
    overflow: 'auto',
  },
  title: { fontSize: 'var(--font-size-lg)', marginBottom: 'var(--spacing-lg)', margin: 0 },
  section: { marginBottom: 'var(--spacing-lg)' },
  label: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)', marginBottom: 'var(--spacing-xs)' },
  value: { fontSize: 'var(--font-size-base)', color: 'var(--text)' },
  placeholder: { color: 'var(--text2)', textAlign: 'center' },
  status: (status) => {
    const colors = {
      DELIVERING: 'var(--green)',
      IDLE: 'var(--amber)',
      OFFLINE: 'var(--red)',
      AVAILABLE: 'var(--blue)',
    }
    return { color: colors[status] || 'var(--text)' }
  },
}
