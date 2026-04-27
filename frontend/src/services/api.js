/**
 * services/api.js — REST API client
 *
 * Makes HTTP calls to backend API
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Shippers API
export const shippersAPI = {
  getAll: () => api.get('/shippers'),
  getById: (id) => api.get(`/shippers/${id}`),
  getHistory: (id, limit = 50) => api.get(`/shippers/${id}/history?limit=${limit}`),
  getStatus: (id) => api.get(`/shippers/${id}/online-status`),
}

// Orders API
export const ordersAPI = {
  getAll: () => api.get('/orders'),
  getPending: () => api.get('/orders/pending'),
  getById: (id) => api.get(`/orders/${id}`),
  create: (data) => api.post('/orders', data),
  assign: (orderId, shipperId) =>
    api.patch(`/orders/${orderId}/assign`, { shipper_id: shipperId }),
  complete: (orderId) => api.patch(`/orders/${orderId}/complete`),
}

// Dashboard API
export const dashboardAPI = {
  getOverview: () => api.get('/stats/overview'),
  getFleetStats: () => api.get('/stats/fleet'),
  getTrackingStats: () => api.get('/stats/tracking-events'),
  getRecentEvents: (minutes = 5, limit = 100) =>
    api.get(`/stats/recent-events?minutes=${minutes}&limit=${limit}`),
}

// Incidents API
export const incidentsAPI = {
  create: (data) => api.post('/incidents', data),
  getById: (id) => api.get(`/incidents/${id}`),
  getByShipper: (shipperId, limit = 100) =>
    api.get(`/incidents/shipper/${shipperId}?limit=${limit}`),
  getRecentByShipper: (shipperId, limit = 5) =>
    api.get(`/incidents/shipper/${shipperId}/recent?limit=${limit}`),
  getUnresolved: () => api.get('/incidents'),
  resolve: (id) => api.patch(`/incidents/${id}/resolve`),
  getUnresolvedCount: () => api.get('/incidents/stats/unresolved-count'),
  bulkImport: (incidents) => api.post('/incidents/bulk', { incidents }),
}

export default api
