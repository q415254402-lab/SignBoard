import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const http = axios.create({ 
  baseURL: '/api/v1',
  withCredentials: true  // 确保 Cookie 跨域发送
})

http.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    const msg = err.response?.data?.detail
    return Promise.reject(new Error(
      Array.isArray(msg) ? msg.map(e => e.msg).join('; ') : (msg || '请求失败')
    ))
  }
)

export default http
