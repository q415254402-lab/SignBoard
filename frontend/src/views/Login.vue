<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Monitor, Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

const username = ref('admin')
const password = ref('')
const showPwd = ref(false)
const error = ref('')
const loading = ref(false)

async function doLogin() {
  error.value = ''
  if (!username.value.trim()) { error.value = '请输入账号'; return }
  if (!password.value) { error.value = '请输入密码'; return }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50 flex">
    <!-- Left panel: branding -->
    <div class="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600 p-12 relative overflow-hidden">
      <div class="absolute inset-0 opacity-10">
        <div class="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl"></div>
        <div class="absolute bottom-20 right-20 w-96 h-96 bg-blue-200 rounded-full blur-3xl"></div>
      </div>
      <div class="relative text-white text-center max-w-md">
        <Monitor :size="72" class="mx-auto mb-6 opacity-90" />
        <h1 class="text-4xl font-bold mb-3">SignBoard 2.0</h1>
        <p class="text-lg text-blue-100">数字标牌系统管理后台</p>
        <div class="mt-10 grid grid-cols-3 gap-6 text-blue-100">
          <div>
            <div class="text-2xl font-bold text-white">📺</div>
            <div class="text-sm mt-1">多屏管理</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-white">📅</div>
            <div class="text-sm mt-1">智能排程</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-white">⚡</div>
            <div class="text-sm mt-1">实时推送</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right panel: login form -->
    <div class="flex-1 flex items-center justify-center p-8">
      <div class="w-full max-w-sm">
        <div class="lg:hidden text-center mb-8">
          <Monitor :size="48" class="mx-auto mb-3 text-blue-500" />
          <h1 class="text-2xl font-bold text-slate-800">SignBoard 2.0</h1>
        </div>

        <div class="bg-white rounded-2xl shadow-lg shadow-slate-200/50 p-8">
          <h2 class="text-xl font-bold text-slate-800 text-center mb-6">登录</h2>

          <!-- Error -->
          <div v-if="error" class="mb-4 px-4 py-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
            <span class="text-base">⚠</span>
            <span>{{ error }}</span>
          </div>

          <!-- Username -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-slate-600 mb-1.5">账号</label>
            <input v-model="username" class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all duration-200" placeholder="请输入账号">
          </div>

          <!-- Password -->
          <div class="mb-5">
            <label class="block text-sm font-medium text-slate-600 mb-1.5">密码</label>
            <div class="relative">
              <input v-model="password" :type="showPwd ? 'text' : 'password'" class="w-full px-4 py-2.5 pr-10 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all duration-200" placeholder="请输入密码" @keyup.enter="doLogin()">
              <button @click="showPwd = !showPwd" class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <EyeOff v-if="showPwd" :size="18" />
                <Eye v-else :size="18" />
              </button>
            </div>
          </div>

          <!-- Submit -->
          <button @click="doLogin()" :disabled="loading" class="w-full py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]">
            {{ loading ? '登录中...' : '登 录' }}
          </button>
        </div>

        <p class="text-center text-xs text-slate-400 mt-6">SignBoard v2.0 · 数字标牌系统</p>
      </div>
    </div>
  </div>
</template>
