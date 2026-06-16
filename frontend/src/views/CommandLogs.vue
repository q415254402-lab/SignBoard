<script setup>
import { ref, onMounted, inject } from 'vue'
import { commandLogApi } from '../api/commandLog'
import { displayApi } from '../api/display'
import { RefreshCw } from 'lucide-vue-next'

const toast = inject('toast')
const logs = ref([])
const displays = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)

const filterDisplay = ref('')
const filterCommand = ref('')
const filterTriggered = ref('')

const commandLabels = {
  screen_off: { text: '熄屏', cls: 'bg-orange-100 text-orange-600' },
  screen_on: { text: '唤醒', cls: 'bg-green-100 text-green-600' },
  restart: { text: '重启', cls: 'bg-red-100 text-red-600' },
  screenshot: { text: '截屏', cls: 'bg-slate-100 text-slate-600' },
  layout_sync: { text: '布局同步', cls: 'bg-blue-100 text-blue-600' },
}

const triggerLabels = {
  schedule: { text: '自动调度', cls: 'bg-purple-100 text-purple-600' },
  manual: { text: '手动操作', cls: 'bg-slate-100 text-slate-500' },
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterDisplay.value) params.display_id = filterDisplay.value
    if (filterCommand.value) params.command = filterCommand.value
    if (filterTriggered.value) params.triggered_by = filterTriggered.value

    const [logData, displayData] = await Promise.all([commandLogApi.list(params), displayApi.list()])
    logs.value = logData.items || []
    total.value = logData.total || 0
    displays.value = displayData
  } catch (e) { toast.error(e.message) } finally { loading.value = false }
}

function getCommandLabel(cmd) {
  return commandLabels[cmd] || { text: cmd, cls: 'bg-slate-100 text-slate-500' }
}

function getTriggerLabel(t) {
  return triggerLabels[t] || { text: t, cls: 'bg-slate-100 text-slate-500' }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * pageSize.value < total.value) { page.value++; load() } }

onMounted(load)
</script>

<template>
  <div>
    <!-- 顶栏 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-2">
        <select v-model="filterDisplay" @change="page = 1; load()" class="px-3 py-1.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20">
          <option value="">全部设备</option>
          <option v-for="d in displays" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <select v-model="filterCommand" @change="page = 1; load()" class="px-3 py-1.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20">
          <option value="">全部命令</option>
          <option value="screen_off">熄屏</option>
          <option value="screen_on">唤醒</option>
          <option value="restart">重启</option>
          <option value="screenshot">截屏</option>
        </select>
        <select v-model="filterTriggered" @change="page = 1; load()" class="px-3 py-1.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20">
          <option value="">全部来源</option>
          <option value="schedule">自动调度</option>
          <option value="manual">手动操作</option>
        </select>
      </div>
      <button @click="load()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all">
        <RefreshCw :size="14" /> 刷新
      </button>
    </div>

    <!-- 表格 -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div v-if="loading" class="text-center py-12 text-slate-400">加载中...</div>
      <table v-else class="w-full">
        <thead><tr class="border-b border-slate-100 bg-slate-50">
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">时间</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">设备</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">命令</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">触发方式</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">状态</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">错误信息</th>
        </tr></thead>
        <tbody>
          <tr v-for="item in logs" :key="item.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="px-4 py-2 text-sm text-slate-500 whitespace-nowrap">{{ formatTime(item.created_at) }}</td>
            <td class="px-4 py-2 text-sm text-slate-700 font-medium">{{ item.display_name || '-' }}</td>
            <td class="px-4 py-2">
              <span :class="['text-xs px-2 py-0.5 rounded-full', getCommandLabel(item.command).cls]">{{ getCommandLabel(item.command).text }}</span>
            </td>
            <td class="px-4 py-2">
              <span :class="['text-xs px-2 py-0.5 rounded-full', getTriggerLabel(item.triggered_by).cls]">{{ getTriggerLabel(item.triggered_by).text }}</span>
            </td>
            <td class="px-4 py-2">
              <span v-if="item.status === 'success'" class="text-xs text-green-600">✓ 成功</span>
              <span v-else class="text-xs text-red-600">✗ 失败</span>
            </td>
            <td class="px-4 py-2 text-xs text-slate-400 max-w-[200px] truncate">{{ item.error_msg || '-' }}</td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="6" class="px-6 py-8 text-center text-sm text-slate-400">暂无记录</td>
          </tr>
        </tbody>
      </table>
      <!-- 分页 -->
      <div v-if="total > pageSize" class="flex items-center justify-between px-4 py-3 border-t border-slate-100">
        <span class="text-sm text-slate-500">共 {{ total }} 条</span>
        <div class="flex gap-2">
          <button @click="prevPage" :disabled="page <= 1" class="px-3 py-1 text-sm border border-slate-200 rounded-lg disabled:opacity-50 hover:bg-slate-50">上一页</button>
          <span class="px-3 py-1 text-sm text-slate-500">{{ page }}</span>
          <button @click="nextPage" :disabled="page * pageSize >= total" class="px-3 py-1 text-sm border border-slate-200 rounded-lg disabled:opacity-50 hover:bg-slate-50">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>
