import api from './client'
import type { Lecturer } from '../types'

export const lecturersApi = {
  list: async (params?: { department_id?: number }): Promise<Lecturer[]> =>
    (await api.get('/api/lecturers', { params })).data,
  get: async (id: number): Promise<Lecturer> => (await api.get(`/api/lecturers/${id}`)).data,
  create: async (data: {
    employee_id: string; full_name: string; department_id: number;
    username: string; email: string; password: string
  }): Promise<Lecturer> => (await api.post('/api/lecturers', data)).data,
  update: async (id: number, data: Partial<Lecturer>): Promise<Lecturer> =>
    (await api.patch(`/api/lecturers/${id}`, data)).data,
  deactivate: async (id: number): Promise<void> => api.delete(`/api/lecturers/${id}`),
}
