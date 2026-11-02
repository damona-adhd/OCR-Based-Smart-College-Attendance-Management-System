import api from './client'
import type { Department } from '../types'

export const departmentsApi = {
  list: async (): Promise<Department[]> => (await api.get('/api/departments')).data,
  get: async (id: number): Promise<Department> => (await api.get(`/api/departments/${id}`)).data,
  create: async (data: { name: string; code: string }): Promise<Department> =>
    (await api.post('/api/departments', data)).data,
  update: async (id: number, data: Partial<Department>): Promise<Department> =>
    (await api.patch(`/api/departments/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/api/departments/${id}`),
}
