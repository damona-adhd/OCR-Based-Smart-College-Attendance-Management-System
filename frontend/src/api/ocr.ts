import api from './client'
import type { OCRResult } from '../types'

export const ocrApi = {
  uploadImage: async (sessionId: number, file: File): Promise<{
    source_file_id: number; session_id: number; original_filename: string;
    file_size: number; processing_status: string
  }> => {
    const form = new FormData()
    form.append('file', file)
    const res = await api.post(`/api/files/upload/${sessionId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  processOCR: async (sessionId: number, provider?: string): Promise<OCRResult> => {
    const url = provider ? `/api/ocr/process/${sessionId}?provider=${encodeURIComponent(provider)}` : `/api/ocr/process/${sessionId}`
    return (await api.post(url)).data
  },

  confirmOCR: async (
    sessionId: number,
    corrections: { row_index: number; student_id: number; attendance_status: string }[]
  ): Promise<{ message: string; session_id: number; record_count: number }> =>
    (await api.post(`/api/ocr/confirm/${sessionId}`, {
      session_id: sessionId,
      corrections,
    })).data,

  getImageUrl: (sessionId: number): string => {
    const base = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
    return `${base}/api/files/image/${sessionId}`
  },
}
