import http from './index'

export const authApi = {
  login(username, password) {
    return http.post('/auth/login', { username, password })
  },
  logout() {
    return http.post('/auth/logout')
  },
  changePassword(oldPassword, newPassword) {
    return http.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
  },
  me() {
    return http.get('/auth/me')
  },
  // User management
  listUsers() { return http.get('/auth/users') },
  createUser(data) { return http.post('/auth/users', data) },
  updateUser(id, data) { return http.put(`/auth/users/${id}`, data) },
  deleteUser(id) { return http.delete(`/auth/users/${id}`) },
  getRoles() { return http.get('/auth/roles') },
}
