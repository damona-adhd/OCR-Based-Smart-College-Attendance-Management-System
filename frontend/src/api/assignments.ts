import api from './client'
import type { TeachingAssignment } from '../types'

export const assignmentsApi = {
  list: async (params?: { lecturer_id?: number; class_id?: number }): Promise<TeachingAssignment[]> =>
    (await api.get('/api/assignments', { params })).data,
  create: async (data: { lecturer_id: number; subject_id: number; class_id: number }): Promise<TeachingAssignment> =>
    (await api.post('/api/assignments', data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/api/assignments/${id}`),
}
