<script setup>
import { ref, onMounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '../api/auth'
import { auditApi } from '../api/audit'
import { tagApi } from '../api/tag'
import { useAuthStore } from '../stores/auth'
import { Key, Save, History, Filter, Tags, Plus, Trash2, Edit3, X, Radio } from 'lucide-vue-next'
import CommandLogs from './CommandLogs.vue'

const route = useRoute()
const toast = inject('toast')
const auth = useAuthStore()
const activeTab = ref(route.query.tab || 'password')

// 修改密码
const form = ref({ old_password: '', new_password: '', confirm_password: '' })
const msg = ref('')
const error = ref('')

// 审计日志
const logs = ref([])
const logFilter = ref({ resource: '', action: '', username: '' })
const loadingLogs = ref(false)

// 标签管理
const tags = ref([])
const showTagModal = ref(false)
const editingTag = ref(null)
const tagForm = ref({ name: '', color: '#3B82F6' })

const actionLabels = {
  login: '登录', create: '创建', update: '更新', delete: '删除',
}
const resourceLabels = {
  media: '素材', layout: '布局', schedule: '排程', display: '设备', user: '用户',
}

async function changePw() {
  error.value = ''; msg.value = ''
  if (!form.value.old_password || !form.value.new_password) { error.value = '请填写所有字段'; return }
  if (form.value.new_password !== form.value.confirm_password) { error.value = '两次密码不一致'; return }
  if (form.value.new_password.length < 6) { error.value = '新密码至少 6 位'; return }
  try {
    await authApi.changePassword(form.value.old_password, form.value.new_password)
    msg.value = '密码修改成功！'
    form.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (e) { error.value = e.message || '修改失败' }
}

async function loadLogs() {
  loadingLogs.value = true
  try {
    const params = { limit: 100 }
    if (logFilter.value.resource) params.resource = logFilter.value.resource
    if (logFilter.value.action) params.action = logFilter.value.action
    if (logFilter.value.username) params.username = logFilter.value.username
    logs.value = await auditApi.list(params)
  } catch (e) { console.error(e) } finally { loadingLogs.value = false }
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

// 标签管理
async function loadTags() { try { tags.value = await tagApi.list() } catch (e) { console.error(e) } }

function openTagModal(tag = null) {
  editingTag.value = tag
  tagForm.value = tag ? { name: tag.name, color: tag.color } : { name: '', color: '#3B82F6' }
  showTagModal.value = true
}

async function saveTag() {
  if (!tagForm.value.name.trim()) return
  try {
    if (editingTag.value) await tagApi.update(editingTag.value.id, tagForm.value)
    else await tagApi.create(tagForm.value)
    showTagModal.value = false; await loadTags()
  } catch (e) { console.error(e) }
}

async function deleteTag(tag) {
  if (!confirm(`删除标签「${tag.name}」？`)) return
  try { await tagApi.remove(tag.id); await loadTags() } catch (e) { console.error(e) }
}

onMounted(() => { loadTags(); loadLogs() })
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Tab navigation -->
    <div class="flex items-center gap-1 bg-white rounded-xl p-1 shadow-sm border border-slate-100">
      <button @click="activeTab = 'password'" :class="['flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all', activeTab === 'password' ? 'bg-blue-50 text-blue-600' : 'text-slate-500 hover:text-slate-700']">
        <Key :size="16" /> 修改密码
      </button>
      <button @click="activeTab = 'logs'" :class="['flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all', activeTab === 'logs' ? 'bg-blue-50 text-blue-600' : 'text-slate-500 hover:text-slate-700']">
        <History :size="16" /> 操作日志
      </button>
      <button @click="activeTab = 'tags'" :class="['flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all', activeTab === 'tags' ? 'bg-blue-50 text-blue-600' : 'text-slate-500 hover:text-slate-700']">
        <Tags :size="16" /> 标签管理
      </button>
      <button @click="activeTab = 'commandLogs'" :class="['flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all', activeTab === 'commandLogs' ? 'bg-blue-50 text-blue-600' : 'text-slate-500 hover:text-slate-700']">
        <Radio :size="16" /> 下发记录
      </button>
    </div>

    <!-- Tab: 修改密码 -->
    <div v-if="activeTab === 'password'" class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 space-y-4">
      <h2 class="text-lg font-bold text-slate-800">修改密码</h2>
      <div v-if="msg" class="px-4 py-3 bg-green-50 text-green-700 rounded-xl text-sm">{{ msg }}</div>
      <div v-if="error" class="px-4 py-3 bg-red-50 text-red-600 rounded-xl text-sm">{{ error }}</div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-1.5">当前密码</label>
          <input v-model="form.old_password" type="password" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-1.5">新密码</label>
          <input v-model="form.new_password" type="password" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-1.5">确认新密码</label>
          <input v-model="form.confirm_password" type="password" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
        </div>
      </div>
      <button @click="changePw" class="flex items-center gap-2 px-4 py-2.5 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all shadow-lg shadow-blue-500/25">
        <Save :size="16" /> 保存修改
      </button>
    </div>

    <!-- Tab: 操作日志 -->
    <div v-if="activeTab === 'logs'" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div class="flex items-center gap-3 px-6 py-3 border-b border-slate-100 bg-slate-50">
        <Filter :size="14" class="text-slate-400" />
        <select v-model="logFilter.resource" @change="loadLogs()" class="text-sm border border-slate-200 rounded-lg px-2 py-1 focus:outline-none">
          <option value="">全部资源</option>
          <option value="media">素材</option>
          <option value="layout">布局</option>
          <option value="schedule">排程</option>
          <option value="display">设备</option>
          <option value="user">用户</option>
        </select>
        <select v-model="logFilter.action" @change="loadLogs()" class="text-sm border border-slate-200 rounded-lg px-2 py-1 focus:outline-none">
          <option value="">全部操作</option>
          <option value="login">登录</option>
          <option value="create">创建</option>
          <option value="update">更新</option>
          <option value="delete">删除</option>
        </select>
        <input v-model="logFilter.username" @keyup.enter="loadLogs()" class="text-sm border border-slate-200 rounded-lg px-2 py-1 w-32 focus:outline-none" placeholder="用户名">
        <button @click="loadLogs()" class="text-sm text-blue-500 hover:text-blue-700">搜索</button>
      </div>
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">时间</th>
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">用户</th>
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">操作</th>
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">资源</th>
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">详情</th>
            <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="px-6 py-2 text-xs text-slate-500">{{ formatTime(log.created_at) }}</td>
            <td class="px-6 py-2 text-sm text-slate-700">{{ log.username || '-' }}</td>
            <td class="px-6 py-2">
              <span :class="['text-xs px-2 py-0.5 rounded-md font-medium',
                log.action === 'delete' ? 'bg-red-100 text-red-600' :
                log.action === 'login' ? 'bg-green-100 text-green-600' :
                'bg-blue-100 text-blue-600']">{{ actionLabels[log.action] || log.action }}</span>
            </td>
            <td class="px-6 py-2 text-sm text-slate-700">{{ resourceLabels[log.resource] || log.resource || '-' }}</td>
            <td class="px-6 py-2 text-xs text-slate-500">{{ log.detail ? JSON.stringify(log.detail) : '-' }}</td>
            <td class="px-6 py-2 text-xs text-slate-400">{{ log.ip_address || '-' }}</td>
          </tr>
          <tr v-if="!logs.length && !loadingLogs">
            <td colspan="6" class="px-6 py-8 text-center text-sm text-slate-400">暂无日志</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Tab: 标签管理 -->
    <div v-if="activeTab === 'tags'" class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-slate-800">标签管理</h2>
        <button @click="openTagModal()" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600 transition-all">
          <Plus :size="14" /> 新建标签
        </button>
      </div>
      <div v-if="tags.length === 0" class="text-center text-sm text-slate-400 py-8">暂无标签</div>
      <div v-else class="flex flex-wrap gap-3">
        <div v-for="tag in tags" :key="tag.id" class="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 hover:border-slate-300 transition-all">
          <span class="w-3 h-3 rounded-full" :style="{ background: tag.color }"></span>
          <span class="text-sm font-medium text-slate-700">{{ tag.name }}</span>
          <span class="text-xs text-slate-400">({{ tag.count }})</span>
          <button @click="openTagModal(tag)" class="p-1 text-slate-400 hover:text-blue-500"><Edit3 :size="12" /></button>
          <button @click="deleteTag(tag)" class="p-1 text-slate-400 hover:text-red-500"><Trash2 :size="12" /></button>
        </div>
      </div>
    </div>

    <!-- 标签编辑弹窗 -->
    <div v-if="showTagModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showTagModal = false">
      <div class="bg-white rounded-2xl max-w-sm w-full shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">{{ editingTag ? '编辑标签' : '新建标签' }}</h3>
          <button @click="showTagModal = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">标签名称</label>
            <input v-model="tagForm.name" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="如：一楼、促销">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">颜色</label>
            <input v-model="tagForm.color" type="color" class="w-12 h-10 rounded-lg border border-slate-200 cursor-pointer">
          </div>
        </div>
        <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
          <button @click="showTagModal = false" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
          <button @click="saveTag()" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600">保存</button>
        </div>
      </div>
    </div>

    <!-- Tab: 下发记录 -->
    <div v-if="activeTab === 'commandLogs'" class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <CommandLogs />
    </div>
  </div>
</template>
