import { ref, onMounted, onUnmounted } from 'vue'

export function useSensorWebSocket(onMessage) {
  const isConnected = ref(false)
  const connectionError = ref(null)
  let ws = null
  let reconnectTimer = null

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/sensors/ws`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        isConnected.value = true
        connectionError.value = null
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (onMessage) {
            onMessage(data)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (error) => {
        connectionError.value = 'WebSocket 连接错误'
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        isConnected.value = false
        scheduleReconnect()
      }
    } catch (e) {
      connectionError.value = '无法建立 WebSocket 连接'
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    reconnectTimer = setTimeout(() => {
      connect()
    }, 3000)
  }

  function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    connectionError,
    send,
    disconnect
  }
}

export function useFanWebSocket(onMessage) {
  const isConnected = ref(false)
  const connectionError = ref(null)
  let ws = null
  let reconnectTimer = null

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/fans/ws`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        isConnected.value = true
        connectionError.value = null
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (onMessage) {
            onMessage(data)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (error) => {
        connectionError.value = 'WebSocket 连接错误'
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        isConnected.value = false
        scheduleReconnect()
      }
    } catch (e) {
      connectionError.value = '无法建立 WebSocket 连接'
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    reconnectTimer = setTimeout(() => {
      connect()
    }, 3000)
  }

  function sendControlAction(fanId, action, reason = 'ws_manual') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'control_action',
        data: {
          fan_id: fanId,
          action: action,
          reason: reason
        }
      }))
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    connectionError,
    sendControlAction,
    disconnect
  }
}
