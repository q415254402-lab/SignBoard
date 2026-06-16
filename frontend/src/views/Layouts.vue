<script setup>
import { ref, onMounted, inject, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { layoutApi } from '../api/layout'
import { mediaApi } from '../api/media'
import { Plus, Trash2, Edit3, Monitor, X, Layout as LayoutIcon, Image, LayoutGrid, List, Search, ChevronRight, ChevronLeft, ChevronUp, ChevronDown, Eye } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = inject('toast')
const layouts = ref([])
const mediaList = ref([])
const modal = ref(null)
const form = ref({ name: '', type: 'fullscreen', width: 1920, height: 1080, description: '', zones: [{ id: 1, x: 0, y: 0, w: 1, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }] })
const loading = ref(false)
const viewMode = ref(localStorage.getItem('layouts_viewMode') || 'card')
const searchText = ref('')
const modalDirty = ref(false)

// 素材选择器状态
const editingZoneIndex = ref(null)
const mediaSearch = ref('')
const mediaTypeFilter = ref('')
const selectedMediaIds = ref(new Set())
const hoveredMediaId = ref(null)
const previewMedia = ref(null)
const previewPptSlides = ref([])
const previewSlideIndex = ref(0)

async function openMediaPreview(media) {
  previewMedia.value = media
  previewPptSlides.value = []
  previewSlideIndex.value = 0
  if (media.type === 'ppt') {
    try { const res = await mediaApi.getSlides(media.id); previewPptSlides.value = res.slides || [] } catch {}
  }
}

function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem('layouts_viewMode', mode)
}

const layoutTypes = [
  { value: 'fullscreen', label: '全屏轮播', zones: [{ id: 1, x: 0, y: 0, w: 1, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }] },
  { value: 'playlist', label: '播放列表', zones: [{ id: 1, x: 0, y: 0, w: 1, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }] },
  { value: 'webpage', label: '网页组件', zones: [{ id: 1, x: 0, y: 0, w: 1, h: 1, media_id: null, url: '', duration_seconds: 30, volume: 80, fill_mode: 'fill' }] },
  { value: 'split_2', label: '左右分屏', zones: [
    { id: 1, x: 0, y: 0, w: 0.6, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' },
    { id: 2, x: 0.6, y: 0, w: 0.4, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }
  ]},
  { value: 'split_3', label: '上中下三分屏', zones: [
    { id: 1, x: 0, y: 0, w: 1, h: 0.35, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' },
    { id: 2, x: 0, y: 0.35, w: 1, h: 0.3, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' },
    { id: 3, x: 0, y: 0.65, w: 1, h: 0.35, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }
  ]},
]

function zoneDefaults(template) {
  return (layoutTypes.find(t => t.value === template) || layoutTypes[0]).zones.map((z, i) => ({ ...z, id: i + 1 }))
}

const filteredLayouts = computed(() => {
  if (!searchText.value.trim()) return layouts.value
  const q = searchText.value.trim().toLowerCase()
  return layouts.value.filter(l => l.name.toLowerCase().includes(q))
})

// 素材库筛选
const filteredMediaList = computed(() => {
  let list = mediaList.value
  if (mediaTypeFilter.value) {
    list = list.filter(m => m.type === mediaTypeFilter.value)
  }
  if (mediaSearch.value.trim()) {
    const q = mediaSearch.value.trim().toLowerCase()
    list = list.filter(m => m.name.toLowerCase().includes(q))
  }
  return list
})

// 当前编辑区域已绑定的素材
const currentZoneMedia = computed(() => {
  if (editingZoneIndex.value === null) return null
  const zone = form.value.zones[editingZoneIndex.value]
  if (!zone || !zone.media_id) return null
  return mediaList.value.find(m => m.id === zone.media_id) || null
})

async function load() {
  loading.value = true
  try {
    const [layoutsData, mediaData] = await Promise.all([
      layoutApi.list(),
      mediaApi.list()
    ])
    layouts.value = layoutsData
    mediaList.value = mediaData
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  const tpl = layoutTypes[0]
  form.value = { name: '', type: tpl.value, width: 1920, height: 1080, description: '', zones: zoneDefaults(tpl.value) }
  modalDirty.value = false
  editingZoneIndex.value = 0
  mediaSearch.value = ''
  mediaTypeFilter.value = ''
  selectedMediaIds.value = new Set()
  modal.value = {}
}

function openEdit(item) {
  form.value = {
    name: item.name, type: item.type || 'fullscreen',
    width: item.resolution_width || 1920, height: item.resolution_height || 1080,
    description: item.description || item.name || '',
    zones: (item.zones || []).map((z, i) => ({
      id: i + 1, x: z.x ?? 0, y: z.y ?? 0, w: z.w ?? 1, h: z.h ?? 1,
      media_id: z.media_id || null, duration_seconds: z.duration_seconds || 30,
      volume: z.volume != null ? z.volume : 80, fill_mode: z.fill_mode || 'fill',
      ppt_mode: z.ppt_mode || null, ppt_slide_index: z.ppt_slide_index ?? null,
      url: z.url || ''
    }))
  }
  if (form.value.zones.length === 0) form.value.zones = zoneDefaults(item.type)
  modalDirty.value = false
  editingZoneIndex.value = 0
  mediaSearch.value = ''
  mediaTypeFilter.value = ''
  selectedMediaIds.value = new Set()
  modal.value = { editing: item }
}

function tryCloseModal() {
  if (!modalDirty.value) { modal.value = null; return }
  if (confirm('有未保存的修改，确定关闭？')) modal.value = null
}

function markDirty() { modalDirty.value = true }

async function save() {
  if (!form.value.name.trim()) { toast.warning('请输入布局名称'); return }
  try {
    const payload = {
      name: form.value.name.trim(), type: form.value.type,
      resolution_width: form.value.width, resolution_height: form.value.height,
      zones: form.value.zones.map(z => ({
        x: z.x, y: z.y, w: z.w, h: z.h, media_id: z.media_id || null,
        duration_seconds: z.duration_seconds, volume: z.volume, fill_mode: z.fill_mode,
        ppt_mode: z.ppt_mode || null, ppt_slide_index: z.ppt_slide_index ?? null,
        url: z.url || null
      }))
    }
    if (modal.value?.editing) await layoutApi.update(modal.value.editing.id, payload)
    else await layoutApi.create(payload)
    modalDirty.value = false; modal.value = null; await load()
  } catch (e) { toast.error(e.message) }
}

async function remove(item) {
  if (!confirm(`确定删除布局「${item.name}」？`)) return
  try { await layoutApi.remove(item.id); await load(); toast.success('已删除') } catch (e) { toast.error(e.message) }
}

function onTypeChange(type) {
  form.value.type = type; form.value.zones = zoneDefaults(type)
  editingZoneIndex.value = 0; markDirty()
}

function selectZone(index) { editingZoneIndex.value = index; selectedMediaIds.value = new Set() }

function getMediaById(id) { return mediaList.value.find(m => m.id === id) || null }

function getThumbnailUrl(media) {
  if (!media) return null
  if (media.thumbnail_path) return `/uploads/${media.thumbnail_path}`
  if (media.type === 'image') return `/uploads/${media.file_path}`
  return null
}

function getOriginalUrl(media) {
  if (!media) return null
  return `/uploads/${media.file_path}`
}

function getPreviewStyle() {
  const w = form.value.width || 1920
  const h = form.value.height || 1080
  const ratio = w / h
  const maxW = 600
  const maxH = 500
  let boxW, boxH
  if (ratio >= 1) {
    boxW = maxW
    boxH = maxW / ratio
    if (boxH > maxH) { boxH = maxH; boxW = maxH * ratio }
  } else {
    boxH = maxH
    boxW = maxH * ratio
    if (boxW > maxW) { boxW = maxW; boxH = maxW / ratio }
  }
  return { width: boxW + 'px', height: boxH + 'px' }
}

// 选择素材到区域
function selectMediaForZone(mediaId) {
  if (editingZoneIndex.value === null) return
  form.value.zones[editingZoneIndex.value].media_id = mediaId
  markDirty()
}

// 批量选择
function toggleMediaSelect(mediaId) {
  const s = new Set(selectedMediaIds.value)
  if (s.has(mediaId)) s.delete(mediaId)
  else s.add(mediaId)
  selectedMediaIds.value = s
}

// 添加到区域（替换）
function addToZone() {
  if (editingZoneIndex.value === null || !selectedMediaIds.value.size) return
  const firstId = selectedMediaIds.value.values().next().value
  form.value.zones[editingZoneIndex.value].media_id = firstId
  markDirty()
}

onMounted(async () => {
  await load()
  // 从 URL 参数自动打开编辑器
  const layoutId = parseInt(route.query.id)
  if (layoutId) {
    const item = layouts.value.find(l => l.id === layoutId)
    if (item) openEdit(item)
    router.replace('/layouts')
  }
})
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <div v-if="layouts.length > 0" class="relative">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input v-model="searchText" class="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500/20" placeholder="搜索布局...">
        </div>
      </div>
      <div class="flex items-center gap-2">
        <div v-if="layouts.length > 0" class="flex items-center border border-slate-200 rounded-lg overflow-hidden">
          <button @click="setViewMode('card')" :class="['p-1.5 transition-all', viewMode === 'card' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><LayoutGrid :size="16" /></button>
          <button @click="setViewMode('list')" :class="['p-1.5 transition-all', viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><List :size="16" /></button>
        </div>
        <button @click="openCreate()" class="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all shadow-lg shadow-blue-500/25 active:scale-[0.98]">
          <Plus :size="18" /> 新建布局
        </button>
      </div>
    </div>

    <div v-if="!loading && layouts.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
      <LayoutIcon :size="48" class="mx-auto mb-4 text-slate-300" />
      <p class="text-slate-500 font-medium">还没有布局</p>
      <p class="text-sm text-slate-400 mt-1">创建一个布局来定义屏幕的播放区域和素材</p>
    </div>
    <div v-if="loading" class="text-center py-12 text-slate-400">加载中...</div>

    <!-- Card view -->
    <template v-if="viewMode === 'card' && !loading && layouts.length > 0">
      <div v-if="filteredLayouts.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100"><p class="text-slate-400">无匹配布局</p></div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="item in filteredLayouts" :key="item.id" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all group">
          <div class="relative bg-slate-50 flex items-center justify-center p-4" style="height: 160px;">
            <div class="relative border-2 border-slate-200 rounded-lg bg-white shadow-sm" style="width:85%;height:85%">
              <div v-for="z in (item.zones || [{x:0,y:0,w:1,h:1}])" :key="z.id || z.x" class="absolute border border-dashed border-blue-300 bg-blue-50/50 flex items-center justify-center text-xs text-blue-400 font-medium" :style="{ left: (z.x*100)+'%', top: (z.y*100)+'%', width: (z.w*100)+'%', height: (z.h*100)+'%' }">
                {{ (item.zones?.length||1) > 1 ? (z.id||'') : '全屏' }}
              </div>
            </div>
          </div>
          <div class="p-4">
            <div class="font-semibold text-slate-800 truncate">{{ item.name }}</div>
            <div class="flex items-center gap-2 mt-1.5">
              <Monitor :size="14" class="text-slate-400" />
              <span class="text-xs text-slate-400">{{ item.resolution_width||1920 }}x{{ item.resolution_height||1080 }} / {{ (item.zones||[1]).length }}区域</span>
              <span class="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded-md">{{ {fullscreen:'全屏',playlist:'列表',split_2:'二分屏',split_3:'三分屏'}[item.type]||item.type }}</span>
            </div>
            <div class="flex gap-2 mt-3 pt-3 border-t border-slate-50">
              <button @click="openEdit(item)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg"><Edit3 :size="14" /> 编辑</button>
              <button @click="remove(item)" class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg"><Trash2 :size="14" /> 删除</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- List view -->
    <div v-if="viewMode === 'list' && !loading" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <table class="w-full">
        <thead><tr class="border-b border-slate-100 bg-slate-50">
          <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">名称</th>
          <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">类型</th>
          <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">分辨率</th>
          <th class="text-left px-6 py-2 text-xs font-medium text-slate-500">绑定素材</th>
          <th class="text-right px-6 py-2 text-xs font-medium text-slate-500">操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="item in filteredLayouts" :key="item.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="px-6 py-3 font-medium text-slate-800 text-sm">{{ item.name }}</td>
            <td class="px-6 py-3"><span class="text-xs px-2 py-0.5 rounded-md bg-blue-50 text-blue-500">{{ {fullscreen:'全屏',playlist:'列表',webpage:'网页',split_2:'二分屏',split_3:'三分屏'}[item.type]||item.type }}</span></td>
            <td class="px-6 py-3 text-sm text-slate-500">{{ item.resolution_width||1920 }}x{{ item.resolution_height||1080 }}</td>
            <td class="px-6 py-3">
              <div class="flex items-center gap-1.5 flex-wrap">
                <template v-for="z in (item.zones || [])" :key="z.id || z.x">
                  <div v-if="z.media_id && getMediaById(z.media_id)" @click="openMediaPreview(getMediaById(z.media_id))" class="flex items-center gap-1 bg-slate-50 rounded-lg px-1.5 py-0.5 cursor-pointer hover:bg-slate-100 transition-colors">
                    <div class="w-5 h-5 rounded bg-slate-100 overflow-hidden flex-shrink-0 relative">
                      <img v-if="getThumbnailUrl(getMediaById(z.media_id))" :src="getThumbnailUrl(getMediaById(z.media_id))" class="w-full h-full object-cover">
                      <video v-else-if="getMediaById(z.media_id)?.type === 'video'" :src="mediaApi.getUrl(getMediaById(z.media_id)?.file_path)" class="w-full h-full object-cover" muted preload="metadata"></video>
                      <span v-else class="text-[8px] text-slate-400 flex items-center justify-center h-full">{{ getMediaById(z.media_id)?.type?.charAt(0).toUpperCase() }}</span>
                      <div v-if="getMediaById(z.media_id)?.type === 'video' && !getThumbnailUrl(getMediaById(z.media_id))" class="absolute inset-0 bg-black/40 flex items-center justify-center">
                        <svg class="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                      </div>
                    </div>
                    <span class="text-[10px] text-slate-600 max-w-[80px] truncate">{{ getMediaById(z.media_id)?.name }}</span>
                  </div>
                  <div v-else-if="z.url" class="flex items-center gap-1 bg-slate-50 rounded-lg px-1.5 py-0.5">
                    <span class="text-[10px] text-slate-500">网页</span>
                  </div>
                </template>
                <span v-if="!(item.zones || []).some(z => z.media_id || z.url)" class="text-xs text-slate-400">未绑定</span>
              </div>
            </td>
            <td class="px-6 py-3 text-right">
              <div class="flex items-center justify-end gap-1">
                <button @click="openEdit(item)" class="p-1.5 text-slate-400 hover:text-blue-500 rounded-lg hover:bg-blue-50"><Edit3 :size="14" /></button>
                <button @click="remove(item)" class="p-1.5 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50"><Trash2 :size="14" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredLayouts.length"><td colspan="5" class="px-6 py-8 text-center text-sm text-slate-400">无匹配布局</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Edit Modal - 全屏编辑器 -->
    <div v-if="modal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-2">
      <div class="bg-white rounded-2xl w-full h-[95vh] max-w-[1400px] flex flex-col shadow-2xl overflow-hidden" @click.stop>
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-3 border-b border-slate-100 shrink-0">
          <h3 class="font-semibold text-slate-800">{{ modal.editing ? '编辑布局' : '新建布局' }}</h3>
          <div class="flex items-center gap-3">
            <button @click="tryCloseModal()" class="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-xl">取消</button>
            <button @click="save()" :disabled="!form.name.trim()" class="px-6 py-2 text-sm bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50">保存</button>
          </div>
        </div>

        <!-- Body: 三栏布局 -->
        <div class="flex-1 flex overflow-hidden">
          <!-- 左栏: 属性配置 -->
          <div class="w-64 border-r border-slate-100 p-4 overflow-y-auto shrink-0 space-y-4">
            <!-- 类型 -->
            <div>
              <label class="block text-xs font-medium text-slate-500 mb-1.5">布局类型</label>
              <select v-model="form.type" @change="onTypeChange(form.type)" class="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/20">
                <option v-for="t in layoutTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
            <!-- 名称 -->
            <div>
              <label class="block text-xs font-medium text-slate-500 mb-1.5">布局名称</label>
              <input v-model="form.name" @input="markDirty()" class="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/20" placeholder="布局名称">
            </div>
            <!-- 分辨率 -->
            <div>
              <label class="block text-xs font-medium text-slate-500 mb-1.5">分辨率</label>
              <div class="flex gap-1.5 mb-2">
                <button @click="form.width = 1920; form.height = 1080; markDirty()" :class="['px-2 py-1 text-[10px] rounded-lg border transition-all', form.width === 1920 && form.height === 1080 ? 'border-blue-400 bg-blue-50 text-blue-600' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
                  横屏 1920x1080
                </button>
                <button @click="form.width = 1080; form.height = 1920; markDirty()" :class="['px-2 py-1 text-[10px] rounded-lg border transition-all', form.width === 1080 && form.height === 1920 ? 'border-blue-400 bg-blue-50 text-blue-600' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
                  竖屏 1080x1920
                </button>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div><label class="block text-[10px] text-slate-400 mb-0.5">宽</label><input v-model.number="form.width" @input="markDirty()" type="number" class="w-full px-2 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500/20"></div>
                <div><label class="block text-[10px] text-slate-400 mb-0.5">高</label><input v-model.number="form.height" @input="markDirty()" type="number" class="w-full px-2 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500/20"></div>
              </div>
            </div>

            <!-- 区域列表 -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-xs font-medium text-slate-500">播放区域</label>
                <button @click="form.zones.push({ id: Date.now(), x: 0, y: 0, w: 1, h: 1, media_id: null, duration_seconds: 30, volume: 80, fill_mode: 'fill' }); editingZoneIndex = form.zones.length - 1; markDirty()" class="text-xs text-blue-500 hover:text-blue-700">+ 添加</button>
              </div>
              <div class="space-y-1.5">
                <div v-for="(z, i) in form.zones" :key="z.id" @click="selectZone(i)" :class="['flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all border', editingZoneIndex === i ? 'bg-blue-50 border-blue-300' : 'bg-slate-50 border-transparent hover:bg-slate-100']">
                  <span class="w-6 h-6 rounded-lg text-xs font-medium flex items-center justify-center" :class="editingZoneIndex === i ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-500'">{{ i + 1 }}</span>
                  <div class="flex-1 min-w-0">
                    <div class="text-xs text-slate-600 truncate">{{ z.media_id ? getMediaById(z.media_id)?.name || '已绑定' : (z.url ? '网页' : '未绑定') }}</div>
                    <div v-if="getMediaById(z.media_id)?.type === 'ppt'" class="text-[10px] text-blue-400">{{ z.ppt_mode === 'fixed' ? '固定第' + ((z.ppt_slide_index || 0) + 1) + '页' : '轮播全部页' }}</div>
                  </div>
                  <button v-if="form.zones.length > 1" @click.stop="form.zones.splice(i, 1); if(editingZoneIndex >= form.zones.length) editingZoneIndex = form.zones.length - 1; markDirty()" class="text-slate-400 hover:text-red-500"><X :size="12" /></button>
                </div>
              </div>
            </div>

            <!-- 当前区域属性 -->
            <div v-if="editingZoneIndex !== null && form.zones[editingZoneIndex]" class="space-y-2 pt-2 border-t border-slate-100">
              <label class="text-xs font-medium text-slate-500">区域 #{{ editingZoneIndex + 1 }} 属性</label>
              <div class="grid grid-cols-2 gap-1.5">
                <div><label class="text-[10px] text-slate-400">左</label><input v-model.number="form.zones[editingZoneIndex].x" @input="markDirty()" type="number" step="0.01" min="0" max="1" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs text-center focus:outline-none"></div>
                <div><label class="text-[10px] text-slate-400">顶</label><input v-model.number="form.zones[editingZoneIndex].y" @input="markDirty()" type="number" step="0.01" min="0" max="1" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs text-center focus:outline-none"></div>
                <div><label class="text-[10px] text-slate-400">宽</label><input v-model.number="form.zones[editingZoneIndex].w" @input="markDirty()" type="number" step="0.01" min="0" max="1" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs text-center focus:outline-none"></div>
                <div><label class="text-[10px] text-slate-400">高</label><input v-model.number="form.zones[editingZoneIndex].h" @input="markDirty()" type="number" step="0.01" min="0" max="1" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs text-center focus:outline-none"></div>
              </div>
              <div><label class="text-[10px] text-slate-400">时长(秒)</label><input v-model.number="form.zones[editingZoneIndex].duration_seconds" @input="markDirty()" type="number" min="1" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs focus:outline-none"></div>
              <div><label class="text-[10px] text-slate-400">音量</label><input v-model.number="form.zones[editingZoneIndex].volume" @input="markDirty()" type="number" min="0" max="100" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs focus:outline-none"></div>
              <!-- 网页组件 URL -->
              <div v-if="form.type === 'webpage'">
                <label class="text-[10px] text-slate-400">网页地址</label>
                <input v-model="form.zones[editingZoneIndex].url" @input="markDirty()" type="url" class="w-full px-1.5 py-1 border border-slate-200 rounded text-xs focus:outline-none" placeholder="https://example.com">
              </div>
              <!-- PPT 播放设置 -->
              <div v-if="getMediaById(form.zones[editingZoneIndex].media_id)?.type === 'ppt'" class="bg-blue-50 rounded-lg p-2 space-y-2">
                <div class="text-[10px] font-medium text-blue-600">PPT 播放设置</div>
                <div>
                  <label class="text-[10px] text-slate-500 mb-0.5 block">播放模式</label>
                  <select v-model="form.zones[editingZoneIndex].ppt_mode" @change="markDirty()" class="w-full px-2 py-1 border border-slate-200 rounded text-xs focus:outline-none">
                    <option :value="null">轮播全部页</option>
                    <option value="fixed">固定某一页</option>
                  </select>
                </div>
                <div v-if="form.zones[editingZoneIndex].ppt_mode === 'fixed'">
                  <label class="text-[10px] text-slate-500 mb-0.5 block">选择页码</label>
                  <select v-model.number="form.zones[editingZoneIndex].ppt_slide_index" @change="markDirty()" class="w-full px-2 py-1 border border-slate-200 rounded text-xs focus:outline-none">
                    <option v-for="(img, idx) in getMediaById(form.zones[editingZoneIndex].media_id)?.ppt_images || []" :key="idx" :value="idx">第 {{ idx + 1 }} 页</option>
                  </select>
                </div>
                <div v-if="form.zones[editingZoneIndex].ppt_mode !== 'fixed'" class="space-y-2">
                  <div class="text-[10px] text-slate-400">共 {{ getMediaById(form.zones[editingZoneIndex].media_id)?.ppt_images?.length || 0 }} 页</div>
                  <div>
                    <label class="text-[10px] text-slate-500 mb-0.5 block">每页时长(秒)</label>
                    <input v-model.number="form.zones[editingZoneIndex].duration_seconds" @input="markDirty()" type="number" min="1" max="3600" class="w-full px-2 py-1 border border-slate-200 rounded text-xs focus:outline-none">
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 中栏: 布局预览 -->
          <div class="flex-1 flex items-center justify-center bg-slate-50 p-4 overflow-hidden">
            <div class="relative border-2 border-slate-300 rounded-lg bg-white shadow" :style="getPreviewStyle()">
              <div v-for="(z, i) in form.zones" :key="z.id" @click="selectZone(i)" :class="['absolute border-2 rounded cursor-pointer transition-all flex items-center justify-center overflow-hidden', editingZoneIndex === i ? 'border-blue-500 bg-blue-50/80' : 'border-slate-300 bg-slate-50/50 hover:border-blue-300']" :style="{ left: (z.x*100)+'%', top: (z.y*100)+'%', width: (z.w*100)+'%', height: (z.h*100)+'%' }">
                <template v-if="z.media_id && getMediaById(z.media_id)">
                  <img v-if="getMediaById(z.media_id)?.type === 'image' || getMediaById(z.media_id)?.type === 'ppt'" :src="getOriginalUrl(getMediaById(z.media_id))" class="w-full h-full object-cover" />
                  <video v-else-if="getMediaById(z.media_id)?.type === 'video'" :src="mediaApi.getUrl(getMediaById(z.media_id)?.file_path)" class="w-full h-full object-cover" muted preload="metadata"></video>
                  <div v-else class="text-xs text-slate-400 text-center px-2">{{ getMediaById(z.media_id)?.name }}</div>
                </template>
                <span v-else class="text-xs text-slate-400">区域{{ i + 1 }}</span>
              </div>
            </div>
          </div>

          <!-- 右栏: 素材库 -->
          <div class="w-80 border-l border-slate-100 flex flex-col shrink-0">
            <!-- 素材库标题 -->
            <div class="px-4 py-3 border-b border-slate-100 shrink-0">
              <div class="text-sm font-medium text-slate-700 mb-2">素材库</div>
              <div class="flex items-center gap-2">
                <div class="relative flex-1">
                  <Search :size="12" class="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input v-model="mediaSearch" class="w-full pl-7 pr-2 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500/20" placeholder="搜索素材...">
                </div>
                <select v-model="mediaTypeFilter" class="px-2 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none">
                  <option value="">全部</option>
                  <option value="image">图片</option>
                  <option value="video">视频</option>
                  <option value="ppt">PPT</option>
                </select>
              </div>
            </div>

            <!-- 素材列表 -->
            <div class="flex-1 overflow-y-auto">
              <div class="p-2 space-y-1">
                <div v-for="m in filteredMediaList" :key="m.id" @dblclick="selectMediaForZone(m.id)" @click="toggleMediaSelect(m.id)" @mouseenter="hoveredMediaId = m.id" @mouseleave="hoveredMediaId = null"
                  :class="['flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all', editingZoneIndex !== null && form.zones[editingZoneIndex]?.media_id === m.id ? 'bg-blue-100 border border-blue-300' : 'hover:bg-slate-100 border border-transparent']">
                  <div class="w-8 h-8 rounded bg-slate-100 overflow-hidden flex-shrink-0 flex items-center justify-center relative">
                    <img v-if="getThumbnailUrl(m)" :src="getThumbnailUrl(m)" class="w-full h-full object-cover" :alt="m.name">
                    <video v-else-if="m.type === 'video'" :src="mediaApi.getUrl(m.file_path)" class="w-full h-full object-cover" muted preload="metadata"></video>
                    <span v-else class="text-[10px] text-slate-400">PPT</span>
                    <div v-if="m.type === 'video' && !getThumbnailUrl(m)" class="absolute inset-0 bg-black/40 flex items-center justify-center">
                      <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-xs font-medium text-slate-700 truncate">{{ m.name }}</div>
                    <div class="text-[10px] text-slate-400">{{ m.type }} / {{ m.file_size ? (m.file_size / 1024 / 1024).toFixed(1) + 'MB' : '' }}</div>
                  </div>
                  <!-- 快捷操作按钮 -->
                  <template v-if="hoveredMediaId === m.id">
                    <button @click.stop="previewMedia = m" class="p-1 bg-slate-200 text-slate-600 rounded hover:bg-slate-300" title="预览"><Eye :size="12" /></button>
                    <button v-if="editingZoneIndex !== null" @click.stop="selectMediaForZone(m.id)" class="p-1 bg-blue-500 text-white rounded hover:bg-blue-600" title="绑定到当前区域">
                      <ChevronRight :size="12" />
                    </button>
                  </template>
                  <span v-if="editingZoneIndex !== null && form.zones[editingZoneIndex]?.media_id === m.id" class="text-[10px] text-blue-500 font-medium">已选</span>
                </div>
                <div v-if="!filteredMediaList.length" class="text-center text-xs text-slate-400 py-4">无匹配素材</div>
              </div>
            </div>

            <!-- 底部统计 -->
            <div class="px-4 py-2 border-t border-slate-100 text-[10px] text-slate-400 shrink-0">
              共 {{ filteredMediaList.length }} 个素材
              <span v-if="editingZoneIndex !== null && form.zones[editingZoneIndex]?.media_id"> / 当前绑定: {{ getMediaById(form.zones[editingZoneIndex].media_id)?.name || '-' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 素材预览弹窗 -->
    <div v-if="previewMedia" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" @click.self="previewMedia = null">
      <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800 text-sm">{{ previewMedia.name }}</h3>
          <button @click="previewMedia = null" class="p-1 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="16" /></button>
        </div>
        <div class="flex items-center justify-center bg-slate-900 p-4" style="min-height: 200px;">
          <img v-if="previewMedia.type === 'image'" :src="mediaApi.getUrl(previewMedia.file_path)" class="max-w-full max-h-[50vh] object-contain rounded">
          <video v-else-if="previewMedia.type === 'video'" :src="mediaApi.getUrl(previewMedia.file_path)" controls class="max-w-full max-h-[50vh] rounded"></video>
          <template v-else-if="previewMedia.type === 'ppt'">
            <div v-if="previewPptSlides.length" class="flex flex-col items-center gap-3 w-full">
              <img :src="mediaApi.getUrl(previewPptSlides[previewSlideIndex])" class="max-w-full max-h-[45vh] object-contain rounded">
              <div class="flex items-center gap-3">
                <button @click="previewSlideIndex = Math.max(0, previewSlideIndex - 1)" :disabled="previewSlideIndex === 0" class="px-3 py-1 bg-white/10 hover:bg-white/20 text-white rounded text-xs disabled:opacity-30">上一页</button>
                <span class="text-white/70 text-xs">{{ previewSlideIndex + 1 }} / {{ previewPptSlides.length }}</span>
                <button @click="previewSlideIndex = Math.min(previewPptSlides.length - 1, previewSlideIndex + 1)" :disabled="previewSlideIndex >= previewPptSlides.length - 1" class="px-3 py-1 bg-white/10 hover:bg-white/20 text-white rounded text-xs disabled:opacity-30">下一页</button>
              </div>
            </div>
            <img v-else :src="mediaApi.getUrl(previewMedia.thumbnail_path || previewMedia.file_path)" class="max-w-full max-h-[50vh] object-contain rounded">
          </template>
        </div>
        <div class="px-4 py-2 text-xs text-slate-400 flex items-center gap-3">
          <span>{{ previewMedia.type }}</span>
          <span v-if="previewMedia.width && previewMedia.height">{{ previewMedia.width }}x{{ previewMedia.height }}</span>
          <span>{{ previewMedia.file_size ? (previewMedia.file_size / 1024 / 1024).toFixed(1) + 'MB' : '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
