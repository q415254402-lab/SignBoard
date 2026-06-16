import http from './index'

export const scheduleApi = {
  list() { return http.get('/schedules/list') },
  count() { return http.get('/schedules/count') },
  create(data) { return http.post('/schedules', data) },
  update(id, data) { return http.put(`/schedules/${id}`, data) },
  patch(id, data) { return http.patch(`/schedules/${id}`, data) },
  remove(id) { return http.delete(`/schedules/${id}`) }
}