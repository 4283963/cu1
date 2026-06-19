<script setup>
import { ref, computed, watch } from 'vue'
import { scheduleApi } from '../api'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  fans: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'saved'])

const WEEKDAYS = [
  { value: 0, label: '一', short: '一' },
  { value: 1, label: '二', short: '二' },
  { value: 2, label: '三', short: '三' },
  { value: 3, label: '四', short: '四' },
  { value: 4, label: '五', short: '五' },
  { value: 5, label: '六', short: '六' },
  { value: 6, label: '日', short: '日' }
]

const defaultForm = {
  name: '',
  fan_ids: [],
  weekdays: [],
  start_time: '08:00',
  end_time: '18:00',
  target_temperature: 26.0,
  is_enabled: true
}

const form = ref({ ...defaultForm })
const editingId = ref(null)
const saving = ref(false)
const errorMsg = ref('')

const isEditing = computed(() => editingId.value !== null)

const canSave = computed(() => {
  return (
    form.value.name.trim() !== '' &&
    form.value.fan_ids.length > 0 &&
    form.value.weekdays.length > 0 &&
    form.value.start_time !== '' &&
    form.value.end_time !== '' &&
    form.value.target_temperature >= 10 &&
    form.value.target_temperature <= 40
  )
})

const weekdayLabels = computed(() => {
  if (form.value.weekdays.length === 0) return '未选择'
  if (form.value.weekdays.length === 7) return '每天'
  const sorted = [...form.value.weekdays].sort((a, b) => a - b)
  return sorted.map(d => WEEKDAYS.find(w => w.value === d)?.short || '').join('、')
})

function toggleWeekday(day) {
  const idx = form.value.weekdays.indexOf(day)
  if (idx === -1) {
    form.value.weekdays.push(day)
  } else {
    form.value.weekdays.splice(idx, 1)
  }
}

function toggleFan(fanId) {
  const idx = form.value.fan_ids.indexOf(fanId)
  if (idx === -1) {
    form.value.fan_ids.push(fanId)
  } else {
    form.value.fan_ids.splice(idx, 1)
  }
}

function selectAllWeekdays() {
  if (form.value.weekdays.length === 7) {
    form.value.weekdays = []
  } else {
    form.value.weekdays = [0, 1, 2, 3, 4, 5, 6]
  }
}

function selectAllFans() {
  if (form.value.fan_ids.length === props.fans.length) {
    form.value.fan_ids = []
  } else {
    form.value.fan_ids = props.fans.map(f => f.id)
  }
}

function resetForm() {
  form.value = { ...defaultForm, weekdays: [], fan_ids: [] }
  editingId.value = null
  errorMsg.value = ''
}

function openForCreate() {
  resetForm()
  errorMsg.value = ''
}

function openForEdit(schedule) {
  editingId.value = schedule.id
  form.value = {
    name: schedule.name,
    fan_ids: [...(schedule.fan_ids || [])],
    weekdays: [...(schedule.weekdays || [])],
    start_time: schedule.start_time,
    end_time: schedule.end_time,
    target_temperature: schedule.target_temperature,
    is_enabled: schedule.is_enabled
  }
  errorMsg.value = ''
}

async function saveSchedule() {
  if (!canSave.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    if (isEditing.value) {
      await scheduleApi.updateSchedule(editingId.value, form.value)
    } else {
      await scheduleApi.createSchedule(form.value)
    }
    emit('saved')
    close()
  } catch (e) {
    errorMsg.value = e.message || '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

function close() {
  emit('close')
}

watch(() => props.visible, (val) => {
  if (!val) {
    setTimeout(() => {
      resetForm()
    }, 300)
  }
})

defineExpose({
  openForCreate,
  openForEdit
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      @click.self="close"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col"
      >
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-gray-800">
              {{ isEditing ? '编辑温控计划' : '新建温控计划' }}
            </h2>
            <p class="text-xs text-gray-400 mt-0.5">
              自动在指定时段内根据温度控制排风扇
            </p>
          </div>
          <button
            @click="close"
            class="w-8 h-8 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors flex items-center justify-center text-xl"
          >
            ×
          </button>
        </div>

        <div class="px-6 py-4 overflow-y-auto flex-1 space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              计划名称
            </label>
            <input
              v-model="form.name"
              type="text"
              maxlength="30"
              placeholder="例如：一号养殖区白天通风"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="text-sm font-medium text-gray-700">
                执行周期
              </label>
              <button
                @click="selectAllWeekdays"
                class="text-xs text-primary-600 hover:text-primary-700"
              >
                {{ form.weekdays.length === 7 ? '取消全选' : '全选' }}
              </button>
            </div>
            <div class="flex gap-2">
              <button
                v-for="day in WEEKDAYS"
                :key="day.value"
                @click="toggleWeekday(day.value)"
                :class="[
                  'w-10 h-10 rounded-lg font-medium text-sm transition-all duration-150',
                  form.weekdays.includes(day.value)
                    ? 'bg-primary-500 text-white shadow-md scale-105'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                ]"
              >
                {{ day.short }}
              </button>
            </div>
            <p class="text-xs text-gray-400 mt-1.5">已选：{{ weekdayLabels }}</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">
                开始时间
              </label>
              <input
                v-model="form.start_time"
                type="time"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">
                结束时间
              </label>
              <input
                v-model="form.end_time"
                type="time"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              目标温度：<span class="text-primary-600 font-semibold">{{ form.target_temperature.toFixed(1) }}°C</span>
            </label>
            <div class="flex items-center gap-3">
              <input
                v-model.number="form.target_temperature"
                type="range"
                min="15"
                max="35"
                step="0.5"
                class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
              />
              <input
                v-model.number="form.target_temperature"
                type="number"
                min="10"
                max="40"
                step="0.5"
                class="w-20 px-2 py-1 text-center border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <p class="text-xs text-gray-400 mt-1.5">
              温度高于目标温度 1°C 以上自动开启排风扇，低于目标温度 0.5°C 以下自动关闭
            </p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="text-sm font-medium text-gray-700">
                控制的排风扇
              </label>
              <button
                @click="selectAllFans"
                class="text-xs text-primary-600 hover:text-primary-700"
              >
                {{ form.fan_ids.length === fans.length ? '取消全选' : '全选' }}
              </button>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="fan in fans"
                :key="fan.id"
                @click="toggleFan(fan.id)"
                :class="[
                  'p-3 rounded-lg text-left border-2 transition-all duration-150',
                  form.fan_ids.includes(fan.id)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                ]"
              >
                <div class="flex items-center gap-2">
                  <span :class="fan.is_running ? 'text-primary-500' : 'text-gray-400'">🌀</span>
                  <span class="text-sm font-medium text-gray-800">{{ fan.name }}</span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5 ml-6">{{ fan.location }}</p>
              </button>
            </div>
            <p class="text-xs text-gray-400 mt-1.5">
              已选 {{ form.fan_ids.length }} / {{ fans.length }} 台
            </p>
          </div>

          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p class="text-sm font-medium text-gray-700">启用该计划</p>
              <p class="text-xs text-gray-400">关闭后计划将不会自动执行</p>
            </div>
            <button
              @click="form.is_enabled = !form.is_enabled"
              :class="[
                'relative w-11 h-6 rounded-full transition-colors duration-200',
                form.is_enabled ? 'bg-primary-500' : 'bg-gray-300'
              ]"
            >
              <span
                :class="[
                  'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200',
                  form.is_enabled ? 'translate-x-5.5 left-0.5' : 'left-0.5'
                ]"
                :style="{ left: form.is_enabled ? '22px' : '2px' }"
              ></span>
            </button>
          </div>

          <div
            v-if="errorMsg"
            class="p-3 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm"
          >
            ⚠️ {{ errorMsg }}
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-100 flex gap-3">
          <button
            @click="close"
            class="flex-1 py-2.5 px-4 rounded-lg border border-gray-200 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="saveSchedule"
            :disabled="!canSave || saving"
            :class="[
              'flex-1 py-2.5 px-4 rounded-lg font-medium transition-all duration-200',
              canSave && !saving
                ? 'bg-primary-500 text-white hover:bg-primary-600 shadow-md hover:shadow-lg'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            ]"
          >
            {{ saving ? '保存中...' : (isEditing ? '保存修改' : '创建计划') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
