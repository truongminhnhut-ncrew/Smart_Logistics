/**
 * components/Dashboard.jsx — Statistics dashboard with active incidents
 */

import { useState, useEffect } from 'react'
import { incidentsAPI } from '../services/api'

export const Dashboard = ({ stats = null }) => {
  const [activeIncidents, setActiveIncidents] = useState([])

  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await incidentsAPI.getActive()
        setActiveIncidents(res.data)
      } catch (e) {
        console.error('Failed to fetch active incidents:', e)
      }
    }
    fetchIncidents()
    const interval = setInterval(fetchIncidents, 5000)
    return () => clearInterval(interval)
  }, [])

  if (!stats) {
    return (
      <div style={styles.container}>
        <p style={styles.placeholder}>Loading stats...</p>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Fleet Overview</h2>

      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.cardLabel}>Active Shippers</div>
          <div style={styles.cardValue}>{stats.fleet?.online_count || 0}</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardLabel}>Delivering</div>
          <div style={styles.cardValue}>{stats.fleet?.delivering_count || 0}</div>
        </div>

        <div style={{...styles.card, borderColor: activeIncidents.length > 0 ? 'var(--red)' : 'var(--border)'}}>
          <div style={styles.cardLabel}>Active Incidents</div>
          <div style={{...styles.cardValue, color: activeIncidents.length > 0 ? 'var(--red)' : 'var(--green)'}}>
            {activeIncidents.length}
          </div>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Active Incidents</h3>
        <div style={styles.incidentList}>
          {activeIncidents.length === 0 ? (
            <div style={styles.placeholder}>No active incidents 🟢</div>
          ) : (
            activeIncidents.map(inc => (
              <div key={inc.incident_id} style={styles.incidentItem}>
                <div style={styles.incidentInfo}>
                  <div style={styles.incidentShipper}>{inc.shipper_id}</div>
                  <div style={styles.incidentType}>{inc.incident_type}</div>
                </div>
                <div style={styles.incidentTime}>
                  {new Date(inc.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Top Shippers</h3>
        <div style={styles.list}>
          {stats.top_shippers?.map((s, i) => (
            <div key={i} style={styles.listItem}>
              <span>{i + 1}. {s.shipper_id}</span>
              <span style={styles.listValue}>{s.completed_count} orders</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const styles = {
  container: { padding: 'var(--spacing-lg)', flex: 1, overflowY: 'auto', background: 'var(--bg)' },
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
  sectionTitle: { fontSize: 'var(--font-size-base)', fontWeight: 'bold', marginBottom: 'var(--spacing-md)', margin: 0 },
  incidentList: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' },
  incidentItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 'var(--spacing-md)',
    background: 'rgba(255, 71, 87, 0.05)',
    border: '1px solid rgba(255, 71, 87, 0.2)',
    borderRadius: 'var(--radius-md)',
  },
  incidentInfo: { display: 'flex', flexDirection: 'column' },
  incidentShipper: { fontWeight: 'bold', fontSize: 'var(--font-size-sm)' },
  incidentType: { color: 'var(--red)', fontSize: '11px' },
  incidentTime: { fontSize: '10px', color: 'var(--text2)' },
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
  placeholder: { textAlign: 'center', color: 'var(--text2)', padding: 'var(--spacing-xl)', fontSize: 'var(--font-size-sm)' },
}
