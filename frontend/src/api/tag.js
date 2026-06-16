import http from './index'

export const tagApi = {
  list() { return http.get('/tags') },
  create(data) { return http.post('/tags', data) },
  update(id, data) { return http.put(`/tags/${id}`, data) },
  remove(id) { return http.delete(`/tags/${id}`) },
  getMediaTags(mediaId) { return http.get(`/tags/media/${mediaId}`) },
  setMediaTags(mediaId, tagIds) { return http.put(`/tags/media/${mediaId}`, { tag_ids: tagIds }) },
}
