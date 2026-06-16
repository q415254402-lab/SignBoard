import http from './index'

export const deviceGroupApi = {
  list() { return http.get('/device-groups') },
  create(data) { return http.post('/device-groups', data) },
  update(id, data) { return http.put(`/device-groups/${id}`, data) },
  remove(id) { return http.delete(`/device-groups/${id}`) },
}
