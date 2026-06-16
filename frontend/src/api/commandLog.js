import http from './index'

export const commandLogApi = {
  list(params) { return http.get('/command-logs', { params }) },
}
