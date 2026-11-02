import api from './client'
import type { Class } from '../types'

export const classesApi = {
  list: async (params?: { department_id?: number }): Promise<Class[]> =>
    (await api.get('/api/classes', { params })).data,
  get: async (id: number): Promise<Class> => (await api.get(`/api/classes/${id}`)).data,
  create: async (data: Omit<Class, 'id' | 'department'>): Promise<Class> =>
    (await api.post('/api/classes', data)).data,
  update: async (id: number, data: Partial<Class>): Promise<Class> =>
    (await api.patch(`/api/classes/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/api/classes/${id}`),
}
