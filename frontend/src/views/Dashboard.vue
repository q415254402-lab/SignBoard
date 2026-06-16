<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { displayApi } from '../api/display'
import { mediaApi } from '../api/media'
import { scheduleApi } from '../api/schedule'
import { Monitor, MonitorCheck, Image, Calendar, RefreshCw } from 'lucide-vue-next'

const stats = ref({ totalDisplays: 0, onlineDisplays: 0, totalMedia: 0, activeSchedules: 0 })
const screenshots = ref([])
let timer = null
let pollInterval = 30000

async function load() {
  try {
    const [displayStats, mediaStats, scheduleStats, displays] = await Promise.all([
      displayApi.count(),
      mediaApi.count(),
      scheduleApi.count(),
      displayApi.list()  // 截图仍需全量数据
    ])
    stats.value.totalDisplays = displayStats.total
    stats.value.onlineDisplays = displayStats.online
    stats.value.totalMedia = mediaStats.total
    stats.value.activeSchedules = scheduleStats.active

    // Build screenshots with display info
    screenshots.value = displays.map(d => ({
      ...d,
      screenshotUrl: d.last_screenshot ? `${displayApi.getScreenshot(d.id)}?t=${Date.now()}` : null
    }))
    // 成功后重置轮询间隔
    pollInterval = 30000
  } catch (e) {
    console.error(e)
    // 失败后加倍轮询间隔（最大 5 分钟）
    pollInterval = Math.min(pollInterval * 2, 300000)
  }
}

function startPolling() {
  load()
  timer = setInterval(load, pollInterval)
}

onMounted(startPolling)
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div>
    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-300">
        <div class="flex items-center justify-between mb-3">
          <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <Monitor :size="20" class="text-blue-500" />
          </div>
        </div>
        <div class="text-3xl font-bold text-slate-800">{{ stats.totalDisplays }}</div>
        <div class="text-sm text-slate-500 mt-1">总屏幕数</div>
        <div class="mt-3 h-1 rounded-full bg-blue-100"><div class="h-full rounded-full bg-blue-400" style="width:100%"></div></div>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-300">
        <div class="flex items-center justify-between mb-3">
          <div class="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
            <MonitorCheck :size="20" class="text-green-500" />
          </div>
        </div>
        <div class="text-3xl font-bold text-green-600">{{ stats.onlineDisplays }}</div>
        <div class="text-sm text-slate-500 mt-1">在线屏幕</div>
        <div class="mt-3 h-1 rounded-full bg-green-100">
          <div class="h-full rounded-full bg-green-400" :style="{ width: stats.totalDisplays ? (stats.onlineDisplays / stats.totalDisplays * 100) + '%' : '0%' }"></div>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-300">
        <div class="flex items-center justify-between mb-3">
          <div class="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
            <Image :size="20" class="text-purple-500" />
          </div>
        </div>
        <div class="text-3xl font-bold text-slate-800">{{ stats.totalMedia }}</div>
        <div class="text-sm text-slate-500 mt-1">素材总数</div>
        <div class="mt-3 h-1 rounded-full bg-purple-100"><div class="h-full rounded-full bg-purple-400" style="width:100%"></div></div>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-300">
        <div class="flex items-center justify-between mb-3">
          <div class="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center">
            <Calendar :size="20" class="text-amber-500" />
          </div>
        </div>
        <div class="text-3xl font-bold text-slate-800">{{ stats.activeSchedules }}</div>
        <div class="text-sm text-slate-500 mt-1">活跃排程</div>
        <div class="mt-3 h-1 rounded-full bg-amber-100"><div class="h-full rounded-full bg-amber-400" style="width:100%"></div></div>
      </div>
    </div>

    <!-- Screenshots -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-bold text-slate-800">屏幕实时截图</h2>
      <button @click="load()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all duration-200">
        <RefreshCw :size="14" />
        刷新
      </button>
    </div>

    <div v-if="screenshots.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
      <Monitor :size="48" class="mx-auto mb-4 text-slate-300" />
      <p class="text-slate-500 font-medium">还没有屏幕接入</p>
      <p class="text-sm text-slate-400 mt-1">在 Player 上输入服务器地址启动后会自动注册到这里</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div v-for="d in screenshots" :key="d.id" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all duration-300 group">
        <!-- Screenshot -->
        <div class="relative bg-slate-900 flex items-center justify-center" style="height: 160px;">
          <img v-if="d.screenshotUrl" :src="d.screenshotUrl" class="w-full h-full object-contain" alt="截图">
          <div v-else class="text-slate-500 text-sm">暂无截图</div>
          <!-- Online dot -->
          <div class="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full">
            <span class="w-2 h-2 rounded-full" :class="d.status === 'online' ? 'bg-green-400 animate-pulse' : 'bg-slate-400'"></span>
            <span class="text-xs text-white">{{ d.status === 'online' ? '在线' : '离线' }}</span>
          </div>
        </div>
        <!-- Info -->
        <div class="p-4">
          <div class="font-semibold text-slate-800 truncate">{{ d.name }}</div>
          <div class="text-xs text-slate-400 mt-1">{{ d.screen_width }}×{{ d.screen_height }} · {{ d.screen_orientation === 'portrait' ? '竖屏' : '横屏' }}</div>
          <div v-if="d.current_program" class="text-xs text-blue-500 mt-1.5 truncate">当前: {{ d.current_program }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
