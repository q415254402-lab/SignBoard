import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || 'admin')
  const isLoggedIn = computed(() => !!username.value)
  const isAdmin = computed(() => role.value === 'admin')
  const canWrite = computed(() => role.value !== 'readonly')

  async function login(user, pass) {
    const res = await authApi.login(user, pass)
    username.value = res.username
    role.value = res.role || 'admin'
    localStorage.setItem('username', res.username)
    localStorage.setItem('role', res.role || 'admin')
  }

  async function checkAuth() {
    try {
      const res = await authApi.me()
      username.value = res.username
      role.value = res.role || 'admin'
      localStorage.setItem('username', res.username)
      localStorage.setItem('role', res.role || 'admin')
      return true
    } catch {
      username.value = ''
      role.value = 'admin'
      localStorage.removeItem('username')
      localStorage.removeItem('role')
      return false
    }
  }

  function logout() {
    authApi.logout().catch(() => {})
    username.value = ''
    role.value = 'admin'
    localStorage.removeItem('username')
    localStorage.removeItem('role')
  }

  return { username, role, isLoggedIn, isAdmin, canWrite, login, logout, checkAuth }
})
