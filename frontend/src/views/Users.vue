<script setup>
import { ref, onMounted, inject } from 'vue'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { Users as UsersIcon, Plus, Trash2, Edit3, X, Shield } from 'lucide-vue-next'

const toast = inject('toast')
const auth = useAuthStore()
const users = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ username: '', password: '', role: 'operator' })

const roleLabels = { admin: '管理员', operator: '操作员', readonly: '只读' }
const roleColors = { admin: 'bg-red-100 text-red-600', operator: 'bg-blue-100 text-blue-600', readonly: 'bg-slate-100 text-slate-600' }

async function load() {
  try {
    users.value = await authApi.listUsers()
  } catch (e) {
    toast.error(e.message)
  }
}

function openCreate() {
  editing.value = null
  form.value = { username: '', password: '', role: 'operator' }
  showModal.value = true
}

function openEdit(u) {
  editing.value = u
  form.value = { username: u.username, password: '', role: u.role }
  showModal.value = true
}

async function save() {
  if (!form.value.username.trim()) { toast.warning('请输入用户名'); return }
  if (!editing.value && !form.value.password) { toast.warning('请输入密码'); return }

  try {
    if (editing.value) {
      const data = { username: form.value.username, role: form.value.role }
      if (form.value.password) data.password = form.value.password
      await authApi.updateUser(editing.value.id, data)
    } else {
      await authApi.createUser(form.value)
    }
    showModal.value = false
    await load()
    toast.success(editing.value ? '用户已更新' : '用户已创建')
  } catch (e) {
    toast.error(e.message)
  }
}

async function remove(u) {
  if (!confirm(`确定删除用户「${u.username}」？`)) return
  try {
    await authApi.deleteUser(u.id)
    toast.success('已删除')
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-lg font-bold text-slate-800">用户管理</h1>
      <button @click="openCreate()" class="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all shadow-lg shadow-blue-500/25">
        <Plus :size="18" />
        新建用户
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">用户名</th>
            <th class="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">角色</th>
            <th class="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">创建时间</th>
            <th class="text-right px-6 py-3 text-xs font-medium text-slate-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <span class="text-sm font-medium text-blue-600">{{ u.username[0].toUpperCase() }}</span>
                </div>
                <span class="font-medium text-slate-800">{{ u.username }}</span>
                <span v-if="u.username === auth.username" class="text-xs text-slate-400">(当前)</span>
              </div>
            </td>
            <td class="px-6 py-4">
              <span :class="['px-2 py-1 text-xs font-medium rounded-lg', roleColors[u.role]]">
                {{ roleLabels[u.role] || u.role }}
              </span>
            </td>
            <td class="px-6 py-4 text-sm text-slate-500">{{ u.created_at?.split('T')[0] || '-' }}</td>
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-1">
                <button @click="openEdit(u)" class="p-1.5 text-slate-400 hover:text-blue-500 rounded-lg hover:bg-blue-50 transition-all">
                  <Edit3 :size="14" />
                </button>
                <button v-if="u.username !== auth.username" @click="remove(u)" class="p-1.5 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-all">
                  <Trash2 :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showModal = false">
      <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">{{ editing ? '编辑用户' : '新建用户' }}</h3>
          <button @click="showModal = false" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">用户名</label>
            <input v-model="form.username" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="输入用户名">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">密码 {{ editing ? '(留空不修改)' : '' }}</label>
            <input v-model="form.password" type="password" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400" placeholder="输入密码">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-600 mb-1.5">角色</label>
            <select v-model="form.role" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400">
              <option value="admin">管理员 - 全部权限</option>
              <option value="operator">操作员 - 管理素材/布局/排程</option>
              <option value="readonly">只读 - 仅查看</option>
            </select>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
          <button @click="showModal = false" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
          <button @click="save()" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
