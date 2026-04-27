/**
 * components/TopBar.jsx — Header component
 *
 * Logo, status indicator, live clock
 */

import { useState, useEffect } from 'react'

export const TopBar = ({ wsConnected, shipperCount, totalShippers }) => {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div style={styles.container}>
      <div style={styles.left}>
        <h1 style={styles.title}>🚚 ShipTrack</h1>
      </div>
      <div style={styles.center}>
        <span style={styles.clock}>
          {time.toLocaleTimeString()}
        </span>
      </div>
      <div style={styles.right}>
        <div style={styles.statusDot(wsConnected)}>
          {wsConnected ? '🟢' : '🔴'}
        </div>
        <span>{shipperCount}/{totalShippers || shipperCount} online</span>
      </div>
    </div>
  )
}

const styles = {
  container: {
    minHeight: '46px',
    background: 'var(--bg2)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    paddingLeft: 'var(--spacing-lg)',
    paddingRight: 'var(--spacing-lg)',
    justifyContent: 'space-between',
  },
  left: { flex: 0 },
  center: { flex: 1, textAlign: 'center', minWidth: 120 },
  right: { flex: 0, display: 'flex', gap: 'var(--spacing-md)', alignItems: 'center', fontSize: 'var(--font-size-sm)' },
  title: { fontSize: 'var(--font-size-xl)', margin: 0, color: 'var(--green)' },
  clock: { fontFamily: 'var(--mono)', color: 'var(--text2)' },
  statusDot: (active) => ({
    display: 'inline-block',
    fontSize: '16px',
    animation: active ? 'pulse 1s infinite' : 'none',
  }),
}
