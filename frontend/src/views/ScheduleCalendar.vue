<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { scheduleApi } from '../api/schedule'
import { displayApi } from '../api/display'
import { ChevronLeft, ChevronRight, List, Zap, X } from 'lucide-vue-next'

const toast = inject('toast')
const router = useRouter()
const schedules = ref([])
const displays = ref([])
const layouts = ref([])
const filterDisplay = ref(null)
const urgentModal = ref(null)
const urgentForm = ref({ layout_id: null, display_ids: [], duration_minutes: 30 })

const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth()) // 0-based

const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
const weekDaysShorts = ['一', '二', '三', '四', '五', '六', '日']

function prevMonth() {
  if (currentMonth.value === 0) { currentMonth.value = 11; currentYear.value-- }
  else currentMonth.value--
}

function nextMonth() {
  if (currentMonth.value === 11) { currentMonth.value = 0; currentYear.value++ }
  else currentMonth.value++
}

function goToday() {
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth()
}

// Calendar grid
const calendarDays = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startDayOfWeek = firstDay.getDay() || 7 // Mon=1..Sun=7
  const daysInMonth = lastDay.getDate()

  const days = []
  // Previous month padding
  for (let i = 1; i < startDayOfWeek; i++) {
    const d = new Date(year, month, 1 - (startDayOfWeek - i))
    days.push({ date: d, currentMonth: false })
  }
  // Current month
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({ date: new Date(year, month, i), currentMonth: true })
  }
  return days
})

function getSchedulesForDate(date) {
  const dayStart = new Date(date)
  const dayEnd = new Date(date)
  dayEnd.setHours(23, 59, 59, 999)
  return schedules.value.filter(s => {
    if (!s.is_active) return false
    if (filterDisplay.value && s.display_ids?.length && !s.display_ids.includes(filterDisplay.value)) return false
    // 排程时间范围与当天有交集即显示
    if (s.start_time && new Date(s.start_time) > dayEnd) return false
    if (s.end_time && new Date(s.end_time) < dayStart) return false

    if (s.repeat_type === 'none') {
      return true
    }
    if (s.repeat_type === 'daily') {
      if (s.repeat_until && date > new Date(s.repeat_until)) return false
      return true
    }
    if (s.repeat_type === 'weekly') {
      if (s.repeat_until && date > new Date(s.repeat_until)) return false
      const dow = date.getDay() || 7
      return (s.repeat_days || []).includes(dow)
    }
    if (s.repeat_type === 'monthly') {
      if (s.repeat_until && date > new Date(s.repeat_until)) return false
      return (s.repeat_days || []).includes(date.getDate())
    }
    return false
  })
}

function isToday(date) {
  const t = new Date()
  return date.getFullYear() === t.getFullYear() && date.getMonth() === t.getMonth() && date.getDate() === t.getDate()
}

function formatDateShort(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

async function load() {
  try {
    const { layoutApi } = await import('../api/layout')
    const [s, d, l] = await Promise.all([scheduleApi.list(), displayApi.list(), layoutApi.list()])
    schedules.value = s
    displays.value = d
    layouts.value = l
  } catch (e) {
    console.error(e)
  }
}

function openUrgent() {
  urgentForm.value = { layout_id: layouts.value[0]?.id || null, display_ids: [], duration_minutes: 30 }
  urgentModal.value = {}
}

function toLocalISOString(d) {
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function submitUrgent() {
  const now = new Date()
  const end = new Date(now.getTime() + urgentForm.value.duration_minutes * 60000)
  const data = {
    name: `🚨 紧急插播 ${now.toLocaleTimeString('zh-CN')}`,
    layout_id: urgentForm.value.layout_id,
    display_ids: urgentForm.value.display_ids,
    start_time: toLocalISOString(now),
    end_time: toLocalISOString(end),
    priority: 999,
    is_active: true,
    repeat_type: 'none'
  }
  try {
    await scheduleApi.create(data)
    urgentModal.value = null
    await load()
  } catch (e) {
    toast.error('插播失败: ' + e.message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button @click="router.push('/schedules')" class="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-xl text-sm text-slate-600 hover:bg-slate-50 transition-all duration-200">
          <List :size="16" />
          列表视图
        </button>
        <select v-model="filterDisplay" class="px-3 py-2 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
          <option :value="null">全部屏幕</option>
          <option v-for="d in displays" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
      <button @click="openUrgent()" class="inline-flex items-center gap-2 px-4 py-2.5 bg-red-500 text-white font-medium rounded-xl hover:bg-red-600 transition-all duration-200 shadow-lg shadow-red-500/25 active:scale-[0.98]" title="紧急插播">
        <Zap :size="18" />
        紧急插播
      </button>
    </div>

    <!-- Calendar header -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <button @click="prevMonth()" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all duration-200">
            <ChevronLeft :size="20" />
          </button>
          <h2 class="text-lg font-bold text-slate-800">{{ currentYear }}年 {{ monthNames[currentMonth] }}</h2>
          <button @click="nextMonth()" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all duration-200">
            <ChevronRight :size="20" />
          </button>
        </div>
        <button @click="goToday()" class="px-4 py-1.5 text-sm border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-all duration-200">今天</button>
      </div>

      <!-- Weekday headers -->
      <div class="grid grid-cols-7 border-b border-slate-100">
        <div v-for="d in weekDaysShorts" :key="d" class="px-2 py-2.5 text-center text-xs font-medium text-slate-400">{{ d }}</div>
      </div>

      <!-- Days grid -->
      <div class="grid grid-cols-7">
        <div v-for="(day, idx) in calendarDays" :key="idx"
          :class="[
            'min-h-[100px] border-b border-r border-slate-50 p-1.5 transition-all duration-200',
            day.currentMonth ? 'bg-white' : 'bg-slate-50/50',
            isToday(day.date) ? 'ring-2 ring-inset ring-blue-400' : ''
          ]"
        >
          <div class="text-xs mb-1" :class="day.currentMonth ? 'text-slate-700 font-medium' : 'text-slate-300'">
            {{ day.date.getDate() }}
          </div>
          <div class="space-y-0.5">
            <div v-for="s in getSchedulesForDate(day.date).slice(0, 3)" :key="s.id"
              :class="[
                'text-xs px-1.5 py-0.5 rounded-md truncate',
                s.priority >= 999 ? 'bg-red-100 text-red-600' : s.repeat_type !== 'none' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-600'
              ]"
              :title="s.name"
            >
              {{ s.name }}
            </div>
            <div v-if="getSchedulesForDate(day.date).length > 3" class="text-xs text-slate-400 pl-1">
              +{{ getSchedulesForDate(day.date).length - 3 }} 更多
            </div>
          </div>
        </div>
      </div>

      <!-- Legend -->
      <div class="flex items-center gap-4 px-6 py-3 border-t border-slate-100 text-xs text-slate-400">
        <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded bg-blue-100"></span> 普通排程</span>
        <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded bg-amber-100"></span> 重复排程</span>
        <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded bg-red-100"></span> 紧急插播</span>
      </div>
    </div>

    <!-- Urgent broadcast modal -->
    <div v-if="urgentModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="urgentModal = null">
      <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800 flex items-center gap-2"><Zap :size="18" class="text-red-500" /> 紧急插播</h3>
          <button @click="urgentModal = null" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100">
            <X :size="20" />
          </button>
        </div>
        <div class="p-6 space-y-4">
          <p class="text-sm text-red-600 bg-red-50 rounded-xl p-3">
            紧急插播将创建最高优先级排程，立即覆盖所有屏幕当前播放内容。
          </p>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">选择布局</label>
            <select v-model="urgentForm.layout_id" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-400">
              <option v-for="l in layouts" :key="l.id" :value="l.id">{{ l.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">目标屏幕</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="d in displays" :key="d.id" class="flex items-center gap-1.5 px-3 py-1.5 border rounded-xl text-sm cursor-pointer transition-all duration-200" :class="urgentForm.display_ids.includes(d.id) ? 'border-red-400 bg-red-50 text-red-600' : 'border-slate-200 text-slate-500 hover:border-slate-300'">
                <input type="checkbox" :value="d.id" v-model="urgentForm.display_ids" class="sr-only">
                {{ d.name }}
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">持续时长（分钟）</label>
            <input v-model.number="urgentForm.duration_minutes" type="number" min="1" max="1440" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-400">
          </div>
        </div>
        <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
          <button @click="urgentModal = null" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl transition-all duration-200">取消</button>
          <button @click="submitUrgent()" :disabled="!urgentForm.layout_id" class="px-6 py-2 text-sm bg-red-500 text-white font-medium rounded-xl hover:bg-red-600 transition-all duration-200 shadow-lg shadow-red-500/25 disabled:opacity-50">立即插播</button>
        </div>
      </div>
    </div>
  </div>
</template>