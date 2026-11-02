import api from './client'

export interface RosterPreviewRow {
  usn: string
  full_name: string
  status: 'new' | 'existing' | 'invalid'
  notes?: string
}

export interface RosterPreviewResponse {
  filename: string
  page_count: number
  kind: string
  has_text_layer: boolean
  total_extracted: number
  new_count: number
  existing_count: number
  invalid_count: number
  rows: RosterPreviewRow[]
  note: string
}

export interface RosterImportResponse {
  imported_count: number
  skipped_count: number
  class_id: number
  message: string
}

export const rosterApi = {
  preview: async (file: File, classId?: number): Promise<RosterPreviewResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (classId) {
      formData.append('class_id', String(classId))
    }
    const res = await api.post<RosterPreviewResponse>('/api/roster/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  commitImport: async (classId: number, students: { usn: string; full_name: string }[]): Promise<RosterImportResponse> => {
    const res = await api.post<RosterImportResponse>('/api/roster/import', {
      class_id: classId,
      students,
    })
    return res.data
  },
}
