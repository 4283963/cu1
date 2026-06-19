<script setup>
import { ref, onMounted } from 'vue'
import Dashboard from './components/Dashboard.vue'
import FanControl from './components/FanControl.vue'
import ConnectionStatus from './components/ConnectionStatus.vue'
import { healthApi } from './api'

const activeTab = ref('dashboard')
const isBackendOnline = ref(false)

async function checkBackend() {
  try {
    await healthApi.check()
    isBackendOnline.value = true
  } catch (e) {
    isBackendOnline.value = false
  }
}

onMounted(() => {
  checkBackend()
  setInterval(checkBackend, 5000)
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50">
    <header class="bg-white shadow-sm border-b border-primary-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-3">
            <span class="text-3xl">🐛</span>
            <div>
              <h1 class="text-xl font-bold text-gray-800">蚕桑养殖监控系统</h1>
              <p class="text-xs text-gray-500">温湿度实时监控 · 排风扇远程控制</p>
            </div>
          </div>
          <ConnectionStatus :backend-online="isBackendOnline" />
        </div>
      </div>
    </header>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 mb-6">
        <nav class="flex gap-1 p-1">
          <button
            @click="activeTab = 'dashboard'"
            :class="[
              'flex-1 py-3 px-4 rounded-lg font-medium text-sm transition-all duration-200',
              activeTab === 'dashboard'
                ? 'bg-primary-500 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            ]"
          >
            📊 环境指标看板
          </button>
          <button
            @click="activeTab = 'fans'"
            :class="[
              'flex-1 py-3 px-4 rounded-lg font-medium text-sm transition-all duration-200',
              activeTab === 'fans'
                ? 'bg-primary-500 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            ]"
          >
            🌬️ 排风扇控制
          </button>
        </nav>
      </div>

      <div v-if="activeTab === 'dashboard'">
        <Dashboard />
      </div>
      <div v-else-if="activeTab === 'fans'">
        <FanControl />
      </div>
    </div>

    <footer class="mt-12 py-6 text-center text-gray-400 text-sm">
      <p>蚕桑养殖温湿度监控与排风扇远程控制系统 v1.0.0</p>
    </footer>
  </div>
</template>
