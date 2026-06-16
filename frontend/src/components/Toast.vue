<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const toasts = ref([])
let id = 0

function addToast(message, type = 'info', duration = 3000) {
  const toast = { id: ++id, message, type }
  toasts.value.push(toast)
  if (duration > 0) {
    setTimeout(() => removeToast(toast.id), duration)
  }
}

function removeToast(toastId) {
  toasts.value = toasts.value.filter(t => t.id !== toastId)
}

function success(message, duration) { addToast(message, 'success', duration) }
function error(message, duration) { addToast(message, 'error', duration || 5000) }
function info(message, duration) { addToast(message, 'info', duration) }
function warning(message, duration) { addToast(message, 'warning', duration || 4000) }

defineExpose({ success, error, info, warning })
</script>

<template>
  <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'px-4 py-3 rounded-lg shadow-lg text-sm text-white pointer-events-auto cursor-pointer max-w-sm break-words',
          toast.type === 'success' && 'bg-green-500',
          toast.type === 'error' && 'bg-red-500',
          toast.type === 'warning' && 'bg-amber-500',
          toast.type === 'info' && 'bg-slate-700'
        ]"
        @click="removeToast(toast.id)"
      >
        {{ toast.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
