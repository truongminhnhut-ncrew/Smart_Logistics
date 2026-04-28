/**
 * services/api.js — REST API client
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Shippers API
export const shippersAPI = {
  getAll: () => api.get('/shippers'),
  getById: (id) => api.get(`/shippers/${id}`),
  getHistory: (id, limit = 50) => api.get(`/shippers/${id}/history?limit=${limit}`),
}

// Orders API
export const ordersAPI = {
  getAll: () => api.get('/orders'),
  getPending: () => api.get('/orders/pending'),
  getById: (id) => api.get(`/orders/${id}`),
  create: (data) => api.post('/orders', data),
  assign: (orderId, shipperId) => api.patch(`/orders/${orderId}/assign`, { shipper_id: shipperId }),
  complete: (orderId) => api.patch(`/orders/${orderId}/complete`),
  bulkImport: (orders) => api.post('/orders/bulk-import', orders),
}

// Dashboard API
export const dashboardAPI = {
  getOverview: () => api.get('/stats/overview'),
  getFleetStats: () => api.get('/stats/fleet'),
}

// Simulation API
export const simulationAPI = {
  start: () => api.post('/simulation/start'),
  getState: () => api.get('/simulation/state'),
  getShippers: () => api.get('/shippers'),
  getNearest: (n = 3) => api.get(`/simulation/nearest?top_n=${n}`),
  dispatch: (shipperIds) => api.post('/simulation/dispatch', { shipper_ids: shipperIds }),
  assignDelivery: (data) => api.post('/simulation/assign-delivery', data),
  complete: () => api.post('/simulation/complete'),
  reset: () => api.post('/simulation/reset'),
}

// Incidents API
export const incidentsAPI = {
  getAll: () => api.get('/incidents'),
  getActive: () => api.get('/incidents/active'),
  create: (data) => api.post('/incidents', data),
  resolve: (id) => api.patch(`/incidents/${id}/resolve`),
  getByShipper: (shipperId) => api.get(`/incidents/shipper/${shipperId}`),
}

export default api
