import http from './index'

export const mediaApi = {
  list(type) { return http.get('/media/list', { params: type ? { type } : {} }) },
  count() { return http.get('/media/count') },
  upload(files) {
    const fd = new FormData()
    Array.from(files).forEach(f => fd.append('file', f))
    return http.post('/media/upload', fd)
  },
  update(id, data) { return http.put(`/media/${id}`, data) },
  remove(id) { return http.delete(`/media/${id}`) },
  getSlides(id) { return http.get(`/media/${id}/slides`) },
  getUrl(filePath) { return `/uploads/${filePath}` }
}
