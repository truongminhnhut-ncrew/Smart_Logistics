/**
 * components/Dashboard.jsx — Statistics dashboard
 */

export const Dashboard = ({ stats = null }) => {
  if (!stats) {
    return (
      <div style={styles.container}>
        <p style={styles.placeholder}>Loading...</p>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Dashboard</h2>

      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.cardLabel}>Active Shippers</div>
          <div style={styles.cardValue}>{stats.fleet?.online_count || 0}</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>Delivering</div>
          <div style={styles.cardValue}>{stats.fleet?.delivering_count || 0}</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>Total Distance</div>
          <div style={styles.cardValue}>{stats.fleet?.total_distance_km?.toFixed(0) || 0}km</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>In Transit</div>
          <div style={styles.cardValue}>{stats.orders?.in_transit || 0}</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>Delivered</div>
          <div style={styles.cardValue}>{stats.orders?.delivered || 0}</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>Pending</div>
          <div style={styles.cardValue}>{stats.orders?.pending || 0}</div>
        </div>
      </div>

      {stats.top_shippers && stats.top_shippers.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Top Shippers</h3>
          <div style={styles.list}>
            {stats.top_shippers.map((s, i) => (
              <div key={i} style={styles.listItem}>
                <span>{i + 1}. {s.shipper_id}</span>
                <span style={styles.listValue}>{s.completed_count} orders</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const styles = {
  container: { padding: 'var(--spacing-lg)' },
  title: { fontSize: 'var(--font-size-lg)', marginBottom: 'var(--spacing-lg)', margin: 0 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 'var(--spacing-lg)',
    marginBottom: 'var(--spacing-xl)',
  },
  card: {
    padding: 'var(--spacing-lg)',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
  },
  cardLabel: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)', marginBottom: 'var(--spacing-md)' },
  cardValue: { fontSize: 'var(--font-size-xl)', color: 'var(--green)', fontWeight: 'bold' },
  section: { marginTop: 'var(--spacing-xl)' },
  sectionTitle: { fontSize: 'var(--font-size-lg)', marginBottom: 'var(--spacing-md)', margin: 0 },
  list: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' },
  listItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: 'var(--spacing-md)',
    background: 'var(--bg2)',
    borderRadius: 'var(--radius-md)',
    fontSize: 'var(--font-size-sm)',
  },
  listValue: { color: 'var(--green)', fontWeight: 'bold' },
  placeholder: { textAlign: 'center', color: 'var(--text2)' },
}
