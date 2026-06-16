<script setup>
import { ref, onMounted, inject, computed } from 'vue'
import { useRouter } from 'vue-router'
import { mediaApi } from '../api/media'
import { tagApi } from '../api/tag'
import { Upload, Trash2, Eye, Image, Video, FileText, X, LayoutGrid, List, Tags, Check } from 'lucide-vue-next'

const router = useRouter()
const toast = inject('toast')
const media = ref([])
const tags = ref([])
const filter = ref('')
const tagFilter = ref(null)
const preview = ref(null)
const pptSlides = ref([])
const slideIndex = ref(0)
const loading = ref(false)
const editingName = ref(null)
const editNameValue = ref('')
const viewMode = ref(localStorage.getItem('media_viewMode') || 'card')
const mediaTags = ref({})

// 批量选择
const selectedMediaIds = ref(new Set())
const showBatchTagMenu = ref(false)
// 单个素材的标签下拉
const activeTagDropdown = ref(null)

function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem('media_viewMode', mode)
}

const typeIcons = { image: Image, video: Video, ppt: FileText }

async function load() {
  loading.value = true
  try {
    const [mediaData, tagData] = await Promise.all([mediaApi.list(filter.value || undefined), tagApi.list()])
    media.value = mediaData
    tags.value = tagData
    await loadAllMediaTags()
  } catch (e) { toast.error(e.message) } finally { loading.value = false }
}

async function loadAllMediaTags() {
  const map = {}
  for (const m of media.value) {
    try { const t = await tagApi.getMediaTags(m.id); map[m.id] = t.map(tg => tg.id) } catch { map[m.id] = [] }
  }
  mediaTags.value = map
}

const filteredMedia = computed(() => {
  let list = media.value
  if (tagFilter.value === -1) list = list.filter(m => !mediaTags.value[m.id]?.length)
  else if (tagFilter.value > 0) list = list.filter(m => mediaTags.value[m.id]?.includes(tagFilter.value))
  return list
})

const isAllSelected = computed(() => filteredMedia.value.length > 0 && filteredMedia.value.every(m => selectedMediaIds.value.has(m.id)))
const selectedCount = computed(() => selectedMediaIds.value.size)

function toggleSelect(id) {
  const s = new Set(selectedMediaIds.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  selectedMediaIds.value = s
}
function toggleAll() {
  if (isAllSelected.value) selectedMediaIds.value = new Set()
  else selectedMediaIds.value = new Set(filteredMedia.value.map(m => m.id))
}
function clearSelection() { selectedMediaIds.value = new Set(); showBatchTagMenu.value = false }

async function upload(e) {
  const files = e.target.files
  if (!files.length) return
  try { await mediaApi.upload(files); await load(); e.target.value = '' } catch (err) { toast.error(err.message) }
}

async function remove(item) {
  if (!confirm(`确定删除「${item.name}」？`)) return
  try { await mediaApi.remove(item.id); await load() } catch (e) { toast.error(e.message) }
}

async function openPreview(item) {
  preview.value = item; pptSlides.value = []; slideIndex.value = 0
  if (item.type === 'ppt') { try { const res = await mediaApi.getSlides(item.id); pptSlides.value = res.slides || [] } catch {} }
}
function closePreview() { preview.value = null; pptSlides.value = []; slideIndex.value = 0 }

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

function startRename(item) { editingName.value = item.id; editNameValue.value = item.name }
async function finishRename(item) {
  const newName = editNameValue.value.trim()
  if (newName && newName !== item.name) { try { await mediaApi.update(item.id, { name: newName }); item.name = newName } catch (e) { toast.error(e.message) } }
  editingName.value = null
}

// --- 标签操作 ---
function toggleTagDropdown(mediaId) {
  activeTagDropdown.value = activeTagDropdown.value === mediaId ? null : mediaId
}

async function toggleMediaTag(mediaId, tagId) {
  const current = new Set(mediaTags.value[mediaId] || [])
  if (current.has(tagId)) current.delete(tagId); else current.add(tagId)
  try {
    await tagApi.setMediaTags(mediaId, [...current])
    mediaTags.value[mediaId] = [...current]
    // 刷新标签数量
    tags.value = await tagApi.list()
  } catch (e) { toast.error(e.message) }
}

async function batchAssignTag(tagId) {
  const ids = [...selectedMediaIds.value]
  if (!ids.length) return
  try {
    for (const id of ids) {
      const current = new Set(mediaTags.value[id] || [])
      current.add(tagId)
      await tagApi.setMediaTags(id, [...current])
      mediaTags.value[id] = [...current]
    }
    tags.value = await tagApi.list()
    toast.success(`已将 ${ids.length} 个素材添加到标签`)
    showBatchTagMenu.value = false
    clearSelection()
  } catch (e) { toast.error(e.message) }
}

async function batchRemoveTag(tagId) {
  const ids = [...selectedMediaIds.value]
  if (!ids.length) return
  try {
    for (const id of ids) {
      const current = new Set(mediaTags.value[id] || [])
      current.delete(tagId)
      await tagApi.setMediaTags(id, [...current])
      mediaTags.value[id] = [...current]
    }
    tags.value = await tagApi.list()
    toast.success(`已将 ${ids.length} 个素材移除标签`)
    showBatchTagMenu.value = false
    clearSelection()
  } catch (e) { toast.error(e.message) }
}

function getTagById(id) { return tags.value.find(t => t.id === id) }

onMounted(load)
</script>

<template>
  <div>
    <!-- 顶栏 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <select v-model="filter" @change="load()" class="px-3 py-2 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20">
          <option value="">全部类型</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
          <option value="ppt">PPT</option>
        </select>
        <div v-if="media.length > 0" class="flex items-center border border-slate-200 rounded-lg overflow-hidden">
          <button @click="setViewMode('card')" :class="['p-1.5 transition-all', viewMode === 'card' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><LayoutGrid :size="16" /></button>
          <button @click="setViewMode('list')" :class="['p-1.5 transition-all', viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-slate-400 hover:text-slate-600']"><List :size="16" /></button>
        </div>
      </div>
      <label class="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-all cursor-pointer shadow-lg shadow-blue-500/25 active:scale-[0.98]">
        <Upload :size="18" /> 上传素材
        <input type="file" multiple class="hidden" @change="upload" accept="image/*,video/*,.pptx">
      </label>
    </div>

    <!-- 标签筛选栏 -->
    <div v-if="tags.length > 0" class="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
      <button @click="tagFilter = null" :class="['px-3 py-1 text-xs rounded-lg border whitespace-nowrap transition-all', tagFilter === null ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        全部 ({{ media.length }})
      </button>
      <button v-for="t in tags" :key="t.id" @click="tagFilter = t.id"
        :class="['flex items-center gap-1.5 px-3 py-1 text-xs rounded-lg border whitespace-nowrap transition-all', tagFilter === t.id ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        <span class="w-2 h-2 rounded-full" :style="{ background: t.color }"></span>{{ t.name }} ({{ t.count }})
      </button>
      <button v-if="tagFilter === null" @click="tagFilter = -1" :class="['px-3 py-1 text-xs rounded-lg border whitespace-nowrap transition-all', tagFilter === -1 ? 'border-blue-400 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-500 hover:border-slate-300']">
        未打标签
      </button>
      <button @click="router.push('/settings?tab=tags')" class="px-3 py-1 text-xs text-blue-500 hover:text-blue-700 border border-dashed border-blue-300 rounded-lg whitespace-nowrap transition-all">
        + 管理标签
      </button>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedCount > 0" class="flex items-center gap-3 mb-4 p-3 bg-blue-50 border border-blue-200 rounded-xl">
      <button @click="toggleAll" class="text-sm text-blue-600">{{ isAllSelected ? '取消全选' : '全选' }}</button>
      <span class="text-sm text-blue-600 font-medium">已选 {{ selectedCount }} 个</span>
      <div class="flex-1"></div>
      <!-- 批量打标签 -->
      <div class="relative">
        <button @click="showBatchTagMenu = !showBatchTagMenu" class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-1">
          <Tags :size="14" /> 打标签
        </button>
        <div v-if="showBatchTagMenu" class="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-30 min-w-[140px]">
          <div class="px-3 py-1 text-[10px] text-slate-400 font-medium border-b border-slate-100">添加标签</div>
          <div v-for="t in tags" :key="'add-'+t.id" @click="batchAssignTag(t.id)" class="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer">
            <span class="w-2 h-2 rounded-full" :style="{ background: t.color }"></span>{{ t.name }}
          </div>
          <div class="px-3 py-1 text-[10px] text-slate-400 font-medium border-t border-b border-slate-100 mt-1">移除标签</div>
          <div v-for="t in tags" :key="'rm-'+t.id" @click="batchRemoveTag(t.id)" class="flex items-center gap-2 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 cursor-pointer">
            <span class="w-2 h-2 rounded-full" :style="{ background: t.color }"></span>{{ t.name }}
          </div>
          <div v-if="!tags.length" class="px-3 py-1.5 text-xs text-slate-400">无标签</div>
        </div>
      </div>
      <button @click="clearSelection()" class="p-1 text-slate-400 hover:text-slate-600"><X :size="16" /></button>
    </div>

    <div v-if="!loading && filteredMedia.length === 0" class="bg-white rounded-2xl p-12 text-center border border-slate-100">
      <Image :size="48" class="mx-auto mb-4 text-slate-300" />
      <p class="text-slate-500 font-medium">{{ media.length === 0 ? '还没有素材' : '无匹配素材' }}</p>
    </div>
    <div v-if="loading" class="text-center py-12 text-slate-400">加载中...</div>

    <!-- Card view -->
    <div v-if="viewMode === 'card' && !loading && filteredMedia.length > 0" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
      <div v-for="item in filteredMedia" :key="item.id" class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden group hover:shadow-md transition-all">
        <div class="relative aspect-video bg-slate-100 flex items-center justify-center overflow-hidden">
          <img v-if="item.type === 'image' || item.type === 'ppt'" :src="mediaApi.getUrl(item.thumbnail_path || item.file_path)" class="w-full h-full object-contain" :alt="item.name">
          <video v-else-if="item.type === 'video'" :src="mediaApi.getUrl(item.file_path)" class="w-full h-full object-contain" muted></video>
          <component v-else :is="typeIcons[item.type] || Image" :size="36" class="text-slate-300" />
          <!-- 复选框 -->
          <button @click.stop="toggleSelect(item.id)" class="absolute bottom-2 left-2 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all"
            :class="selectedMediaIds.has(item.id) ? 'bg-blue-500 border-blue-500 text-white' : 'bg-white/80 border-slate-300 text-transparent hover:border-blue-400'">
            <Check :size="14" />
          </button>
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
            <button @click="openPreview(item)" class="p-2 bg-white/90 rounded-xl text-slate-700 hover:bg-white"><Eye :size="18" /></button>
            <button @click="remove(item)" class="p-2 bg-white/90 rounded-xl text-red-500 hover:bg-white"><Trash2 :size="18" /></button>
          </div>
        </div>
        <div class="p-3">
          <div v-if="editingName === item.id" class="flex gap-1">
            <input v-model="editNameValue" @keyup.enter="finishRename(item)" @keyup.escape="editingName = null" @blur="finishRename(item)" class="flex-1 px-2 py-1 text-sm border border-blue-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" autofocus>
          </div>
          <div v-else @dblclick="startRename(item)" class="text-sm font-medium text-slate-700 truncate cursor-pointer hover:text-blue-600" :title="'双击修改名称'">{{ item.name }}</div>
          <div class="flex items-center gap-1.5 mt-1">
            <span class="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-md">{{ item.type }}</span>
            <span v-if="item.width && item.height" class="text-xs text-slate-400">{{ item.width }}x{{ item.height }}</span>
            <span class="text-xs text-slate-400">{{ item.duration_seconds ? item.duration_seconds + 's' : formatSize(item.file_size) }}</span>
          </div>
          <!-- 标签：点击弹出下拉选择 -->
          <div class="mt-1.5 relative">
            <div @click.stop="toggleTagDropdown(item.id)" class="flex flex-wrap gap-1 cursor-pointer min-h-[20px] hover:bg-slate-50 rounded px-1 py-0.5 transition-colors">
              <span v-for="tagId in (mediaTags[item.id] || [])" :key="tagId" class="text-[10px] px-1.5 py-0.5 rounded text-white" :style="{ background: getTagById(tagId)?.color || '#94a3b8' }">
                {{ getTagById(tagId)?.name }}
              </span>
              <span v-if="!(mediaTags[item.id] || []).length" class="text-[10px] text-slate-300">+标签</span>
            </div>
            <!-- 标签下拉 -->
              <div v-if="activeTagDropdown === item.id" class="absolute left-0 top-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-30 min-w-[130px]" @click.stop>
              <div v-for="t in tags" :key="t.id" @click="toggleMediaTag(item.id, t.id)"
                class="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer">
                <span class="w-2 h-2 rounded-full" :style="{ background: t.color }"></span>
                {{ t.name }}
                <span v-if="(mediaTags[item.id] || []).includes(t.id)" class="ml-auto text-blue-500">✓</span>
              </div>
              <div v-if="!tags.length" class="px-3 py-1.5 text-xs text-slate-400">请先创建标签</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- List view -->
    <div v-if="viewMode === 'list' && !loading" class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <table class="w-full">
        <thead><tr class="border-b border-slate-100 bg-slate-50">
          <th class="w-10 px-4 py-2"><button @click="toggleAll" :class="['w-5 h-5 rounded border-2 flex items-center justify-center', isAllSelected ? 'bg-blue-500 border-blue-500 text-white' : 'border-slate-300 text-transparent hover:border-blue-400']"><Check :size="12" /></button></th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">名称</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">类型</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">标签</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">分辨率</th>
          <th class="text-left px-4 py-2 text-xs font-medium text-slate-500">大小</th>
          <th class="text-right px-4 py-2 text-xs font-medium text-slate-500">操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="item in filteredMedia" :key="item.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="px-4 py-2"><button @click="toggleSelect(item.id)" :class="['w-5 h-5 rounded border-2 flex items-center justify-center', selectedMediaIds.has(item.id) ? 'bg-blue-500 border-blue-500 text-white' : 'border-slate-300 text-transparent hover:border-blue-400']"><Check :size="12" /></button></td>
            <td class="px-4 py-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-slate-100 overflow-hidden flex-shrink-0 flex items-center justify-center">
                  <img v-if="item.thumbnail_path" :src="mediaApi.getUrl(item.thumbnail_path)" class="w-full h-full object-cover">
                  <img v-else-if="item.type === 'image' || item.type === 'ppt'" :src="mediaApi.getUrl(item.thumbnail_path || item.file_path)" class="w-full h-full object-cover">
                  <video v-else-if="item.type === 'video'" :src="mediaApi.getUrl(item.file_path)" class="w-full h-full object-cover" muted preload="metadata"></video>
                  <FileText v-else :size="16" class="text-slate-400" />
                </div>
                <div v-if="editingName === item.id"><input v-model="editNameValue" @keyup.enter="finishRename(item)" @keyup.escape="editingName = null" @blur="finishRename(item)" class="px-2 py-1 text-sm border border-blue-300 rounded-lg focus:outline-none w-40" autofocus></div>
                <span v-else @dblclick="startRename(item)" class="font-medium text-slate-800 text-sm cursor-pointer hover:text-blue-600 truncate max-w-[200px]">{{ item.name }}</span>
              </div>
            </td>
            <td class="px-4 py-2"><span class="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-500">{{ item.type }}</span></td>
            <td class="px-4 py-2 relative">
              <div @click.stop="toggleTagDropdown(item.id)" class="flex flex-wrap gap-1 cursor-pointer min-h-[20px]">
                <span v-for="tagId in (mediaTags[item.id] || [])" :key="tagId" class="text-[10px] px-1.5 py-0.5 rounded text-white" :style="{ background: getTagById(tagId)?.color || '#94a3b8' }">{{ getTagById(tagId)?.name }}</span>
                <span v-if="!(mediaTags[item.id] || []).length" class="text-[10px] text-slate-300">+标签</span>
              </div>
              <div v-if="activeTagDropdown === item.id" class="absolute left-0 top-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-20 min-w-[130px]" @click.stop>
                <div v-for="t in tags" :key="t.id" @click="toggleMediaTag(item.id, t.id)" class="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer">
                  <span class="w-2 h-2 rounded-full" :style="{ background: t.color }"></span>{{ t.name }}
                  <span v-if="(mediaTags[item.id] || []).includes(t.id)" class="ml-auto text-blue-500">✓</span>
                </div>
                <div v-if="!tags.length" class="px-3 py-1.5 text-xs text-slate-400">请先创建标签</div>
              </div>
            </td>
            <td class="px-4 py-2 text-xs text-slate-500">{{ item.width && item.height ? item.width + 'x' + item.height : '-' }}</td>
            <td class="px-4 py-2 text-sm text-slate-500">{{ formatSize(item.file_size) }}</td>
            <td class="px-4 py-2 text-right">
              <div class="flex items-center justify-end gap-1">
                <button @click="openPreview(item)" class="p-1.5 text-slate-400 hover:text-blue-500 rounded-lg hover:bg-blue-50"><Eye :size="14" /></button>
                <button @click="remove(item)" class="p-1.5 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50"><Trash2 :size="14" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredMedia.length"><td colspan="6" class="px-6 py-8 text-center text-sm text-slate-400">暂无素材</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Preview modal -->
    <div v-if="preview" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-8" @click.self="closePreview">
      <div class="bg-white rounded-2xl max-w-4xl max-h-[85vh] w-full overflow-hidden shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 class="font-semibold text-slate-800">{{ preview.name }}</h3>
          <button @click="closePreview" class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"><X :size="20" /></button>
        </div>
        <div class="p-6 flex items-center justify-center bg-slate-900 min-h-[300px]">
          <img v-if="preview.type === 'image'" :src="mediaApi.getUrl(preview.file_path)" class="max-w-full max-h-[60vh] object-contain rounded-lg">
          <template v-else-if="preview.type === 'ppt'">
            <div v-if="pptSlides.length" class="flex flex-col items-center gap-4 w-full">
              <img :src="mediaApi.getUrl(pptSlides[slideIndex])" class="max-w-full max-h-[55vh] object-contain rounded-lg">
              <div class="flex items-center gap-3">
                <button @click="slideIndex = Math.max(0, slideIndex - 1)" :disabled="slideIndex === 0" class="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg disabled:opacity-30">上一页</button>
                <span class="text-white/70 text-sm">{{ slideIndex + 1 }} / {{ pptSlides.length }}</span>
                <button @click="slideIndex = Math.min(pptSlides.length - 1, slideIndex + 1)" :disabled="slideIndex >= pptSlides.length - 1" class="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg disabled:opacity-30">下一页</button>
              </div>
            </div>
            <img v-else :src="mediaApi.getUrl(preview.thumbnail_path || preview.file_path)" class="max-w-full max-h-[60vh] object-contain rounded-lg">
          </template>
          <video v-else-if="preview.type === 'video'" :src="mediaApi.getUrl(preview.file_path)" controls class="max-w-full max-h-[60vh] rounded-lg"></video>
        </div>
      </div>
    </div>

    <!-- 点击空白关闭标签下拉 -->
    <div v-if="activeTagDropdown" class="fixed inset-0 z-10" @click="activeTagDropdown = null"></div>
  </div>
</template>
