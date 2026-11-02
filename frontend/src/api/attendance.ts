import api from './client'
import type { AttendanceSession, AttendanceRecord, AttendanceStatus } from '../types'

export const attendanceApi = {
  listSessions: async (params?: {
    class_id?: number; subject_id?: number; status?: string;
    date_from?: string; date_to?: string; skip?: number; limit?: number
  }): Promise<AttendanceSession[]> => (await api.get('/api/attendance/sessions', { params })).data,

  getSession: async (id: number): Promise<AttendanceSession> =>
    (await api.get(`/api/attendance/sessions/${id}`)).data,

  createSession: async (data: {
    subject_id: number; class_id: number; attendance_date: string; source_type?: string
  }): Promise<AttendanceSession> => (await api.post('/api/attendance/sessions', data)).data,

  submitRecords: async (
    sessionId: number,
    records: { student_id: number; status: AttendanceStatus }[]
  ): Promise<AttendanceRecord[]> =>
    (await api.post(`/api/attendance/sessions/${sessionId}/records`, { records })).data,

  finalizeSession: async (sessionId: number): Promise<AttendanceSession> =>
    (await api.post(`/api/attendance/sessions/${sessionId}/finalize`, { confirm: true })).data,

  cancelSession: async (sessionId: number, reason: string): Promise<AttendanceSession> =>
    (await api.post(`/api/attendance/sessions/${sessionId}/cancel`, { reason })).data,

  correctRecord: async (
    sessionId: number,
    studentId: number,
    newStatus: AttendanceStatus,
    reason: string
  ): Promise<AttendanceRecord> =>
    (await api.post(`/api/attendance/sessions/${sessionId}/correct`, {
      student_id: studentId, new_status: newStatus, reason
    })).data,

  myAttendance: async (params?: { subject_id?: number }): Promise<AttendanceRecord[]> =>
    (await api.get('/api/attendance/my', { params })).data,
}
