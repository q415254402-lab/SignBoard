<script setup>
import { ref, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { scheduleApi } from '../api/schedule'
import { layoutApi } from '../api/layout'
import { displayApi } from '../api/display'
import { Plus, Trash2, Edit3, Zap, Calendar, X, Pause, Play } from 'lucide-vue-next'

const route = useRoute()
const toast = inject('toast')
const router = useRouter()
const schedules = ref([])
const layouts = ref([])
const displays = ref([])
const modal = ref(null)
const form = ref({
  name: '', layout_id: null, display_ids: [],
  start_time: '', end_time: '', priority: 0, enabled: true,
  repeat_type: 'none', repeat_days: [], repeat_start_time: '', repeat_end_time: '', repeat_until: ''
})
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [s, l, d] = await Promise.all([scheduleApi.list(), layoutApi.list(), displayApi.list()])
    schedules.value = s
    layouts.value = l
    displays.value = d
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function toLocalISOString(date) {
  const offset = date.getTimezoneOffset()
  const local = new Date(date.getTime() - offset * 60000)
  return local.toISOString().slice(0, 16)
}

function openCreate() {
  form.value = {
    name: '', layout_id: layouts.value[0]?.id || null, display_ids: [],
    start_time: toLocalISOString(new Date()), end_time: '', priority: 0, enabled: true,
    repeat_type: 'none', repeat_days: [], repeat_start_time: '', repeat_end_time: '', repeat_until: ''
  }
  modal.value = {}
}

function openEdit(item) {
  form.value = {
    name: item.name, layout_id: item.layout_id, display_ids: item.display_ids || [],
    start_time: item.start_time ? item.start_time.slice(0, 16) : '',
    end_time: item.end_time ? item.end_time.slice(0, 16) : '',
    priority: item.priority || 0, enabled: item.is_active ?? true,
    repeat_type: item.repeat_type || 'none', repeat_days: item.repeat_days || [],
    repeat_start_time: item.repeat_start_time || '', repeat_end_time: item.repeat_end_time || '',
    repeat_until: item.repeat_until || ''
  }
  modal.value = { editing: item }
}

async function save() {
  const data = { ...form.value }
  // 映射 enabled -> is_active
  data.is_active = data.enabled
  delete data.enabled
  // 确保 start_time 有值
  if (!data.start_time) data.start_time = toLocalISOString(new Date())
  if (!data.end_time) delete data.end_time
  if (!data.repeat_until) delete data.repeat_until
  if (data.repeat_type === 'none') {
    delete data.repeat_days; delete data.repeat_start_time; delete data.repeat_end_time; delete data.repeat_until
  }
  try {
    if (modal.value?.editing) {
      await scheduleApi.update(modal.value.editing.id, data)
    } else {
      await scheduleApi.create(data)
    }
    modal.value = null
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function remove(item) {
  if (!confirm(`确定删除排程「${item.name}」？`)) return
  try {
    await scheduleApi.remove(item.id)
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function toggle(item) {
  try {
    await scheduleApi.patch(item.id, { is_active: !item.is_active })
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

function getLayoutName(id) {
  return layouts.value.find(l => l.id === id)?.name || '未知布局'
}

function getDisplayNames(ids) {
  if (!ids || ids.length === 0) return '全部屏幕'
  return ids.map(id => displays.value.find(d => d.id === id)?.name || `#${id}`).join(', ')
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

const weekDays = ['一', '二', '三', '四', '五', '六', '日']

onMounted(async () => {
  await load()
  const scheduleId = parseInt(route.query.id)
  if (scheduleId) {
    const item = schedules.value.find(s => s.id === scheduleId)
    if (item) openEdit(item)
    router.replace('/schedules')
  }
})
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <button @click="router.push('/schedules/calendar')" class="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-xl text-sm text-slate-600 hover:bg-slate-50 transition-all duration-200">
          <Calendar :size="16" />
          日历视图
        </button>
      </div>
      <div class="flex items-center gap-2">
        <button @click="openCreate()" class="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all duration-200 shadow-lg shadow-blue-500/25 active:scale-[0.98]">
          <Plus :size="18" />
          新建排程
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && schedules.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
      <Calendar :size="48" class="mx-auto mb-4 text-slate-300" />
      <p class="text-slate-500 font-medium">还没有排程</p>
      <p class="text-sm text-slate-400 mt-1">创建一个排程来安排屏幕的播放内容</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-slate-400">加载中...</div>

    <!-- Timeline cards -->
    <div v-else class="space-y-3">
      <div v-for="item in schedules" :key="item.id" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all duration-300">
        <div class="flex">
          <!-- Left color bar -->
          <div class="w-1.5 flex-shrink-0" :class="item.is_active ? 'bg-blue-400' : 'bg-slate-300'"></div>

          <!-- Content -->
          <div class="flex-1 p-5">
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-semibold text-slate-800 truncate">{{ item.name }}</h3>
                  <span v-if="item.repeat_type !== 'none'" class="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded-md font-medium">
                    {{ { daily: '每天', weekly: '每周', monthly: '每月' }[item.repeat_type] }}
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
                  <span>布局: {{ getLayoutName(item.layout_id) }}</span>
                  <span>屏幕: {{ getDisplayNames(item.display_ids) }}</span>
                </div>
                <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-400 mt-1">
                  <span v-if="item.start_time">{{ formatTime(item.start_time) }}</span>
                  <span v-if="item.start_time || item.end_time">→</span>
                  <span v-if="item.end_time">{{ formatTime(item.end_time) }}</span>
                  <span v-if="!item.start_time && !item.end_time" class="text-slate-400">永久有效</span>
                </div>
                <!-- Repeat detail -->
                <div v-if="item.repeat_type !== 'none'" class="mt-2 text-xs text-slate-400">
                  <span v-if="item.repeat_type === 'weekly' && item.repeat_days?.length">
                    每周{{ item.repeat_days.map(d => weekDays[d - 1]).join('、') }}
                  </span>
                  <span v-if="item.repeat_start_time"> {{ item.repeat_start_time }}-{{ item.repeat_end_time }}</span>
                  <span v-if="item.repeat_until"> · 截止 {{ item.repeat_until }}</span>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-1 ml-4 flex-shrink-0">
                <button @click="toggle(item)" :title="item.is_active ? '暂停' : '启用'" class="p-2 rounded-lg transition-all duration-200" :class="item.is_active ? 'text-amber-500 hover:bg-amber-50' : 'text-green-500 hover:bg-green-50'">
                  <Pause v-if="item.is_active" :size="16" />
                  <Play v-else :size="16" />
                </button>
                <button @click="openEdit(item)" class="p-2 rounded-lg text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-all duration-200">
                  <Edit3 :size="16" />
                </button>
                <button @click="remove(item)" class="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all duration-200">
                  <Trash2 :size="16" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit modal -->
    <div v-if="modal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="modal = null">
      <div class="bg-white rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">{{ modal.editing ? '编辑排程' : '新建排程' }}</h3>
          <button @click="modal = null" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all duration-200">
            <X :size="20" />
          </button>
        </div>

        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">名称</label>
            <input v-model="form.name" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all duration-200" placeholder="例如：一楼宣传片">
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">布局</label>
            <select v-model="form.layout_id" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
              <option v-for="l in layouts" :key="l.id" :value="l.id">{{ l.name }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">目标屏幕</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="d in displays" :key="d.id" class="flex items-center gap-1.5 px-3 py-1.5 border rounded-xl text-sm cursor-pointer transition-all duration-200" :class="form.display_ids.includes(d.id) ? 'border-blue-400 bg-blue-50 text-blue-600' : 'border-slate-200 text-slate-500 hover:border-slate-300'">
                <input type="checkbox" :value="d.id" v-model="form.display_ids" class="sr-only">
                {{ d.name }}
              </label>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-600 mb-1.5">开始时间</label>
              <input v-model="form.start_time" type="datetime-local" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all duration-200">
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-600 mb-1.5">结束时间</label>
              <input v-model="form.end_time" type="datetime-local" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all duration-200">
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">重复</label>
            <select v-model="form.repeat_type" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
              <option value="none">不重复</option>
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>

          <div v-if="form.repeat_type !== 'none'" class="space-y-3 p-4 bg-slate-50 rounded-xl">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-slate-500 mb-1">时间段开始</label>
                <input v-model="form.repeat_start_time" type="time" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-400">
              </div>
              <div>
                <label class="block text-xs text-slate-500 mb-1">时间段结束</label>
                <input v-model="form.repeat_end_time" type="time" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-400">
              </div>
            </div>

            <div v-if="form.repeat_type === 'weekly'">
              <label class="block text-xs text-slate-500 mb-1.5">重复日</label>
              <div class="flex gap-1.5">
                <button v-for="(d, i) in weekDays" :key="i" @click="form.repeat_days.includes(i + 1) ? form.repeat_days = form.repeat_days.filter(v => v !== i + 1) : form.repeat_days.push(i + 1)" :class="['w-9 h-9 rounded-lg text-sm font-medium transition-all duration-200', form.repeat_days.includes(i + 1) ? 'bg-blue-500 text-white' : 'bg-white border border-slate-200 text-slate-500 hover:border-blue-300']">
                  {{ d }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs text-slate-500 mb-1">截止日期</label>
              <input v-model="form.repeat_until" type="date" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-400">
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">优先级</label>
            <select v-model.number="form.priority" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
              <option :value="0">普通</option>
              <option :value="10">高</option>
              <option :value="999">紧急</option>
            </select>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
          <button @click="modal = null" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl transition-all duration-200">取消</button>
          <button @click="save()" :disabled="!form.name || !form.layout_id" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all duration-200 shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>