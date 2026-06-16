<script setup>
import { ref, onMounted, inject, computed } from 'vue'
import { powerScheduleApi } from '../api/powerSchedule'
import { displayApi } from '../api/display'
import { Power, PowerOff, Trash2, Edit3, X, Check, Search, LayoutGrid, List, ToggleLeft, ToggleRight } from 'lucide-vue-next'

const toast = inject('toast')
const schedules = ref([])
const displays = ref([])
const loading = ref(false)
const searchText = ref('')
const viewMode = ref(localStorage.getItem('powerSchedules_viewMode') || 'card')
const showEditModal = ref(false)
const editingId = ref(null)

const dayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const dayValues = ['0', '1', '2', '3', '4', '5', '6']

const form = ref({
  name: '',
  display_ids: [],
  on_time: '08:00',
  off_time: '22:00',
  power_days: '1,2,3,4,5',
  is_enabled: true,
})
const noOnTime = ref(false)
const noOffTime = ref(false)

function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem('powerSchedules_viewMode', mode)
}

const filteredSchedules = computed(() => {
  if (!searchText.value.trim()) return schedules.value
  const q = searchText.value.trim().toLowerCase()
  return schedules.value.filter(s => s.name.toLowerCase().includes(q))
})

async function load() {
  loading.value = true
  try {
    const [scheduleData, displayData] = await Promise.all([powerScheduleApi.list(), displayApi.list()])
    schedules.value = scheduleData
    displays.value = displayData
  } catch (e) { toast.error(e.message) } finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', display_ids: [], on_time: '08:00', off_time: '22:00', power_days: '1,2,3,4,5', is_enabled: true }
  noOnTime.value = false
  noOffTime.value = false
  showEditModal.value = true
}

function openEdit(item) {
  editingId.value = item.id
  form.value = {
    name: item.name,
    display_ids: [...item.display_ids],
    on_time: item.on_time || '08:00',
    off_time: item.off_time || '22:00',
    power_days: item.power_days,
    is_enabled: item.is_enabled,
  }
  noOnTime.value = !item.on_time
  noOffTime.value = !item.off_time
  showEditModal.value = true
}

function toggleDay(d) {
  const days = new Set(form.value.power_days.split(',').filter(Boolean))
  if (days.has(d)) days.delete(d); else days.add(d)
  form.value.power_days = [...days].join(',')
}

function toggleDisplay(id) {
  const ids = new Set(form.value.display_ids)
  if (ids.has(id)) ids.delete(id); else ids.add(id)
  form.value.display_ids = [...ids]
}

function selectAllDisplays() {
  form.value.display_ids = displays.value.map(d => d.id)
}

function clearDisplaySelection() {
  form.value.display_ids = []
}

async function save() {
  const data = {
    ...form.value,
    on_time: noOnTime.value ? null : form.value.on_time,
    off_time: noOffTime.value ? null : form.value.off_time,
  }
  if (!data.name.trim()) { toast.warning('请输入计划名称'); return }
  if (!data.on_time && !data.off_time) { toast.warning('请至少设置开机或关机时间'); return }
  if (!data.power_days) { toast.warning('请至少选择一天'); return }
  try {
    if (editingId.value) {
      await powerScheduleApi.update(editingId.value, data)
      toast.success('计划已更新')
    } else {
      await powerScheduleApi.create(data)
      toast.success('计划已创建')
    }
    showEditModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
}

async function toggleEnabled(item) {
  try {
    await powerScheduleApi.patch(item.id, { is_enabled: !item.is_enabled })
    item.is_enabled = !item.is_enabled
    toast.success(item.is_enabled ? '已启用' : '已禁用')
  } catch (e) { toast.error(e.message) }
}

async function remove(item) {
  if (!confirm(`确定删除计划「${item.name}」？`)) return
  try {
    await powerScheduleApi.remove(item.id)
    toast.success('已删除')
    await load()
  } catch (e) { toast.error(e.message) }
}

function getDisplayNames(ids) {
  if (!ids || !ids.length) return '全部设备'
  return ids.map(id => displays.value.find(d => d.id === id)?.name || `#${id}`).join(', ')
}

function formatDays(days) {
  if (!days) return ''
  const list = days.split(',').filter(Boolean).sort()
  if (list.length === 7) return '每天'
  const names = list.map(d => dayNames[parseInt(d)] || d)
  return names.join(', ')
}

onMounted(load)
</script>

<template>
  <div>
    <!-- 顶栏 -->
    <div class="flex justify-between items-center mb-4">
      <div v-if="schedules.length > 0" class="flex items-center gap-2">
        <div class="relative">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input v-model="searchText" class="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="搜索计划名称...">
        </div>
      </div>
      <div v-else></div>
      <div class="flex items-center gap-2">
        <div v-if="schedules.length > 0" class="flex items-center border border-slate-200 rounded-lg overflow-hidden">
          <button @click="setViewMode('card')" :class="['p-1.5 transition-all', viewMode === 'card' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><LayoutGrid :size="16" /></button>
          <button @click="setViewMode('list')" :class="['p-1.5 transition-all', viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><List :size="16" /></button>
        </div>
        <button @click="load()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all">
          刷新
        </button>
        <button @click="openCreate()" class="flex items-center gap-1.5 px-4 py-2 bg-blue-500 text-white font-medium text-sm rounded-xl hover:bg-blue-600 transition-all shadow-lg shadow-blue-500/25 active:scale-[0.98]">
          + 新建计划
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && filteredSchedules.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
      <Power :size="48" class="mx-auto mb-4 text-slate-300" />
      <p class="text-slate-500 font-medium">{{ schedules.length === 0 ? '还没有开关机计划' : '无匹配计划' }}</p>
    </div>
    <div v-if="loading" class="text-center py-12 text-slate-400">加载中...</div>

    <!-- 卡片视图 -->
    <div v-if="viewMode === 'card' && !loading && filteredSchedules.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="item in filteredSchedules" :key="item.id" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all">
        <div class="p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-slate-800 truncate">{{ item.name }}</h3>
            <button @click="toggleEnabled(item)" class="flex items-center gap-1 text-sm" :class="item.is_enabled ? 'text-green-600' : 'text-slate-400'">
              <ToggleRight v-if="item.is_enabled" :size="20" />
              <ToggleLeft v-else :size="20" />
              {{ item.is_enabled ? '启用' : '禁用' }}
            </button>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex items-center gap-2">
              <Power :size="14" class="text-green-500" />
              <span class="text-slate-600">开机: {{ item.on_time || '不控制' }}</span>
              <PowerOff :size="14" class="text-orange-500 ml-3" />
              <span class="text-slate-600">关机: {{ item.off_time || '不控制' }}</span>
            </div>
            <div class="text-slate-500">📅 {{ formatDays(item.power_days) }}</div>
            <div class="text-slate-500 truncate">📺 {{ getDisplayNames(item.display_ids) }}</div>
          </div>
          <div class="flex gap-2 pt-3 mt-3 border-t border-slate-50">
            <button @click="openEdit(item)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all">
              <Edit3 :size="14" /> 编辑
            </button>
            <button @click="remove(item)" class="flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all">
              <Trash2 :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-if="viewMode === 'list' && !loading" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <table class="w-full">
        <thead><tr class="border-b border-slate-100 bg-slate-50">
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">名称</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">开机时间</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">关机时间</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">执行日</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">绑定设备</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">状态</th>
          <th class="text-right px-4 py-2 text-xs font-medium text-slate-500">操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="item in filteredSchedules" :key="item.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="px-4 py-2 font-medium text-slate-800 text-sm">{{ item.name }}</td>
            <td class="px-4 py-2 text-sm text-slate-600">{{ item.on_time || '-' }}</td>
            <td class="px-4 py-2 text-sm text-slate-600">{{ item.off_time || '-' }}</td>
            <td class="px-4 py-2 text-sm text-slate-500">{{ formatDays(item.power_days) }}</td>
            <td class="px-4 py-2 text-sm text-slate-500 truncate max-w-[200px]">{{ getDisplayNames(item.display_ids) }}</td>
            <td class="px-4 py-2">
              <span :class="['text-xs px-2 py-0.5 rounded-full', item.is_enabled ? 'bg-green-100 text-green-600' : 'bg-slate-100 text-slate-500']">
                {{ item.is_enabled ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="px-4 py-2 text-right">
              <div class="flex items-center justify-end gap-1">
                <button @click="openEdit(item)" class="p-1.5 text-slate-400 hover:text-blue-500 rounded" title="编辑"><Edit3 :size="14" /></button>
                <button @click="remove(item)" class="p-1.5 text-slate-400 hover:text-red-500 rounded" title="删除"><Trash2 :size="14" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredSchedules.length"><td colspan="7" class="px-6 py-8 text-center text-sm text-slate-400">暂无计划</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showEditModal = false">
      <div class="bg-white rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">{{ editingId ? '编辑' : '新建' }}开关机计划</h3>
          <button @click="showEditModal = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6 space-y-5">
          <!-- 计划名称 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">计划名称</label>
            <input v-model="form.name" class="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="如：工作日开关机">
          </div>

          <!-- 时间 -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">开机时间</label>
              <input v-model="form.on_time" type="time" :disabled="noOnTime" class="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 disabled:bg-slate-50 disabled:text-slate-400">
              <label class="flex items-center gap-1.5 mt-1 text-xs text-slate-500 cursor-pointer">
                <input type="checkbox" v-model="noOnTime" class="rounded"> 不控制开机
              </label>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">关机时间</label>
              <input v-model="form.off_time" type="time" :disabled="noOffTime" class="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 disabled:bg-slate-50 disabled:text-slate-400">
              <label class="flex items-center gap-1.5 mt-1 text-xs text-slate-500 cursor-pointer">
                <input type="checkbox" v-model="noOffTime" class="rounded"> 不控制关机
              </label>
            </div>
          </div>

          <!-- 执行日 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">执行日</label>
            <div class="flex flex-wrap gap-2">
              <button v-for="(name, i) in dayNames" :key="i" @click="toggleDay(String(i))"
                :class="['px-3 py-1.5 text-sm rounded-lg border transition-all', form.power_days.split(',').includes(String(i)) ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
                {{ name }}
              </button>
            </div>
          </div>

          <!-- 绑定屏幕 -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm font-medium text-slate-700">绑定屏幕</label>
              <div class="flex gap-2">
                <button @click="selectAllDisplays" class="text-xs text-blue-500 hover:text-blue-700">全选</button>
                <button @click="clearDisplaySelection" class="text-xs text-slate-400 hover:text-slate-600">取消</button>
              </div>
            </div>
            <p class="text-xs text-slate-400 mb-2">不选择则绑定全部设备</p>
            <div class="max-h-40 overflow-y-auto border border-slate-200 rounded-xl p-2 space-y-1">
              <label v-for="d in displays" :key="d.id" class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                <input type="checkbox" :checked="form.display_ids.includes(d.id)" @change="toggleDisplay(d.id)" class="rounded">
                <span class="text-sm text-slate-700">{{ d.name }}</span>
                <span class="text-xs" :class="d.status === 'online' ? 'text-green-500' : 'text-slate-400'">{{ d.status === 'online' ? '在线' : '离线' }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="flex justify-end gap-3 px-6 py-4 border-t border-slate-100">
          <button @click="showEditModal = false" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
          <button @click="save()" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
