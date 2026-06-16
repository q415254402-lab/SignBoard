import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/media', component: () => import('../views/Media.vue') },
  { path: '/layouts', component: () => import('../views/Layouts.vue') },
  { path: '/schedules', component: () => import('../views/Schedules.vue') },
  { path: '/schedules/calendar', component: () => import('../views/ScheduleCalendar.vue') },
  { path: '/displays', component: () => import('../views/Displays.vue') },
  { path: '/power-schedules', component: () => import('../views/PowerSchedules.vue') },
  { path: '/settings', component: () => import('../views/Settings.vue') },
  { path: '/users', component: () => import('../views/Users.vue'), meta: { admin: true } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  // 公开页面直接放行
  if (to.meta.public) {
    if (to.path === '/login' && auth.isLoggedIn) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }
  // 已登录直接放行
  if (auth.isLoggedIn) {
    // 管理员页面检查
    if (to.meta.admin && !auth.isAdmin) {
      next('/dashboard')
      return
    }
    next()
    return
  }
  // 尝试用 cookie 恢复登录状态
  const ok = await auth.checkAuth()
  next(ok ? undefined : '/login')
})

export default router
