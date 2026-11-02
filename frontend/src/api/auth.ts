import api from './client'
import type { TokenResponse, User } from '../types'

export const authApi = {
  login: async (username: string, password: string, expectedRole?: string): Promise<TokenResponse> => {
    const payload: { username: string; password: string; expected_role?: string } = { username, password }
    if (expectedRole) {
      payload.expected_role = expectedRole
    }
    const res = await api.post<TokenResponse>('/api/auth/login', payload)
    return res.data
  },
  me: async (): Promise<User> => {
    const res = await api.get<User>('/api/auth/me')
    return res.data
  },
  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const res = await api.post<TokenResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    })
    return res.data
  },
}
