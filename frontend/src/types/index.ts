// ---- Auth ----
export type UserRole = 'admin' | 'lecturer' | 'student'

export interface User {
  id: number
  username: string
  email: string
  role: UserRole
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  role: UserRole
  user_id: number
  username: string
}

// ---- Department ----
export interface Department {
  id: number
  name: string
  code: string
}

// ---- Class ----
export interface Class {
  id: number
  name: string
  academic_year: string
  semester: number
  section?: string
  course?: string
  department_id: number
  department?: Department
}

// ---- Subject ----
export interface Subject {
  id: number
  subject_code: string
  subject_name: string
  semester: number
  department_id: number
  department?: Department
}

// ---- Student ----
export interface Student {
  id: number
  usn: string
  full_name: string
  department_id: number
  academic_year: string
  semester: number
  class_id: number
  is_active: boolean
  user_id?: number
  username?: string
  email?: string
}

// ---- Lecturer ----
export interface Lecturer {
  id: number
  employee_id: string
  full_name: string
  department_id: number
  is_active: boolean
  user_id: number
  username?: string
  email?: string
}

// ---- Teaching Assignment ----
export interface TeachingAssignment {
  id: number
  lecturer_id: number
  subject_id: number
  class_id: number
  lecturer?: Lecturer
  subject?: Subject
  class_?: Class
}

// ---- Attendance Session ----
export type SessionStatus = 'draft' | 'finalized' | 'cancelled'
export type SourceType = 'manual' | 'ocr'
export type AttendanceStatus = 'present' | 'absent'

export interface AttendanceSession {
  id: number
  subject_id: number
  class_id: number
  lecturer_id: number
  attendance_date: string
  status: SessionStatus
  source_type: SourceType
  source_file_id?: number
  finalized_at?: string
  created_at: string
  updated_at: string
  records?: AttendanceRecord[]
  subject_name?: string
  class_name?: string
  lecturer_name?: string
}

export interface AttendanceRecord {
  id: number
  attendance_session_id: number
  student_id: number
  status: AttendanceStatus
  source_type: SourceType
  student_usn?: string
  student_name?: string
}

// ---- OCR & Document Extraction ----
export type MatchStatus = 'matched' | 'unmatched' | 'uncertain' | 'ambiguous' | 'duplicate' | 'missing'

export interface OCRRow {
  page_number?: number
  row_index: number
  student_name?: string
  usn?: string
  raw_attendance_mark?: string
  attendance_status?: 'present' | 'absent' | 'unknown'
  confidence: number
  match_status: MatchStatus
  review_required?: boolean
  review_reason?: string
  matched_student_id?: number
  matched_student_name?: string
  matched_student_usn?: string
  extracted_usn?: string
  extracted_name?: string
  proposed_status?: string
  needs_review: boolean
  corrected_student_id?: number
  corrected_status?: string
}

export interface OCRResult {
  source_file_id: number
  session_id: number
  extraction_provider?: string
  processing_status?: string
  page_count?: number
  rows: OCRRow[]
  total_candidate_rows?: number
  valid_rows?: number
  matched_students?: number
  unmatched_students?: number
  ambiguous_rows?: number
  present_count?: number
  absent_count?: number
  unknown_count?: number
  total_extracted: number
  total_matched: number
  total_unmatched: number
  total_uncertain: number
  processing_note?: string
  provider_errors?: string[]
}

// ---- Reports ----
export interface SubjectAttendanceSummary {
  subject_id: number
  subject_code: string
  subject_name: string
  total_sessions: number
  attended_sessions: number
  attendance_percentage: number
  is_shortage: boolean
}

export interface StudentAttendanceReport {
  student_id: number
  usn: string
  full_name: string
  subjects: SubjectAttendanceSummary[]
  overall_percentage: number
}

export interface ClassAttendanceRow {
  student_id: number
  usn: string
  full_name: string
  attended: number
  total: number
  percentage: number
  is_shortage: boolean
}

export interface ClassAttendanceReport {
  class_id: number
  class_name: string
  subject_id: number
  subject_name: string
  date_from?: string
  date_to?: string
  rows: ClassAttendanceRow[]
}

export interface DailyRow {
  attendance_date: string
  subject_code: string
  subject_name: string
  class_name: string
  present_count: number
  absent_count: number
  total_count: number
  attendance_percentage: number
}

// ---- Audit ----
export interface AuditEvent {
  id: number
  actor_user_id?: number
  actor_username?: string
  action: string
  entity_type?: string
  entity_id?: number
  details?: Record<string, unknown>
  created_at: string
}

// ---- Settings ----
export interface AppSetting {
  key: string
  value: string
  description?: string
}

// ---- Pagination helper ----
export interface PaginatedParams {
  skip?: number
  limit?: number
}
