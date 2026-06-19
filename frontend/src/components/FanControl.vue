<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useFanWebSocket } from '../composables/useWebSocket'
import { fanApi } from '../api'
import FanCard from './FanCard.vue'

const fans = ref([])
const loading = ref(true)
const selectedFanId = ref(null)
const logs = ref([])
const logsLoading = ref(false)

function handleWebSocketMessage(message) {
  if (message.type === 'fan_status_update') {
    const updatedFan = message.data
    const index = fans.value.findIndex(f => f.id === updatedFan.id)
    if (index !== -1) {
      fans.value[index] = updatedFan
    }
  }
}

const { isConnected, sendControlAction } = useFanWebSocket(handleWebSocketMessage)

async function loadFans() {
  try {
    loading.value = true
    fans.value = await fanApi.getFans()
  } catch (e) {
    console.error('Failed to load fans:', e)
  } finally {
    loading.value = false
  }
}

async function handleToggle(fanId) {
  try {
    sendControlAction(fanId, 'TOGGLE', 'ws_manual')
  } catch (e) {
    console.error('Failed to toggle fan:', e)
  }
}

async function handleOn(fanId) {
  try {
    sendControlAction(fanId, 'ON', 'ws_manual')
  } catch (e) {
    console.error('Failed to turn on fan:', e)
  }
}

async function handleOff(fanId) {
  try {
    sendControlAction(fanId, 'OFF', 'ws_manual')
  } catch (e) {
    console.error('Failed to turn off fan:', e)
  }
}

async function showLogs(fanId) {
  if (selectedFanId.value === fanId) {
    selectedFanId.value = null
    logs.value = []
    return
  }
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

onMounted(() => {
  loadFans()
})
</script>

<template>
  <div>
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
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-primary-500 animate-pulse' : 'bg-gray-300'
            ]"
          ></span>
          <span class="text-gray-500">
            {{ isConnected ? '控制通道已连接' : '控制通道离线' }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">排风扇控制</h2>
      <button
        @click="loadFans"
        class="text-sm text-primary-600 hover:text-primary-700"
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
        <li>• 控制指令通过 WebSocket 实时发送，状态同步更新</li>
        <li>• 适宜蚕宝宝生长环境：温度 22-28°C，湿度 55-80%</li>
        <li>• 当温度或湿度超出适宜范围时，请及时开启排风扇通风</li>
      </ul>
    </div>
  </div>
</template>
