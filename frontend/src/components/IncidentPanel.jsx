import { useState } from 'react';

const INCIDENT_TYPES = [
  { type: 'TRAFFIC_JAM', label: '🚗 Kẹt xe', color: '#f59e0b', severity: 'MEDIUM' },
  { type: 'HEAVY_RAIN', label: '🌧️ Mưa lớn', color: '#3b82f6', severity: 'HIGH' },
  { type: 'CUSTOMER_ABSENT', label: '👤 Khách vắng', color: '#8b5cf6', severity: 'LOW' },
  { type: 'VEHICLE_BREAKDOWN', label: '🔧 Hư xe', color: '#ef4444', severity: 'HIGH' },
  { type: 'LOST_CONNECTION', label: '🔋 Mất kết nối', color: '#6b7280', severity: 'MEDIUM' },
];

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function IncidentPanel({ selectedShipper, onIncidentApplied }) {
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const applyIncident = async (incidentType) => {
    if (!selectedShipper) {
      alert('Vui lòng chọn shipper trước khi tạo sự cố!');
      return;
    }
    setLoading(true);
    setLastResult(null);
    try {
      const res = await fetch(`${API_BASE}/simulation/incident/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shipper_id: selectedShipper,
          incident_type: incidentType,
        }),
      });
      const data = await res.json();
      setLastResult(data);
      if (onIncidentApplied) onIncidentApplied(data);
    } catch (err) {
      setLastResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const resolveIncident = async () => {
    if (!selectedShipper) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulation/incident/resolve/${selectedShipper}`, {
        method: 'POST',
      });
      const data = await res.json();
      setLastResult({ resolved: true, ...data });
      if (onIncidentApplied) onIncidentApplied({ resolved: true });
    } catch (err) {
      setLastResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: 12,
      padding: 16,
      marginBottom: 12,
      border: '1px solid #334155',
    }}>
      <h3 style={{ color: '#f8fafc', margin: '0 0 12px 0', fontSize: 14, fontWeight: 600 }}>
        ⚠️ Tạo Sự Cố {selectedShipper ? `— ${selectedShipper}` : ''}
      </h3>

      {!selectedShipper && (
        <p style={{ color: '#94a3b8', fontSize: 12, margin: 0 }}>
          Chọn shipper trên bản đồ hoặc danh sách để tạo sự cố
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {INCIDENT_TYPES.map((inc) => (
          <button
            key={inc.type}
            onClick={() => applyIncident(inc.type)}
            disabled={loading || !selectedShipper}
            style={{
              background: selectedShipper ? inc.color + '22' : '#334155',
              border: `1px solid ${selectedShipper ? inc.color : '#475569'}`,
              borderRadius: 8,
              padding: '8px 4px',
              color: selectedShipper ? inc.color : '#64748b',
              cursor: selectedShipper ? 'pointer' : 'not-allowed',
              fontSize: 11,
              fontWeight: 500,
              transition: 'all 0.2s',
              opacity: loading ? 0.5 : 1,
            }}
          >
            {inc.label}
          </button>
        ))}

        {/* Resolve button */}
        <button
          onClick={resolveIncident}
          disabled={loading || !selectedShipper}
          style={{
            background: selectedShipper ? '#10b98122' : '#334155',
            border: `1px solid ${selectedShipper ? '#10b981' : '#475569'}`,
            borderRadius: 8,
            padding: '8px 4px',
            color: selectedShipper ? '#10b981' : '#64748b',
            cursor: selectedShipper ? 'pointer' : 'not-allowed',
            fontSize: 11,
            fontWeight: 500,
            gridColumn: 'span 3',
          }}
        >
          ✅ Giải quyết sự cố
        </button>
      </div>

      {/* Result display */}
      {lastResult && (
        <div style={{
          marginTop: 10,
          padding: 8,
          borderRadius: 6,
          background: lastResult.error ? '#7f1d1d' : lastResult.resolved ? '#064e3b' : '#1e3a5f',
          fontSize: 11,
          color: '#e2e8f0',
        }}>
          {lastResult.error ? (
            <span>❌ {lastResult.error}</span>
          ) : lastResult.resolved ? (
            <span>✅ Đã giải quyết — {lastResult.status}</span>
          ) : (
            <>
              <div>📍 {lastResult.incident_type} — Severity: {lastResult.severity}</div>
              <div>⏱️ Delay: ~{lastResult.estimated_delay} phút</div>
              <div>💡 {lastResult.recommended_action}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}