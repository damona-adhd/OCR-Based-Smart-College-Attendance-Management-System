import api from './client'
import type { StudentAttendanceReport, ClassAttendanceReport, DailyRow, AuditEvent, AppSetting } from '../types'

export const reportsApi = {
  studentReport: async (studentId: number): Promise<StudentAttendanceReport> =>
    (await api.get(`/api/reports/student/${studentId}`)).data,

  myReport: async (): Promise<StudentAttendanceReport> =>
    (await api.get('/api/reports/my')).data,

  classReport: async (params: {
    class_id: number; subject_id: number; date_from?: string; date_to?: string
  }): Promise<ClassAttendanceReport> => (await api.get('/api/reports/class', { params })).data,

  classCSVUrl: (params: {
    class_id: number; subject_id: number; date_from?: string; date_to?: string
  }): string => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v && q.set(k, String(v)))
    const base = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
    return `${base}/api/reports/class/csv?${q}`
  },

  daily: async (params?: {
    class_id?: number; date_from?: string; date_to?: string
  }): Promise<DailyRow[]> => (await api.get('/api/reports/daily', { params })).data,

  auditLogs: async (params?: {
    skip?: number; limit?: number; action?: string
  }): Promise<AuditEvent[]> => (await api.get('/api/reports/audit', { params })).data,

  getSettings: async (): Promise<AppSetting[]> => (await api.get('/api/settings')).data,

  updateSetting: async (key: string, value: string): Promise<AppSetting> =>
    (await api.put(`/api/settings/${key}`, null, { params: { value } })).data,
}
