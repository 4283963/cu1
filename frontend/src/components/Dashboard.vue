<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useSensorWebSocket } from '../composables/useWebSocket'
import { sensorApi } from '../api'
import SensorCard from './SensorCard.vue'

const sensorData = reactive({})
const nodes = ref([])
const loading = ref(true)
const wsConnected = ref(false)

function handleWebSocketMessage(message) {
  if (message.type === 'connection_established') {
    wsConnected.value = true
  } else if (message.type === 'sensor_reading') {
    const data = message.data
    sensorData[data.sensor_node_id] = {
      ...data,
      timestamp: message.timestamp
    }
  }
}

const { isConnected, connectionError } = useSensorWebSocket(handleWebSocketMessage)

async function loadInitialData() {
  try {
    loading.value = true
    const [nodesData, readingsData] = await Promise.all([
      sensorApi.getNodes(),
      sensorApi.getLatestReadings()
    ])
    nodes.value = nodesData
    readingsData.forEach(reading => {
      sensorData[reading.sensor_node_id] = {
        id: reading.id,
        sensor_node_id: reading.sensor_node_id,
        sensor_node_name: reading.sensor_node.name,
        sensor_node_location: reading.sensor_node.location,
        temperature: reading.temperature,
        humidity: reading.humidity,
        timestamp: reading.timestamp
      }
    })
  } catch (e) {
    console.error('Failed to load initial data:', e)
  } finally {
    loading.value = false
  }
}

const activeNodes = () => nodes.value.filter(n => n.is_active)

const avgTemperature = () => {
  const readings = Object.values(sensorData)
  if (readings.length === 0) return 0
  return readings.reduce((sum, r) => sum + r.temperature, 0) / readings.length
}

const avgHumidity = () => {
  const readings = Object.values(sensorData)
  if (readings.length === 0) return 0
  return readings.reduce((sum, r) => sum + r.humidity, 0) / readings.length
}

const alertCount = () => {
  return Object.values(sensorData).filter(r => {
    return r.temperature < 22 || r.temperature > 28 || r.humidity < 55 || r.humidity > 80
  }).length
}

onMounted(() => {
  loadInitialData()
})
</script>

<template>
  <div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">平均温度</p>
            <p class="text-3xl font-bold text-gray-800">{{ avgTemperature().toFixed(1) }}°C</p>
          </div>
          <div class="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center">
            <span class="text-3xl">🌡️</span>
          </div>
        </div>
        <div class="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-primary-400 to-primary-600 transition-all duration-500"
            :style="{ width: Math.min(100, Math.max(0, (avgTemperature() - 15) / 15 * 100)) + '%' }"
          ></div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">平均湿度</p>
            <p class="text-3xl font-bold text-gray-800">{{ avgHumidity().toFixed(1) }}%</p>
          </div>
          <div class="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
            <span class="text-3xl">💧</span>
          </div>
        </div>
        <div class="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-500"
            :style="{ width: avgHumidity() + '%' }"
          ></div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 mb-1">异常节点</p>
            <p
              :class="[
                'text-3xl font-bold',
                alertCount() > 0 ? 'text-danger-600' : 'text-primary-600'
              ]"
            >{{ alertCount() }}</p>
          </div>
          <div
            :class="[
              'w-14 h-14 rounded-full flex items-center justify-center',
              alertCount() > 0 ? 'bg-danger-100' : 'bg-primary-100'
            ]"
          >
            <span class="text-3xl">{{ alertCount() > 0 ? '🚨' : '✅' }}</span>
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
            {{ isConnected ? '实时数据推送中' : '连接断开' }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">监控节点实时数据</h2>
      <span class="text-sm text-gray-400">
        共 {{ activeNodes().length }} 个监控节点
      </span>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent"></div>
    </div>

    <div v-else-if="Object.keys(sensorData).length === 0" class="text-center py-12">
      <span class="text-5xl mb-4 block">📡</span>
      <p class="text-gray-500">等待传感器数据...</p>
      <p class="text-sm text-gray-400 mt-2">请确保后端服务已启动</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <SensorCard
        v-for="node in activeNodes()"
        :key="node.id"
        :node-name="sensorData[node.id]?.sensor_node_name || node.name"
        :location="sensorData[node.id]?.sensor_node_location || node.location"
        :temperature="sensorData[node.id]?.temperature || 0"
        :humidity="sensorData[node.id]?.humidity || 0"
        :timestamp="sensorData[node.id]?.timestamp || new Date().toISOString()"
      />
    </div>

    <div
      v-if="connectionError"
      class="mt-4 p-4 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm"
    >
      {{ connectionError }}
    </div>
  </div>
</template>
