import { ref, onMounted, onUnmounted } from 'vue'

function createWebSocketConnection(wsUrl, onMessage, channelName) {
  const isConnected = ref(false)
  const connectionError = ref(null)
  const reconnectAttempts = ref(0)
  const MAX_RECONNECT_DELAY = 10000
  const MAX_RECONNECT_ATTEMPTS = 20

  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null
  let isManuallyDisconnected = false

  function getReconnectDelay() {
    const baseDelay = 1000
    const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts.value), MAX_RECONNECT_DELAY)
    return delay
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        } catch (e) {
        }
      }
    }, 30000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function connect() {
    if (isManuallyDisconnected) return
    if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
      connectionError.value = '连接失败次数过多，请刷新页面重试'
      return
    }

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        isConnected.value = true
        connectionError.value = null
        reconnectAttempts.value = 0
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (onMessage) {
            onMessage(data)
          }
        } catch (e) {
        }
      }

      ws.onerror = (error) => {
        if (!connectionError.value) {
          connectionError.value = '连接出现异常，正在尝试恢复...'
        }
      }

      ws.onclose = (event) => {
        isConnected.value = false
        stopHeartbeat()
        if (!isManuallyDisconnected) {
          reconnectAttempts.value++
          scheduleReconnect()
        }
      }
    } catch (e) {
      connectionError.value = '无法建立连接'
      reconnectAttempts.value++
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    const delay = getReconnectDelay()
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  function send(data, timeout = 2000) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return false
    }
    try {
      ws.send(JSON.stringify(data))
      return true
    } catch (e) {
      return false
    }
  }

  function disconnect() {
    isManuallyDisconnected = true
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      try {
        ws.close()
      } catch (e) {
      }
      ws = null
    }
    isConnected.value = false
  }

  onMounted(() => {
    isManuallyDisconnected = false
    reconnectAttempts.value = 0
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    connectionError,
    reconnectAttempts,
    send,
    disconnect,
    connect
  }
}

export function useSensorWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/sensors/ws`
  return createWebSocketConnection(wsUrl, onMessage, 'sensor_data')
}

const fanRateLimitMap = new Map()
const FAN_MIN_INTERVAL = 400

export function useFanWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/fans/ws`
  const result = createWebSocketConnection(wsUrl, onMessage, 'fan_status')

  const originalSendControl = (fanId, action, reason = 'ws_manual') => {
    return result.send({
      type: 'control_action',
      data: {
        fan_id: fanId,
        action: action,
        reason: reason
      }
    })
  }

  function sendControlAction(fanId, action, reason = 'ws_manual') {
    const now = Date.now()
    const rateKey = `fan_${fanId}`
    const last = fanRateLimitMap.get(rateKey) || 0

    if (now - last < FAN_MIN_INTERVAL) {
      return false
    }
    fanRateLimitMap.set(rateKey, now)

    return originalSendControl(fanId, action, reason)
  }

  return {
    ...result,
    sendControlAction
  }
}
