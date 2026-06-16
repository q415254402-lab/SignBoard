import http from './index'

export const powerScheduleApi = {
  list() { return http.get('/power-schedules') },
  create(data) { return http.post('/power-schedules', data) },
  update(id, data) { return http.put(`/power-schedules/${id}`, data) },
  patch(id, data) { return http.patch(`/power-schedules/${id}`, data) },
  remove(id) { return http.delete(`/power-schedules/${id}`) },
}
