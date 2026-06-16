<script setup>
import { useAuthStore } from './stores/auth'
import { useAppStore } from './stores/app'
import { useRouter, useRoute } from 'vue-router'
import { computed, provide, ref } from 'vue'
import {
  LayoutDashboard, Image, Layout, Calendar, Monitor,
  Menu, User, KeyRound, LogOut, ChevronLeft, Users, Settings, Power
} from 'lucide-vue-next'
import Toast from './components/Toast.vue'

const auth = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const route = useRoute()
const toastRef = ref(null)

// 提供 toast 给所有子组件
provide('toast', {
  success: (msg, dur) => toastRef.value?.success(msg, dur),
  error: (msg, dur) => toastRef.value?.error(msg, dur),
  info: (msg, dur) => toastRef.value?.info(msg, dur),
  warning: (msg, dur) => toastRef.value?.warning(msg, dur),
})

const isLoginPage = computed(() => route.path === '/login')

const navItems = computed(() => {
  const items = [
    { name: '仪表盘', path: '/dashboard', icon: LayoutDashboard },
    { name: '素材管理', path: '/media', icon: Image },
    { name: '布局设计', path: '/layouts', icon: Layout },
    { name: '排程管理', path: '/schedules', icon: Calendar },
    { name: '屏幕管理', path: '/displays', icon: Monitor },
    { name: '开关机计划', path: '/power-schedules', icon: Power },
  ]
  if (auth.isAdmin) {
    items.push({ name: '用户管理', path: '/users', icon: Users })
  }
  return items
})

function isActive(path) {
  if (path === '/schedules') return route.path.startsWith('/schedules')
  return route.path === path
}

function goLogout() {
  auth.logout()
  router.push('/login')
}

// changepassword — 跳转到 Settings 页面
</script>

<template>
  <Toast ref="toastRef" />
  <div v-if="isLoginPage" class="min-h-screen">
    <router-view />
  </div>

  <div v-else class="min-h-screen bg-slate-50 flex">

    <!-- Sidebar -->
    <aside :class="[
      'fixed left-0 top-0 h-full bg-white border-r border-slate-200 flex flex-col z-30 transition-all duration-300',
      appStore.sidebarCollapsed ? 'w-[68px]' : 'w-[220px]'
    ]">
      <!-- Logo -->
      <div class="flex items-center gap-3 px-4 h-16 border-b border-slate-100 shrink-0">
        <span class="text-2xl flex-shrink-0">🖥</span>
        <span v-if="!appStore.sidebarCollapsed" class="font-bold text-lg whitespace-nowrap">SignBoard</span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <button
          v-for="item in navItems" :key="item.path"
          @click="router.push(item.path)"
          :title="appStore.sidebarCollapsed ? item.name : ''"
          :class="[
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
            isActive(item.path)
              ? 'bg-blue-50 text-blue-600'
              : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
          ]"
        >
          <component :is="item.icon" :size="20" class="flex-shrink-0" />
          <span v-if="!appStore.sidebarCollapsed">{{ item.name }}</span>
        </button>
      </nav>

      <!-- Collapse button -->
      <div class="px-3 py-3 border-t border-slate-100">
        <button
          @click="appStore.toggleSidebar()"
          class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all duration-200"
        >
          <ChevronLeft :size="18" :class="{ 'rotate-180': appStore.sidebarCollapsed }" class="transition-transform duration-300" />
          <span v-if="!appStore.sidebarCollapsed" class="text-xs">收起菜单</span>
        </button>
      </div>
    </aside>

    <!-- Main content area -->
    <div :class="[
      'flex-1 flex flex-col min-h-screen transition-all duration-300',
      appStore.sidebarCollapsed ? 'ml-[68px]' : 'ml-[220px]'
    ]">
      <!-- Top header -->
      <header class="sticky top-0 z-20 h-16 bg-white/70 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-6">
        <!-- Page title -->
        <div class="flex items-center gap-3">
          <button @click="appStore.toggleSidebar()" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 md:hidden">
            <Menu :size="20" />
          </button>
          <h1 class="text-lg font-semibold text-slate-800">
            {{ navItems.find(i => isActive(i.path))?.name || 'SignBoard' }}
          </h1>
        </div>

        <!-- User area (右上角) -->
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-xl">
            <div class="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold">
              {{ auth.username.charAt(0).toUpperCase() }}
            </div>
            <span class="text-sm font-medium text-slate-700">{{ auth.username }}</span>
          </div>

          <div class="h-6 w-px bg-slate-200"></div>

          <button @click="router.push('/settings')" class="flex items-center gap-1 px-2 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all duration-200">
            <Settings :size="16" />
            <span class="hidden sm:inline">更多</span>
          </button>

          <button @click="goLogout()" class="flex items-center gap-1 px-2 py-1.5 text-sm text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200">
            <LogOut :size="16" />
            <span class="hidden sm:inline">退出</span>
          </button>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
