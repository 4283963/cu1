<script setup>
import { computed } from 'vue'

const props = defineProps({
  nodeName: {
    type: String,
    required: true
  },
  location: {
    type: String,
    required: true
  },
  temperature: {
    type: Number,
    required: true
  },
  humidity: {
    type: Number,
    required: true
  },
  timestamp: {
    type: String,
    required: true
  }
})

const tempStatus = computed(() => {
  if (props.temperature < 20 || props.temperature > 30) return 'danger'
  if (props.temperature < 22 || props.temperature > 28) return 'warning'
  return 'normal'
})

const humStatus = computed(() => {
  if (props.humidity < 50 || props.humidity > 85) return 'danger'
  if (props.humidity < 55 || props.humidity > 80) return 'warning'
  return 'normal'
})

const formattedTime = computed(() => {
  const date = new Date(props.timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
})

const tempColorClass = computed(() => {
  switch (tempStatus.value) {
    case 'danger': return 'text-danger-600 bg-danger-50 border-danger-200'
    case 'warning': return 'text-warning-600 bg-warning-50 border-warning-200'
    default: return 'text-primary-600 bg-primary-50 border-primary-200'
  }
})

const humColorClass = computed(() => {
  switch (humStatus.value) {
    case 'danger': return 'text-danger-600 bg-danger-50 border-danger-200'
    case 'warning': return 'text-warning-600 bg-warning-50 border-warning-200'
    default: return 'text-blue-600 bg-blue-50 border-blue-200'
  }
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="font-semibold text-gray-800">{{ nodeName }}</h3>
        <p class="text-xs text-gray-400">{{ location }}</p>
      </div>
      <span class="text-xs text-gray-400">{{ formattedTime }}</span>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div
        :class="[
          'rounded-lg p-4 border transition-all duration-300',
          tempColorClass
        ]"
      >
        <div class="flex items-center gap-2 mb-1">
          <span class="text-lg">🌡️</span>
          <span class="text-xs font-medium">温度</span>
        </div>
        <div class="text-2xl font-bold">
          {{ temperature.toFixed(1) }}
          <span class="text-sm font-normal">°C</span>
        </div>
        <div
          v-if="tempStatus !== 'normal'"
          class="text-xs mt-1 opacity-75"
        >
          {{ tempStatus === 'warning' ? '⚠️ 注意' : '🚨 异常' }}
        </div>
      </div>

      <div
        :class="[
          'rounded-lg p-4 border transition-all duration-300',
          humColorClass
        ]"
      >
        <div class="flex items-center gap-2 mb-1">
          <span class="text-lg">💧</span>
          <span class="text-xs font-medium">湿度</span>
        </div>
        <div class="text-2xl font-bold">
          {{ humidity.toFixed(1) }}
          <span class="text-sm font-normal">%</span>
        </div>
        <div
          v-if="humStatus !== 'normal'"
          class="text-xs mt-1 opacity-75"
        >
          {{ humStatus === 'warning' ? '⚠️ 注意' : '🚨 异常' }}
        </div>
      </div>
    </div>

    <div class="mt-4 pt-3 border-t border-gray-100">
      <div class="flex justify-between text-xs text-gray-400">
        <span>适宜温度: 22-28°C</span>
        <span>适宜湿度: 55-80%</span>
      </div>
    </div>
  </div>
</template>
