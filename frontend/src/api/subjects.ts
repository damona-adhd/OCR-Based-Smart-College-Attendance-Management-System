import api from './client'
import type { Subject } from '../types'

export const subjectsApi = {
  list: async (params?: { department_id?: number; semester?: number }): Promise<Subject[]> =>
    (await api.get('/api/subjects', { params })).data,
  get: async (id: number): Promise<Subject> => (await api.get(`/api/subjects/${id}`)).data,
  create: async (data: Omit<Subject, 'id' | 'department'>): Promise<Subject> =>
    (await api.post('/api/subjects', data)).data,
  quickAdd: async (data: {
    subject_name: string
    subject_code: string
    department_id?: number
    semester?: number
    class_id?: number
  }): Promise<Subject> => (await api.post('/api/subjects/quick-add', data)).data,
  update: async (id: number, data: Partial<Subject>): Promise<Subject> =>
    (await api.patch(`/api/subjects/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/api/subjects/${id}`),
}
