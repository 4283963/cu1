<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  fan: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['toggle', 'on', 'off'])

const controlling = ref(false)
const DEBOUNCE_MS = 500

const formattedTime = computed(() => {
  if (!props.fan.last_updated) return ''
  const date = new Date(props.fan.last_updated)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
})

function withLock(fn) {
  if (controlling.value) return
  controlling.value = true
  try {
    fn()
  } finally {
    setTimeout(() => {
      controlling.value = false
    }, DEBOUNCE_MS)
  }
}

function handleToggle() {
  withLock(() => {
    emit('toggle', props.fan.id)
  })
}

function handleOn() {
  withLock(() => {
    emit('on', props.fan.id)
  })
}

function handleOff() {
  withLock(() => {
    emit('off', props.fan.id)
  })
}

const showOnButton = computed(() => !props.fan.is_running && !controlling.value)
const showOffButton = computed(() => props.fan.is_running && !controlling.value)
</script>

<template>
  <div
    :class="[
      'rounded-xl shadow-sm border p-5 transition-all duration-300',
      fan.is_running
        ? 'bg-primary-50 border-primary-200'
        : 'bg-white border-gray-100'
    ]"
  >
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div
          :class="[
            'w-12 h-12 rounded-full flex items-center justify-center text-2xl',
            fan.is_running ? 'bg-primary-100' : 'bg-gray-100'
          ]"
        >
          <span :class="{ 'animate-spin-slow': fan.is_running }">🌀</span>
        </div>
        <div>
          <h3 class="font-semibold text-gray-800">{{ fan.name }}</h3>
          <p class="text-xs text-gray-400">{{ fan.location }}</p>
        </div>
      </div>
      <div
        :class="[
          'px-3 py-1 rounded-full text-xs font-medium transition-all',
          fan.is_running
            ? 'bg-primary-500 text-white'
            : 'bg-gray-200 text-gray-500'
        ]"
      >
        {{ controlling ? '处理中...' : (fan.is_running ? '运行中' : '已停止') }}
      </div>
    </div>

    <div class="grid grid-cols-3 gap-2 mb-4">
      <button
        @click="handleOn"
        :disabled="fan.is_running || controlling"
        :class="[
          'py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 select-none',
          fan.is_running || controlling
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-primary-500 text-white hover:bg-primary-600 active:scale-95 shadow-sm hover:shadow'
        ]"
      >
        <span v-if="controlling && !fan.is_running">...</span>
        <span v-else>开启</span>
      </button>
      <button
        @click="handleToggle"
        :disabled="controlling"
        :class="[
          'py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 select-none',
          controlling
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-warning-500 text-white hover:bg-warning-600 active:scale-95 shadow-sm hover:shadow'
        ]"
      >
        <span v-if="controlling">处理中</span>
        <span v-else>{{ fan.is_running ? '一键关闭' : '一键启动' }}</span>
      </button>
      <button
        @click="handleOff"
        :disabled="!fan.is_running || controlling"
        :class="[
          'py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 select-none',
          !fan.is_running || controlling
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-danger-500 text-white hover:bg-danger-600 active:scale-95 shadow-sm hover:shadow'
        ]"
      >
        <span v-if="controlling && fan.is_running">...</span>
        <span v-else>关闭</span>
      </button>
    </div>

    <div class="flex items-center justify-between text-xs text-gray-400 pt-3 border-t"
      :class="fan.is_running ? 'border-primary-200' : 'border-gray-100'"
    >
      <span>
        {{ fan.is_auto ? '⚙️ 自动模式' : '👆 手动模式' }}
      </span>
      <span>最后更新: {{ formattedTime }}</span>
    </div>
  </div>
</template>
