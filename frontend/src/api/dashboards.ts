import api from './client'

export interface AdminDashboardData {
  summary: {
    total_students: number
    total_teachers: number
    total_classes: number
    total_subjects: number
    total_sessions: number
    finalized_sessions: number
    draft_sessions: number
    overall_percentage: number
    sessions_today: number
    today_present: number
    today_absent: number
    today_percentage: number
  }
  trends: {
    date: string
    present: number
    absent: number
    percentage: number
  }[]
  present_absent: {
    name: string
    value: number
  }[]
  class_wise: {
    class_id: number
    class_name: string
    present: number
    absent: number
    percentage: number
  }[]
  subject_wise: {
    subject_id: number
    subject_code: string
    subject_name: string
    present: number
    absent: number
    percentage: number
  }[]
  recent_activity: {
    id: number
    date: string
    period: number
    status: string
    subject_name: string
    subject_code: string
    class_name: string
    teacher_name: string
  }[]
}

export interface TeacherDashboardData {
  teacher: {
    id: number
    name: string
    employee_id: string
  }
  summary: {
    assigned_subjects: number
    assigned_classes: number
    total_students: number
    total_sessions: number
    finalized_sessions: number
    draft_sessions: number
    average_attendance: number
  }
  assignments: {
    id: number
    class_id: number
    class_name: string
    subject_id: number
    subject_name: string
    subject_code: string
    semester: number
  }[]
  recent_sessions: {
    id: number
    date: string
    period: number
    status: string
    source_type: string
    subject_name: string
    subject_code: string
    class_name: string
  }[]
  needs_review: {
    id: number
    date: string
    period: number
    status: string
    source_type: string
    subject_name: string
    subject_code: string
    class_name: string
  }[]
}

export interface StudentDashboardData {
  student: {
    id: number
    usn: string
    full_name: string
    class_name: string
    semester: number
    academic_year: string
  }
  summary: {
    overall_percentage: number
    total_conducted: number
    total_attended: number
    total_missed: number
    min_threshold: number
    has_shortage: boolean
  }
  subjects: {
    subject_id: number
    subject_name: string
    subject_code: string
    conducted: number
    attended: number
    missed: number
    percentage: number
    is_shortage: boolean
  }[]
  recent_history: {
    record_id: number
    session_id: number
    date: string
    period: number
    subject_name: string
    subject_code: string
    status: string
    is_corrected: boolean
  }[]
}

export const dashboardsApi = {
  getAdmin: async (): Promise<AdminDashboardData> => {
    const res = await api.get<AdminDashboardData>('/api/dashboards/admin')
    return res.data
  },
  getTeacher: async (): Promise<TeacherDashboardData> => {
    const res = await api.get<TeacherDashboardData>('/api/dashboards/teacher')
    return res.data
  },
  getStudent: async (): Promise<StudentDashboardData> => {
    const res = await api.get<StudentDashboardData>('/api/dashboards/student')
    return res.data
  },
}
