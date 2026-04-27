/**
 * components/ShipperList.jsx — Left panel shipper list
 */

export const ShipperList = ({ shippers = [], selectedId, onSelect }) => {
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Shippers ({shippers.length})</h2>
      <div style={styles.list}>
        {shippers.map(shipper => (
          <div
            key={shipper.shipper_id}
            style={styles.item(selectedId === shipper.shipper_id)}
            onClick={() => onSelect(shipper.shipper_id)}
          >
            <div style={styles.statusDot(shipper.current_status)}></div>
            <div style={styles.info}>
              <div style={styles.id}>{shipper.shipper_id}</div>
              <div style={styles.speed}>{shipper.current_speed_kmh?.toFixed(1) || 0}km/h</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const statusColors = {
  DELIVERING: 'var(--green)',
  IDLE: 'var(--amber)',
  OFFLINE: 'var(--red)',
  AVAILABLE: 'var(--blue)',
  ASSIGNED: 'var(--purple)',
}

const styles = {
  container: {
    width: '250px',
    borderRight: '1px solid var(--border)',
    padding: 'var(--spacing-lg)',
    overflow: 'auto',
  },
  title: { fontSize: 'var(--font-size-lg)', marginBottom: 'var(--spacing-md)', margin: 0 },
  list: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' },
  item: (selected) => ({
    padding: 'var(--spacing-md)',
    background: selected ? 'var(--bg3)' : 'transparent',
    border: `1px solid ${selected ? 'var(--green)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    display: 'flex',
    gap: 'var(--spacing-md)',
    alignItems: 'center',
  }),
  statusDot: (status) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: statusColors[status] || 'var(--text2)',
  }),
  info: { flex: 1, minWidth: 0 },
  id: { fontSize: 'var(--font-size-sm)', color: 'var(--text)' },
  speed: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)' },
}
