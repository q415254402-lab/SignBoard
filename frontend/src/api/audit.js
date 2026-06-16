import http from './index'

export const auditApi = {
  list(params) { return http.get('/audit/list', { params }) },
}
