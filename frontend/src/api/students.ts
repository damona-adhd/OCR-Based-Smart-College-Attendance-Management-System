import api from './client'
import type { Student } from '../types'

export const studentsApi = {
  list: async (params?: {
    class_id?: number; department_id?: number; is_active?: boolean; skip?: number; limit?: number
  }): Promise<Student[]> => (await api.get('/api/students', { params })).data,

  get: async (id: number): Promise<Student> => (await api.get(`/api/students/${id}`)).data,

  create: async (data: {
    usn: string; full_name: string; department_id: number; academic_year: string;
    semester: number; class_id: number; username?: string; email?: string; password?: string
  }): Promise<Student> => (await api.post('/api/students', data)).data,

  update: async (id: number, data: Partial<Student>): Promise<Student> =>
    (await api.patch(`/api/students/${id}`, data)).data,

  deactivate: async (id: number): Promise<void> => api.delete(`/api/students/${id}`),

  // Quick-add student for teachers & admins
  quickAdd: async (data: { full_name: string; usn: string; class_id: number }): Promise<Student> =>
    (await api.post('/api/students/quick-add', data)).data,

  // Roster for a class — accessible to lecturers (no admin required)
  classRoster: async (classId: number): Promise<Student[]> =>
    (await api.get(`/api/students/roster/${classId}`)).data,
}
