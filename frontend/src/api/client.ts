import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

// In dev, Vite proxies /api → http://localhost:8000 so use relative URL.
// In production build, use the full VITE_API_BASE_URL env var.
const isDev = import.meta.env.DEV
export const API_BASE = isDev ? '' : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
