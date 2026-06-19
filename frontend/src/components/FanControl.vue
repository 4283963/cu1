<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useFanWebSocket } from '../composables/useWebSocket'
import { fanApi } from '../api'
import FanCard from './FanCard.vue'

const fans = ref([])
const loading = ref(true)
const selectedFanId = ref(null)
const logs = ref([])
const logsLoading = ref(false)
const globalError = ref(null)
const refreshTimer = ref(null)

const fanLocalState = new Map()

function mergeFanUpdate(updatedFan) {
  const index = fans.value.findIndex(f => f.id === updatedFan.id)
  if (index !== -1) {
    fans.value[index] = { ...fans.value[index], ...updatedFan }
  } else {
    fans.value.push(updatedFan)
  }
}

function handleWebSocketMessage(message) {
  if (message.type === 'fan_status_update') {
    const updatedFan = message.data
    mergeFanUpdate(updatedFan)
    if (selectedFanId.value === updatedFan.id) {
      showLogs(updatedFan.id, true)
    }
  }
}

const { isConnected, connectionError, sendControlAction } = useFanWebSocket(handleWebSocketMessage)

async function loadFans(silent = false) {
  try {
    if (!silent) {
      loading.value = true
    }
    globalError.value = null
    const data = await fanApi.getFans()
    if (Array.isArray(data)) {
      fans.value = data
    }
  } catch (e) {
    globalError.value = e.message || '加载失败，请稍后重试'
    if (!silent) {
      console.error('Failed to load fans:', e)
    }
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

async function handleToggle(fanId) {
  try {
    const fan = fans.value.find(f => f.id === fanId)
    if (fan) {
      fanLocalState.set(fanId, { ...fan, is_running: !fan.is_running })
    }
    const sent = sendControlAction(fanId, 'TOGGLE', 'ws_manual')
    if (!sent) {
      try {
        await fanApi.toggleFan(fanId)
      } catch (fallbackError) {
        console.error('Fallback toggle failed:', fallbackError)
      }
    }
  } catch (e) {
    console.error('Failed to toggle fan:', e)
  }
}

async function handleOn(fanId) {
  try {
    const fan = fans.value.find(f => f.id === fanId)
    if (fan) {
      fanLocalState.set(fanId, { ...fan, is_running: true })
    }
    const sent = sendControlAction(fanId, 'ON', 'ws_manual')
    if (!sent) {
      try {
        await fanApi.turnFanOn(fanId)
      } catch (fallbackError) {
        console.error('Fallback on failed:', fallbackError)
      }
    }
  } catch (e) {
    console.error('Failed to turn on fan:', e)
  }
}

async function handleOff(fanId) {
  try {
    const fan = fans.value.find(f => f.id === fanId)
    if (fan) {
      fanLocalState.set(fanId, { ...fan, is_running: false })
    }
    const sent = sendControlAction(fanId, 'OFF', 'ws_manual')
    if (!sent) {
      try {
        await fanApi.turnFanOff(fanId)
      } catch (fallbackError) {
        console.error('Fallback off failed:', fallbackError)
      }
    }
  } catch (e) {
    console.error('Failed to turn off fan:', e)
  }
}

let logsDebounceTimer = null
async function showLogs(fanId, force = false) {
  if (selectedFanId.value === fanId && !force) {
    selectedFanId.value = null
    logs.value = []
    return
  }

  if (logsDebounceTimer) {
    clearTimeout(logsDebounceTimer)
  }

  if (!force) {
    logsDebounceTimer = setTimeout(async () => {
      await _loadLogs(fanId)
    }, 200)
  } else {
    await _loadLogs(fanId)
  }
}

async function _loadLogs(fanId) {
  try {
    selectedFanId.value = fanId
    logsLoading.value = true
    logs.value = await fanApi.getFanLogs(fanId)
  } catch (e) {
    console.error('Failed to load logs:', e)
  } finally {
    logsLoading.value = false
  }
}

const runningCount = () => fans.value.filter(f => f.is_running).length

const formattedLogTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

watch(isConnected, (connected) => {
  if (connected) {
    loadFans(true)
  }
})

onMounted(() => {
  loadFans()
  refreshTimer.value = setInterval(() => {
    if (!isConnected.value) {
      loadFans(true)
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
  if (logsDebounceTimer) {
    clearTimeout(logsDebounceTimer)
  }
})
</script>

<template>
  <div>
    <div v-if="globalError" class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm">
      ⚠️ {{ globalError }}
    </div>

    <div v-if="connectionError" class="mb-4 p-3 bg-warning-50 border border-warning-200 rounded-lg text-warning-700 text-sm">
      🔌 {{ connectionError }}
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">排风扇总数</p>
            <p class="text-3xl font-bold text-gray-800">{{ fans.length }}</p>
          </div>
          <div class="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center">
            <span class="text-3xl">🌀</span>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">运行中</p>
            <p class="text-3xl font-bold text-primary-600">{{ runningCount() }}</p>
          </div>
          <div class="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center">
            <span class="text-3xl">💨</span>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">已停止</p>
            <p class="text-3xl font-bold text-gray-500">{{ fans.length - runningCount() }}</p>
          </div>
          <div class="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center">
            <span class="text-3xl">⏸️</span>
          </div>
        </div>
        <div class="mt-3 flex items-center gap-2 text-sm">
          <span
            :class="[
              'w-2 h-2 rounded-full transition-colors',
              isConnected ? 'bg-primary-500 animate-pulse' : 'bg-gray-300'
            ]"
          ></span>
          <span class="text-gray-500">
            {{ isConnected ? '控制通道已连接' : '控制通道离线-使用HTTP备用' }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">排风扇控制</h2>
      <button
        @click="loadFans"
        class="text-sm text-primary-600 hover:text-primary-700 transition-colors py-1 px-2 rounded hover:bg-primary-50"
      >
        🔄 刷新状态
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent"></div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="fan in fans" :key="fan.id">
        <FanCard
          :fan="fan"
          @toggle="handleToggle"
          @on="handleOn"
          @off="handleOff"
        />
        <button
          @click="showLogs(fan.id)"
          class="w-full mt-2 py-2 text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          {{ selectedFanId === fan.id ? '▼ 收起日志' : '▶ 查看操作日志' }}
        </button>

        <div
          v-if="selectedFanId === fan.id"
          class="mt-2 bg-white rounded-lg border border-gray-100 p-4"
        >
          <h4 class="text-sm font-medium text-gray-700 mb-3">操作日志</h4>
          <div v-if="logsLoading" class="flex justify-center py-4">
            <div class="animate-spin rounded-full h-5 w-5 border-2 border-primary-500 border-t-transparent"></div>
          </div>
          <div v-else-if="logs.length === 0" class="text-sm text-gray-400 text-center py-4">
            暂无操作记录
          </div>
          <div v-else class="space-y-2 max-h-60 overflow-y-auto">
            <div
              v-for="log in logs"
              :key="log.id"
              class="flex items-center justify-between text-sm py-2 border-b border-gray-50"
            >
              <div class="flex items-center gap-2">
                <span
                  :class="[
                    'px-2 py-0.5 rounded text-xs font-medium',
                    log.action === 'ON'
                      ? 'bg-primary-100 text-primary-700'
                      : 'bg-gray-100 text-gray-700'
                  ]"
                >
                  {{ log.action === 'ON' ? '开启' : '关闭' }}
                </span>
                <span class="text-gray-500">{{ log.reason }}</span>
              </div>
              <span class="text-gray-400 text-xs">{{ formattedLogTime(log.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-8 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 class="text-sm font-medium text-gray-700 mb-3">💡 使用说明</h3>
      <ul class="text-sm text-gray-500 space-y-1">
        <li>• 点击「启动」/「关闭」按钮可快速切换排风扇状态</li>
        <li>• 控制指令优先通过 WebSocket 实时发送，断开时自动降级为 HTTP</li>
        <li>• 系统已内置防抖保护，防止高频点击造成的并发冲突</li>
        <li>• 适宜蚕宝宝生长环境：温度 22-28°C，湿度 55-80%</li>
        <li>• 当温度或湿度超出适宜范围时，请及时开启排风扇通风</li>
      </ul>
    </div>
  </div>
</template>
