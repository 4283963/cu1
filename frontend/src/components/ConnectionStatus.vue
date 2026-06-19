<script setup>
defineProps({
  backendOnline: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="flex items-center gap-4">
    <div class="flex items-center gap-2 text-sm">
      <span
        :class="[
          'w-2 h-2 rounded-full transition-colors duration-300',
          backendOnline ? 'bg-primary-500 animate-pulse-green' : 'bg-gray-300'
        ]"
      ></span>
      <span :class="backendOnline ? 'text-primary-600' : 'text-gray-400'">
        {{ backendOnline ? '后端服务正常' : '后端服务离线' }}
      </span>
    </div>
  </div>
</template>
