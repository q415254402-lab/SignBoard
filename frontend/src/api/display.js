import http from './index'

export const displayApi = {
  list(params) { return http.get('/displays/list', { params }) },
  count() { return http.get('/displays/count') },
  restart(id) { return http.post('/displays/command', { command: 'restart', display_ids: [id] }) },
  command(id, command) { return http.post('/displays/command', { command, display_ids: [id] }) },
  screenshot(id) { return http.post('/displays/command', { command: 'screenshot', display_ids: [id] }) },
  getScreenshot(id) { return `/api/v1/displays/${id}/screenshot` },
  update(id, data) { return http.put(`/displays/${id}`, data) },
  remove(id) { return http.delete(`/displays/${id}`) },
  batchCommand(ids, command) { return http.post('/displays/command', { command, display_ids: ids }) },
  batchSetGroup(ids, groupId) { return http.put('/displays/batch/group', { display_ids: ids, group_id: groupId }) },
  batchSetLayout(ids, layoutId) { return http.put('/displays/batch/layout', { display_ids: ids, layout_id: layoutId }) },
}
