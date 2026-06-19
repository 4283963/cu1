const API_BASE = '/api'

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export const sensorApi = {
  getNodes: () => request('/sensors/nodes'),
  createNode: (data) => request('/sensors/nodes', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getNode: (id) => request(`/sensors/nodes/${id}`),
  getReadings: (limit = 100) => request(`/sensors/readings?limit=${limit}`),
  getLatestReadings: () => request('/sensors/readings/latest'),
  getNodeReadings: (id, limit = 100) => request(`/sensors/nodes/${id}/readings?limit=${limit}`)
}

export const fanApi = {
  getFans: () => request('/fans'),
  createFan: (data) => request('/fans', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getFan: (id) => request(`/fans/${id}`),
  updateFan: (id, data) => request(`/fans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  toggleFan: (id, reason = 'manual') => request(`/fans/${id}/toggle?reason=${encodeURIComponent(reason)}`, {
    method: 'POST'
  }),
  turnFanOn: (id, reason = 'manual') => request(`/fans/${id}/on?reason=${encodeURIComponent(reason)}`, {
    method: 'POST'
  }),
  turnFanOff: (id, reason = 'manual') => request(`/fans/${id}/off?reason=${encodeURIComponent(reason)}`, {
    method: 'POST'
  }),
  getFanLogs: (id, limit = 50) => request(`/fans/${id}/logs?limit=${limit}`)
}

export const healthApi = {
  check: () => request('/health')
}
