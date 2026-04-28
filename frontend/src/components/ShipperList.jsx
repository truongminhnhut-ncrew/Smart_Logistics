/**
 * components/ShipperList.jsx — Left panel shipper list
 */

const statusColors = {
  DELIVERING: 'var(--green)',
  IDLE: 'var(--amber)',
  HEADING_TO_WAREHOUSE: 'var(--purple)',
  AT_WAREHOUSE: 'var(--blue)',
  DELIVERED: 'var(--green)',
  OFFLINE: 'var(--red)',
}

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
            <div style={styles.statusDot(shipper.status)}></div>
            <div style={styles.info}>
              <div style={styles.id}>{shipper.shipper_id}</div>
              <div style={styles.speed}>{shipper.speed_kmh?.toFixed(1) || 0}km/h</div>
            </div>
            <div style={styles.phaseBadge(shipper.status)}>{shipper.status}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  container: {
    width: '250px',
    borderRight: '1px solid var(--border)',
    padding: 'var(--spacing-lg)',
    overflow: 'auto',
    background: 'var(--bg2)',
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
    transition: 'all 0.2s ease',
  }),
  statusDot: (status) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: statusColors[status] || 'var(--text2)',
    boxShadow: status === 'DELIVERING' ? '0 0 5px var(--green)' : 'none',
  }),
  info: { flex: 1, minWidth: 0 },
  id: { fontSize: 'var(--font-size-sm)', fontWeight: 'bold', color: 'var(--text)' },
  speed: { fontSize: '10px', color: 'var(--text2)' },
  phaseBadge: (status) => ({
    fontSize: '8px',
    padding: '2px 4px',
    borderRadius: '4px',
    background: 'var(--bg)',
    color: statusColors[status] || 'var(--text2)',
    border: `1px solid ${statusColors[status] || 'var(--border)'}`,
  })
}
