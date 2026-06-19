const API_BASE = '/api'
const REQUEST_TIMEOUT = 8000
const MAX_RETRIES = 2

const pendingRequests = new Map()
const rateLimitMap = new Map()
const MIN_REQUEST_INTERVAL = 300

function checkRateLimit(key) {
  const now = Date.now()
  const last = rateLimitMap.get(key) || 0
  if (now - last < MIN_REQUEST_INTERVAL) {
    return false
  }
  rateLimitMap.set(key, now)
  return true
}

async function request(url, options = {}) {
  const requestKey = `${options.method || 'GET'}_${url}`

  if (pendingRequests.has(requestKey) && options.idempotent !== false) {
    return pendingRequests.get(requestKey)
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  let lastError = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const rateKey = `${requestKey}_${options.body || ''}`
      if (!checkRateLimit(rateKey)) {
        if (attempt < MAX_RETRIES) {
          await new Promise(resolve => setTimeout(resolve, 200))
          continue
        }
      }

      const response = await fetch(`${API_BASE}${url}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        signal: controller.signal,
        ...options
      })

      if (!response.ok) {
        if (response.status >= 500 && attempt < MAX_RETRIES) {
          await new Promise(resolve => setTimeout(resolve, 300 * (attempt + 1)))
          continue
        }
        const errorText = await response.text().catch(() => '')
        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`)
      }

      return await response.json()

    } catch (error) {
      lastError = error
      if (error.name === 'AbortError') {
        throw new Error('请求超时，请检查网络连接')
      }
      if (attempt < MAX_RETRIES) {
        await new Promise(resolve => setTimeout(resolve, 300 * (attempt + 1)))
      }
    } finally {
      clearTimeout(timeoutId)
    }
  }

  throw lastError || new Error('请求失败')
}

export const sensorApi = {
  getNodes: () => request('/sensors/nodes'),
  createNode: (data) => request('/sensors/nodes', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getNode: (id) => request(`/sensors/nodes/${id}`),
  getReadings: (limit = 100) => request(`/sensors/readings?limit=${limit}`, { idempotent: false }),
  getLatestReadings: () => request('/sensors/readings/latest', { idempotent: false }),
  getNodeReadings: (id, limit = 100) => request(`/sensors/nodes/${id}/readings?limit=${limit}`, { idempotent: false })
}

const fanRequestLocks = new Map()

async function executeFanRequest(fanId, action, fn) {
  const lockKey = `fan_${fanId}_${action}`

  if (fanRequestLocks.get(lockKey)) {
    throw new Error('操作过于频繁，请稍后再试')
  }

  fanRequestLocks.set(lockKey, true)
  try {
    return await fn()
  } finally {
    setTimeout(() => {
      fanRequestLocks.delete(lockKey)
    }, 400)
  }
}

export const fanApi = {
  getFans: () => request('/fans', { idempotent: false }),
  createFan: (data) => request('/fans', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getFan: (id) => request(`/fans/${id}`, { idempotent: false }),
  updateFan: (id, data) => request(`/fans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  toggleFan: (id, reason = 'manual') => executeFanRequest(id, 'toggle', () =>
    request(`/fans/${id}/toggle?reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    })
  ),
  turnFanOn: (id, reason = 'manual') => executeFanRequest(id, 'on', () =>
    request(`/fans/${id}/on?reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    })
  ),
  turnFanOff: (id, reason = 'manual') => executeFanRequest(id, 'off', () =>
    request(`/fans/${id}/off?reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    })
  ),
  getFanLogs: (id, limit = 50) => request(`/fans/${id}/logs?limit=${limit}`, { idempotent: false })
}

export const healthApi = {
  check: () => request('/health', { idempotent: false })
}

export const scheduleApi = {
  getSchedules: () => request('/schedules', { idempotent: false }),
  getSchedule: (id) => request(`/schedules/${id}`, { idempotent: false }),
  createSchedule: (data) => request('/schedules', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  updateSchedule: (id, data) => request(`/schedules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  deleteSchedule: (id) => request(`/schedules/${id}`, {
    method: 'DELETE'
  }),
  toggleSchedule: (id) => request(`/schedules/${id}/toggle`, {
    method: 'POST'
  })
}
