/**
 * components/SimulationControls.jsx — Controls for the simulation flow
 */

import { simulationAPI } from '../services/api'

export const SimulationControls = ({ phase, onNearestFetched, onDispatch }) => {
  const handleStart = async () => {
    try {
      await simulationAPI.start()
    } catch (e) {
      console.error('Failed to start simulation:', e)
    }
  }

  const handleFetchNearest = async () => {
    try {
      const response = await simulationAPI.getNearest(3)
      onNearestFetched(response.data.nearest)
    } catch (e) {
      console.error('Failed to fetch nearest shippers:', e)
    }
  }

  const handleReset = async () => {
    try {
      await simulationAPI.reset()
    } catch (e) {
      console.error('Failed to reset simulation:', e)
    }
  }

  return (
    <div style={styles.container}>
      {phase === 'IDLE' && (
        <button style={styles.buttonPrimary} onClick={handleStart}>
          🚀 Bắt đầu giao hàng
        </button>
      )}

      {phase === 'STARTED' && (
        <button style={styles.buttonSecondary} onClick={handleFetchNearest}>
          🔍 Tìm 3 shipper gần kho nhất
        </button>
      )}

      {(phase === 'DISPATCHING' || phase === 'WAITING_FOR_ORDER' || phase === 'DELIVERING' || phase === 'COMPLETED') && (
        <button style={styles.buttonDanger} onClick={handleReset}>
          🔄 Reset Simulation
        </button>
      )}
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    gap: 'var(--spacing-md)',
    padding: 'var(--spacing-md)',
    background: 'var(--bg2)',
    borderBottom: '1px solid var(--border)',
    alignItems: 'center',
  },
  buttonPrimary: {
    padding: 'var(--spacing-sm) var(--spacing-lg)',
    background: 'var(--green)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  buttonSecondary: {
    padding: 'var(--spacing-sm) var(--spacing-lg)',
    background: 'var(--blue)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  buttonDanger: {
    padding: 'var(--spacing-sm) var(--spacing-lg)',
    background: 'var(--red)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 'bold',
  }
}
