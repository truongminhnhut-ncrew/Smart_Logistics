/**
 * components/RightPanel.jsx — Shipper detail panel with Orders & Incidents tabs
 */

import { useState, useEffect } from 'react'
import { incidentsAPI } from '../services/api'

export const RightPanel = ({ shipper = null }) => {
  const [activeTab, setActiveTab] = useState('orders')
  const [incidents, setIncidents] = useState([])

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

  if (!shipper) {
    return (
      <div style={styles.container}>
        <p style={styles.placeholder}>Select a shipper to view details</p>
      </div>
    )
  }

  const handleResolve = async (incidentId) => {
    try {
      await incidentsAPI.resolve(incidentId)
      setIncidents(prev => prev.map(inc => 
        inc.incident_id === incidentId ? { ...inc, status: 'RESOLVED' } : inc
      ))
    } catch (e) {
      console.error('Failed to resolve incident:', e)
    }
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>{shipper.shipper_id}</h3>
      <div style={styles.statusBadge(shipper.status)}>{shipper.status}</div>

      <div style={styles.tabs}>
        <button 
          style={styles.tab(activeTab === 'orders')} 
          onClick={() => setActiveTab('orders')}
        >
          Orders
        </button>
        <button 
          style={styles.tab(activeTab === 'incidents')} 
          onClick={() => setActiveTab('incidents')}
        >
          Incidents
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'orders' ? (
          <div style={styles.tabContent}>
            <div style={styles.section}>
              <div style={styles.label}>Order ID</div>
              <div style={styles.value}>{shipper.order_id || 'None'}</div>
            </div>
            <div style={styles.section}>
              <div style={styles.label}>Current Speed</div>
              <div style={styles.value}>{shipper.speed_kmh} km/h</div>
            </div>
            <div style={styles.section}>
              <div style={styles.label}>Position</div>
              <div style={styles.value}>{shipper.lat.toFixed(5)}, {shipper.lon.toFixed(5)}</div>
            </div>
          </div>
        ) : (
          <div style={styles.tabContent}>
            {incidents.length === 0 ? (
              <div style={styles.placeholder}>No incidents recorded</div>
            ) : (
              incidents.map(inc => (
                <div key={inc.incident_id} style={styles.incidentCard(inc.status)}>
                  <div style={styles.incidentHeader}>
                    <span style={styles.incidentType}>{inc.incident_type}</span>
                    <span style={styles.incidentId}>{inc.incident_id}</span>
                  </div>
                  <div style={styles.incidentDesc}>{inc.description}</div>
                  {inc.status === 'ACTIVE' && (
                    <button 
                      style={styles.resolveBtn}
                      onClick={() => handleResolve(inc.incident_id)}
                    >
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
  section: { marginBottom: 'var(--spacing-md)' },
  label: { fontSize: 'var(--font-size-sm)', color: 'var(--text2)', marginBottom: '2px' },
  value: { fontSize: 'var(--font-size-base)' },
  placeholder: { color: 'var(--text2)', textAlign: 'center', marginTop: 'var(--spacing-xl)', fontSize: 'var(--font-size-sm)' },
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
  }
}
