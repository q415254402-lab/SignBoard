<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { displayApi } from '../api/display'
import { deviceGroupApi } from '../api/deviceGroup'
import { layoutApi } from '../api/layout'
import { scheduleApi } from '../api/schedule'
import { Monitor, MonitorOff, RefreshCw, RotateCw, Camera, Trash2, Edit3, X, Check, Search, LayoutGrid, List } from 'lucide-vue-next'

const router = useRouter()
const toast = inject('toast')
const displays = ref([])
const groups = ref([])
const ungroupedCount = ref(0)
const layouts = ref([])
const schedules = ref([])

const selectedGroup = ref(null)
const selectedIds = ref(new Set())
const showGroupModal = ref(false)
const showBatchLayout = ref(false)
const showBatchSchedule = ref(false)
const batchLayoutId = ref(null)
const batchScheduleId = ref(null)
const editingGroup = ref(null)
const groupNameInput = ref('')
const searchText = ref('')
const statusFilter = ref('')
const viewMode = ref(localStorage.getItem('displays_viewMode') || 'card')
let timer = null

function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem('displays_viewMode', mode)
}

const isAllSelected = computed(() => {
  const filtered = filteredDisplays.value
  return filtered.length > 0 && filtered.every(d => selectedIds.value.has(d.id))
})

const filteredDisplays = computed(() => {
  let list = displays.value

  // Group filter
  if (selectedGroup.value === null) {
    // all
  } else if (selectedGroup.value === -1) {
    list = list.filter(d => !d.group_id)
  } else {
    list = list.filter(d => d.group_id === selectedGroup.value)
  }

  // Status filter
  if (statusFilter.value) {
    list = list.filter(d => d.status === statusFilter.value)
  }

  // Search
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    list = list.filter(d =>
      (d.name && d.name.toLowerCase().includes(q)) ||
      (d.ip_address && d.ip_address.toLowerCase().includes(q))
    )
  }

  return list
})

const selectedCount = computed(() => selectedIds.value.size)

async function load() {
  try {
    const [displayData, groupData, layoutData, scheduleData] = await Promise.all([
      displayApi.list(),
      deviceGroupApi.list(),
      layoutApi.list(),
      scheduleApi.list()
    ])
    displays.value = displayData.map(d => ({
      ...d,
      screenshotUrl: d.last_screenshot ? `${displayApi.getScreenshot(d.id)}?t=${Date.now()}` : null
    }))
    groups.value = groupData.groups || []
    ungroupedCount.value = groupData.ungrouped_count || 0
    layouts.value = layoutData
    schedules.value = scheduleData
  } catch (e) {
    console.error(e)
  }
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(filteredDisplays.value.map(d => d.id))
  }
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function batchCommand(cmd) {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const label = { restart: '重启', screen_off: '熄屏', screen_on: '唤醒' }[cmd] || cmd
  if (!confirm(`确定批量${label} ${ids.length} 台设备？`)) return
  try {
    await displayApi.batchCommand(ids, cmd)
    toast.success(`已发送${label}指令`)
    clearSelection()
  } catch (e) {
    toast.error(e.message)
  }
}

async function batchSetLayout() {
  const ids = [...selectedIds.value]
  if (!ids.length || !batchLayoutId.value) return
  try {
    await displayApi.batchSetLayout(ids, batchLayoutId.value)
    toast.success(`已绑定布局到 ${ids.length} 台设备`)
    showBatchLayout.value = false
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function batchSetSchedule() {
  const ids = [...selectedIds.value]
  if (!ids.length || !batchScheduleId.value) return
  try {
    const schedule = schedules.value.find(s => s.id === batchScheduleId.value)
    if (!schedule) { toast.error('排程不存在'); return }
    const existingIds = schedule.display_ids || []
    const mergedIds = [...new Set([...existingIds, ...ids])]
    await scheduleApi.update(batchScheduleId.value, { display_ids: mergedIds })
    toast.success(`已将 ${ids.length} 台设备添加到排程「${schedule.name}」`)
    showBatchSchedule.value = false
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function batchUnbindLayout() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`确定取消 ${ids.length} 台设备的布局绑定？`)) return
  try {
    for (const id of ids) {
      await displayApi.update(id, { current_layout_id: null })
    }
    toast.success(`已取消 ${ids.length} 台设备的布局绑定`)
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function batchUnbindSchedule() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`确定将 ${ids.length} 台设备从所有排程中移除？`)) return
  try {
    for (const s of schedules.value) {
      const existingIds = s.display_ids || []
      const newIds = existingIds.filter(id => !ids.includes(id))
      if (newIds.length !== existingIds.length) {
        await scheduleApi.update(s.id, { display_ids: newIds })
      }
    }
    toast.success(`已将 ${ids.length} 台设备从所有排程中移除`)
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function batchDelete() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`确定删除 ${ids.length} 台设备？此操作不可恢复！`)) return
  try {
    for (const id of ids) {
      await displayApi.remove(id)
    }
    toast.success(`已删除 ${ids.length} 台设备`)
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function setGroupForBatch(groupId) {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  try {
    await displayApi.batchSetGroup(ids, groupId)
    toast.success('分组已更新')
    clearSelection()
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function setGroupForDevice(device, groupId) {
  try {
    await displayApi.update(device.id, { group_id: groupId || null })
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

function openGroupModal() {
  editingGroup.value = null
  groupNameInput.value = ''
  showGroupModal.value = true
}

function openEditGroup(g) {
  editingGroup.value = g
  groupNameInput.value = g.name
}

async function saveGroup() {
  const name = groupNameInput.value.trim()
  if (!name) { toast.warning('请输入分组名称'); return }
  try {
    if (editingGroup.value) {
      await deviceGroupApi.update(editingGroup.value.id, { name })
    } else {
      await deviceGroupApi.create({ name })
    }
    editingGroup.value = null
    groupNameInput.value = ''
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function deleteGroup(g) {
  if (!confirm(`删除分组「${g.name}」？该分组下的设备将变为未分组`)) return
  try {
    await deviceGroupApi.remove(g.id)
    if (selectedGroup.value === g.id) selectedGroup.value = null
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function restart(item) {
  if (!confirm(`确定重启屏幕「${item.name}」？`)) return
  try {
    await displayApi.restart(item.id)
    toast.success('重启指令已发送')
  } catch (e) { toast.error(e.message) }
}

async function screenOff(item) {
  if (!confirm(`确定熄灭「${item.name}」的屏幕？`)) return
  try {
    await displayApi.command(item.id, 'screen_off')
    toast.success('熄屏指令已发送')
  } catch (e) { toast.error(e.message) }
}

async function screenOn(item) {
  if (!confirm(`确定唤醒「${item.name}」的屏幕？`)) return
  try {
    await displayApi.command(item.id, 'screen_on')
    toast.success('唤醒指令已发送')
  } catch (e) { toast.error(e.message) }
}

async function capture(item) {
  try {
    await displayApi.screenshot(item.id)
    setTimeout(load, 2000)
  } catch (e) { toast.error(e.message) }
}

async function removeDisplay(item) {
  if (!confirm(`确定删除屏幕「${item.name}」？`)) return
  try {
    await displayApi.remove(item.id)
    toast.success('已删除')
    await load()
  } catch (e) { toast.error(e.message) }
}

async function editName(item) {
  const newName = prompt('修改屏幕名称', item.name)
  if (newName && newName.trim() && newName.trim() !== item.name) {
    try {
      await displayApi.update(item.id, { name: newName.trim() })
      toast.success('名称已修改')
      await load()
    } catch (e) { toast.error(e.message) }
  }
}

function showDeviceInfo(item) {
  const info = [
    `设备名称: ${item.name}`,
    `平台: ${item.platform || '未知'}`,
    `IP 地址: ${item.ip_address || '未知'}`,
    `MAC 地址: ${item.mac_address || '未知'}`,
    `分辨率: ${item.screen_width}×${item.screen_height}`,
    `方向: ${item.screen_orientation === 'portrait' ? '竖屏' : '横屏'}`,
    `状态: ${item.status === 'online' ? '在线' : '离线'}`,
    `最后心跳: ${item.last_heartbeat || '无'}`
  ].join('\n')
  alert(info)
}

function getGroupName(id) {
  if (!id) return '未分组'
  const g = groups.value.find(g => g.id === id)
  return g ? g.name : '未分组'
}

function getDeviceLayout(d) {
  if (!d.current_layout_id) return null
  return layouts.value.find(l => l.id === d.current_layout_id) || null
}

function getDeviceSchedules(d) {
  return schedules.value.filter(s => s.display_ids && s.display_ids.includes(d.id))
}

onMounted(() => {
  load()
  timer = setInterval(load, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="sr-only">屏幕管理</h1>
      <!-- Search + status filter -->
      <div v-if="displays.length > 0" class="flex items-center gap-2">
        <div class="relative">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input v-model="searchText" class="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="搜索设备名/IP...">
        </div>
        <select v-model="statusFilter" class="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
          <option value="">全部状态</option>
          <option value="online">在线</option>
          <option value="offline">离线</option>
        </select>
      </div>
      <div v-else></div>
      <div class="flex items-center gap-2">
        <!-- View mode toggle -->
        <div v-if="displays.length > 0" class="flex items-center border border-slate-200 rounded-lg overflow-hidden">
          <button @click="setViewMode('card')" :class="['p-1.5 transition-all', viewMode === 'card' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']">
            <LayoutGrid :size="16" />
          </button>
          <button @click="setViewMode('list')" :class="['p-1.5 transition-all', viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']">
            <List :size="16" />
          </button>
        </div>
        <button @click="load()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all duration-200">
          <RefreshCw :size="14" />
          刷新
        </button>
      </div>
    </div>

    <!-- Group bar -->
    <div v-if="displays.length > 0" class="flex items-center gap-2 mb-4 overflow-x-auto pb-2">
      <button @click="selectedGroup = null"
        :class="['px-3 py-1.5 text-sm rounded-xl border whitespace-nowrap transition-all', selectedGroup === null ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        全部 ({{ displays.length }})
      </button>
      <button v-for="g in groups" :key="g.id" @click="selectedGroup = g.id"
        :class="['px-3 py-1.5 text-sm rounded-xl border whitespace-nowrap transition-all', selectedGroup === g.id ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        {{ g.name }} ({{ g.device_count }})
      </button>
      <button v-if="ungroupedCount > 0" @click="selectedGroup = -1"
        :class="['px-3 py-1.5 text-sm rounded-xl border whitespace-nowrap transition-all', selectedGroup === -1 ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        未分组 ({{ ungroupedCount }})
      </button>
      <button @click="openGroupModal()" class="px-3 py-1.5 text-sm text-blue-500 hover:text-blue-700 border border-dashed border-blue-300 rounded-xl whitespace-nowrap">
        + 管理分组
      </button>
    </div>

    <!-- Batch action bar -->
    <div v-if="selectedCount > 0" class="flex items-center gap-3 mb-4 p-3 bg-blue-50 border border-blue-200 rounded-xl">
      <button @click="toggleAll" class="flex items-center gap-1.5 text-sm text-blue-600">
        <Check :size="14" />
        {{ isAllSelected ? '取消全选' : '全选' }}
      </button>
      <span class="text-sm text-blue-600 font-medium">已选 {{ selectedCount }} 台</span>
      <div class="flex-1"></div>
      <button @click="showBatchLayout = true" class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600">绑定布局</button>
      <button @click="batchUnbindLayout()" class="px-3 py-1.5 text-sm bg-blue-400 text-white rounded-lg hover:bg-blue-500">取消布局</button>
      <button @click="showBatchSchedule = true" class="px-3 py-1.5 text-sm bg-purple-500 text-white rounded-lg hover:bg-purple-600">绑定排程</button>
      <button @click="batchUnbindSchedule()" class="px-3 py-1.5 text-sm bg-purple-400 text-white rounded-lg hover:bg-purple-500">取消排程</button>
      <button @click="batchCommand('restart')" class="px-3 py-1.5 text-sm bg-slate-500 text-white rounded-lg hover:bg-slate-600">批量重启</button>
      <button @click="batchCommand('screen_off')" class="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600">批量熄屏</button>
      <button @click="batchCommand('screen_on')" class="px-3 py-1.5 text-sm bg-green-500 text-white rounded-lg hover:bg-green-600">批量唤醒</button>
      <button @click="batchDelete()" class="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600">删除</button>
      <button @click="clearSelection()" class="p-1 text-slate-400 hover:text-slate-600"><X :size="16" /></button>
    </div>

    <!-- Grid (card view) -->
    <template v-if="viewMode === 'card'">
      <div v-if="filteredDisplays.length === 0 && !loading" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
        <Monitor :size="48" class="mx-auto mb-4 text-slate-300" />
        <p class="text-slate-500 font-medium">没有匹配的设备</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="d in filteredDisplays" :key="d.id" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all duration-300 group">
          <!-- Screenshot -->
          <div class="relative bg-slate-900 flex items-center justify-center" style="height: 200px;">
            <img v-if="d.screenshotUrl" :src="d.screenshotUrl" class="w-full h-full object-contain" alt="截图">
            <div v-else class="text-slate-500 text-sm">暂无截图</div>
            <!-- Status badge -->
            <div class="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full">
              <span class="w-2 h-2 rounded-full" :class="d.status === 'online' ? 'bg-green-400 animate-pulse' : 'bg-slate-400'"></span>
              <span class="text-xs text-white">{{ d.status === 'online' ? '在线' : '离线' }}</span>
            </div>
            <!-- Orientation badge -->
            <div class="absolute top-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full text-xs text-white">
              {{ d.screen_orientation === 'portrait' ? '竖屏' : '横屏' }}
            </div>
            <!-- Checkbox -->
            <button @click.stop="toggleSelect(d.id)"
              class="absolute bottom-2 left-2 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all"
              :class="selectedIds.has(d.id) ? 'bg-blue-500 border-blue-500 text-white' : 'bg-white/80 border-slate-300 text-transparent hover:border-blue-400'">
              <Check :size="14" />
            </button>
          </div>
          <!-- Info -->
          <div class="p-4">
            <div class="flex items-center justify-between mb-1">
              <h3 class="font-semibold text-slate-800 truncate">{{ d.name }}</h3>
              <button @click="editName(d)" class="p-1 text-slate-400 hover:text-blue-500 rounded">
                <Edit3 :size="14" />
              </button>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-400 mb-1">
              <span>{{ d.screen_width }}×{{ d.screen_height }}</span>
              <span>·</span>
              <span class="px-1.5 py-0.5 rounded" :class="d.platform === 'android' ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'">
                {{ d.platform === 'android' ? 'Android' : 'Windows' }}
              </span>
              <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{{ getGroupName(d.group_id) }}</span>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <button @click="showDeviceInfo(d)" class="text-xs text-slate-400 hover:text-slate-600">设备信息</button>
              <select @change="setGroupForDevice(d, $event.target.value); $event.target.value = ''" class="text-xs border-none bg-transparent text-slate-400 cursor-pointer focus:outline-none">
                <option value="">移动到...</option>
                <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
                <option value="null">未分组</option>
              </select>
            </div>
            <div v-if="getDeviceLayout(d)" class="text-xs mt-1.5 flex items-center gap-1">
              <span class="px-1.5 py-0.5 bg-blue-50 rounded cursor-pointer hover:bg-blue-100 transition-colors" @click="router.push('/layouts?id=' + d.current_layout_id)">布局: {{ getDeviceLayout(d).name }}</span>
            </div>
            <div v-if="getDeviceSchedules(d).length" class="text-xs text-purple-500 mt-1">
              <span v-for="s in getDeviceSchedules(d).slice(0, 2)" :key="s.id" class="px-1.5 py-0.5 bg-purple-50 rounded mr-1 cursor-pointer hover:bg-purple-100 transition-colors" @click="router.push('/schedules?id=' + s.id)">{{ s.name }}</span>
              <span v-if="getDeviceSchedules(d).length > 2" class="text-slate-400">+{{ getDeviceSchedules(d).length - 2 }}</span>
            </div>
            <!-- Actions -->
            <div class="flex gap-2 pt-3 mt-2 border-t border-slate-50">
              <button @click="capture(d)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200">
                <Camera :size="14" /> 截屏
              </button>
              <button @click="screenOff(d)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-all duration-200">
                <MonitorOff :size="14" /> 熄屏
              </button>
              <button @click="screenOn(d)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-all duration-200">
                <Monitor :size="14" /> 唤醒
              </button>
              <button @click="restart(d)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200">
                <RotateCw :size="14" /> 重启
              </button>
              <button @click="removeDisplay(d)" class="flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- List view -->
    <div v-if="viewMode === 'list'" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-100 bg-slate-50">
            <th class="w-10 px-4 py-2">
              <button @click="toggleAll" :class="['w-5 h-5 rounded border-2 flex items-center justify-center transition-all', isAllSelected ? 'bg-blue-500 border-blue-500 text-white' : 'border-slate-300 text-transparent hover:border-blue-400']">
                <Check :size="12" />
              </button>
            </th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">名称</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">状态</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">平台</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">IP</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">分辨率</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">分组</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">绑定</th>
            <th class="text-right px-4 py-2 text-xs font-medium text-slate-500">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in filteredDisplays" :key="d.id" class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="px-4 py-2">
              <button @click="toggleSelect(d.id)" :class="['w-5 h-5 rounded border-2 flex items-center justify-center transition-all', selectedIds.has(d.id) ? 'bg-blue-500 border-blue-500 text-white' : 'border-slate-300 text-transparent hover:border-blue-400']">
                <Check :size="12" />
              </button>
            </td>
            <td class="px-4 py-2">
              <div class="flex items-center gap-2">
                <span class="font-medium text-slate-800 text-sm">{{ d.name }}</span>
                <button @click="editName(d)" class="p-0.5 text-slate-400 hover:text-blue-500"><Edit3 :size="12" /></button>
              </div>
            </td>
            <td class="px-4 py-2">
              <span class="flex items-center gap-1.5 text-xs">
                <span class="w-2 h-2 rounded-full" :class="d.status === 'online' ? 'bg-green-400' : 'bg-slate-300'"></span>
                {{ d.status === 'online' ? '在线' : '离线' }}
              </span>
            </td>
            <td class="px-4 py-2">
              <span class="text-xs px-1.5 py-0.5 rounded" :class="d.platform === 'android' ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'">
                {{ d.platform === 'android' ? 'Android' : 'Windows' }}
              </span>
            </td>
            <td class="px-4 py-2 text-xs text-slate-500">{{ d.ip_address || '-' }}</td>
            <td class="px-4 py-2 text-xs text-slate-500">{{ d.screen_width }}×{{ d.screen_height }}</td>
            <td class="px-4 py-2">
              <select @change="setGroupForDevice(d, $event.target.value); $event.target.value = ''" class="text-xs border-none bg-transparent text-slate-500 cursor-pointer focus:outline-none">
                <option value="">{{ getGroupName(d.group_id) }}</option>
                <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
                <option value="null">未分组</option>
              </select>
            </td>
            <td class="px-4 py-2 text-xs text-slate-500">
              <div v-if="getDeviceLayout(d)" class="text-blue-500 truncate max-w-[120px] cursor-pointer hover:text-blue-700" @click="router.push('/layouts?id=' + d.current_layout_id)">布局: {{ getDeviceLayout(d).name }}</div>
              <div v-for="s in getDeviceSchedules(d)" :key="s.id" class="text-purple-500 truncate max-w-[120px] cursor-pointer hover:text-purple-700" @click="router.push('/schedules?id=' + s.id)">排程: {{ s.name }}</div>
              <span v-if="!getDeviceLayout(d) && !getDeviceSchedules(d).length" class="text-slate-400">-</span>
            </td>
            <td class="px-4 py-2 text-right">
              <div class="flex items-center justify-end gap-1">
                <button @click="capture(d)" class="p-1 text-slate-400 hover:text-blue-500 rounded" title="截屏"><Camera :size="14" /></button>
                <button @click="screenOff(d)" class="p-1 text-slate-400 hover:text-amber-500 rounded" title="熄屏"><MonitorOff :size="14" /></button>
                <button @click="screenOn(d)" class="p-1 text-slate-400 hover:text-green-500 rounded" title="唤醒"><Monitor :size="14" /></button>
                <button @click="restart(d)" class="p-1 text-slate-400 hover:text-red-500 rounded" title="重启"><RotateCw :size="14" /></button>
                <button @click="removeDisplay(d)" class="p-1 text-slate-400 hover:text-red-500 rounded" title="删除"><Trash2 :size="14" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredDisplays.length">
            <td colspan="8" class="px-4 py-8 text-center text-sm text-slate-400">无匹配设备</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Group management modal -->
    <div v-if="showGroupModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showGroupModal = false">
      <div class="bg-white rounded-2xl max-w-md w-full max-h-[80vh] overflow-y-auto shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">分组管理</h3>
          <button @click="showGroupModal = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6 space-y-3">
          <div v-for="g in groups" :key="g.id" class="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
            <div>
              <span class="font-medium text-slate-700">{{ g.name }}</span>
              <span class="text-xs text-slate-400 ml-2">{{ g.device_count }} 台设备</span>
            </div>
            <div class="flex items-center gap-1">
              <button @click="openEditGroup(g)" class="p-1.5 text-slate-400 hover:text-blue-500 rounded"><Edit3 :size="14" /></button>
              <button @click="deleteGroup(g)" class="p-1.5 text-slate-400 hover:text-red-500 rounded"><Trash2 :size="14" /></button>
            </div>
          </div>
          <div v-if="ungroupedCount > 0" class="p-3 bg-slate-50 rounded-xl">
            <span class="text-slate-500">未分组</span>
            <span class="text-xs text-slate-400 ml-2">{{ ungroupedCount }} 台设备</span>
          </div>
          <div class="flex gap-2 pt-2">
            <input v-model="groupNameInput" @keyup.enter="saveGroup()" class="flex-1 px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="分组名称">
            <button @click="saveGroup()" class="px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600">{{ editingGroup ? '更新' : '添加' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Batch layout modal -->
    <div v-if="showBatchLayout" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showBatchLayout = false">
      <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">批量绑定布局 ({{ selectedCount }} 台)</h3>
          <button @click="showBatchLayout = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6">
          <select v-model="batchLayoutId" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
            <option :value="null">选择布局</option>
            <option v-for="l in layouts" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
          <div class="flex justify-end gap-3 mt-4">
            <button @click="showBatchLayout = false" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
            <button @click="batchSetLayout()" :disabled="!batchLayoutId" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50">确定</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Batch schedule modal -->
    <div v-if="showBatchSchedule" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showBatchSchedule = false">
      <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">批量绑定排程 ({{ selectedCount }} 台)</h3>
          <button @click="showBatchSchedule = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6">
          <select v-model="batchScheduleId" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
            <option :value="null">选择排程</option>
            <option v-for="s in schedules" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <p class="text-xs text-slate-400 mt-2">选中的设备将添加到排程的设备列表中</p>
          <div class="flex justify-end gap-3 mt-4">
            <button @click="showBatchSchedule = false" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
            <button @click="batchSetSchedule()" :disabled="!batchScheduleId" class="px-6 py-2 text-sm bg-purple-500 text-white font-medium rounded-xl hover:bg-purple-600 disabled:opacity-50">确定</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
