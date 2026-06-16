import http from './index'

export const layoutApi = {
  list() { return http.get('/layouts/list') },
  get(id) { return http.get(`/layouts/${id}`) },
  create(data) { return http.post('/layouts', data) },
  update(id, data) { return http.put(`/layouts/${id}`, data) },
  remove(id) { return http.delete(`/layouts/${id}`) }
}
