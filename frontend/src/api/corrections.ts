import api from './client'

export interface CorrectionHistoryItem {
  id: number
  previous_status: string
  new_status: string
  reason: string
  actor_username: string
  created_at: string
}

export interface StudentCorrectionRequestItem {
  id: number
  student_id: number
  student_name: string
  student_usn: string
  attendance_record_id: number
  current_status: string
  requested_status: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  subject_name: string
  date: string
  created_at: string
}

export const correctionsApi = {
  correctRecord: async (recordId: number, data: { new_status: 'present' | 'absent'; reason: string }) => {
    const res = await api.post(`/api/corrections/record/${recordId}`, data)
    return res.data
  },

  getHistory: async (recordId: number): Promise<CorrectionHistoryItem[]> => {
    const res = await api.get<CorrectionHistoryItem[]>(`/api/corrections/history/${recordId}`)
    return res.data
  },

  submitRequest: async (data: {
    attendance_record_id: number
    requested_status: 'present' | 'absent'
    reason: string
  }) => {
    const res = await api.post('/api/corrections/request', data)
    return res.data
  },

  listRequests: async (statusFilter?: string): Promise<StudentCorrectionRequestItem[]> => {
    const res = await api.get<StudentCorrectionRequestItem[]>('/api/corrections/requests', {
      params: statusFilter ? { status_filter: statusFilter } : undefined,
    })
    return res.data
  },

  reviewRequest: async (requestId: number, data: { status: 'approved' | 'rejected'; review_note?: string }) => {
    const res = await api.post(`/api/corrections/requests/${requestId}/review`, data)
    return res.data
  },
}
