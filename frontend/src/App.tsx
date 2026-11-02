import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './features/auth/AuthContext'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'

// Auth
import LoginPage from './pages/auth/LoginPage'
import UnauthorizedPage from './pages/auth/UnauthorizedPage'
import NotFoundPage from './pages/auth/NotFoundPage'

// Admin
import AdminDashboard from './pages/admin/AdminDashboard'
import DepartmentsPage from './pages/admin/DepartmentsPage'
import ClassesPage from './pages/admin/ClassesPage'
import SubjectsPage from './pages/admin/SubjectsPage'
import StudentsPage from './pages/admin/StudentsPage'
import LecturersPage from './pages/admin/LecturersPage'
import AssignmentsPage from './pages/admin/AssignmentsPage'
import SessionsPage from './pages/admin/SessionsPage'
import AdminReportsPage from './pages/admin/AdminReportsPage'
import AuditPage from './pages/admin/AuditPage'
import SettingsPage from './pages/admin/SettingsPage'
import RosterImportPage from './pages/admin/RosterImportPage'

// Lecturer
import LecturerDashboard from './pages/lecturer/LecturerDashboard'
import CreateSessionPage from './pages/lecturer/CreateSessionPage'
import ManualAttendancePage from './pages/lecturer/ManualAttendancePage'
import OCRUploadPage from './pages/lecturer/OCRUploadPage'
import OCRReviewPage from './pages/lecturer/OCRReviewPage'
import SessionDetailPage from './pages/lecturer/SessionDetailPage'
import SessionsListPage from './pages/lecturer/SessionsListPage'
import LecturerReportsPage from './pages/lecturer/LecturerReportsPage'

// Student
import StudentDashboard from './pages/student/StudentDashboard'
import StudentAttendancePage from './pages/student/StudentAttendancePage'
import StudentReportPage from './pages/student/StudentReportPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* Root redirect */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Admin */}
        <Route element={<ProtectedRoute allowedRoles={['admin']}><AppLayout /></ProtectedRoute>}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/departments" element={<DepartmentsPage />} />
          <Route path="/admin/classes" element={<ClassesPage />} />
          <Route path="/admin/subjects" element={<SubjectsPage />} />
          <Route path="/admin/students" element={<StudentsPage />} />
          <Route path="/admin/lecturers" element={<LecturersPage />} />
          <Route path="/admin/assignments" element={<AssignmentsPage />} />
          <Route path="/admin/roster-import" element={<RosterImportPage />} />
          <Route path="/admin/sessions" element={<SessionsPage />} />
          <Route path="/admin/reports" element={<AdminReportsPage />} />
          <Route path="/admin/audit" element={<AuditPage />} />
          <Route path="/admin/settings" element={<SettingsPage />} />
        </Route>

        {/* Lecturer */}
        <Route element={<ProtectedRoute allowedRoles={['lecturer']}><AppLayout /></ProtectedRoute>}>
          <Route path="/lecturer" element={<LecturerDashboard />} />
          <Route path="/lecturer/assignments" element={<SessionsListPage />} />
          <Route path="/lecturer/attendance/new" element={<CreateSessionPage />} />
          <Route path="/lecturer/sessions" element={<SessionsListPage />} />
          <Route path="/lecturer/sessions/:sessionId" element={<SessionDetailPage />} />
          <Route path="/lecturer/sessions/:sessionId/manual" element={<ManualAttendancePage />} />
          <Route path="/lecturer/sessions/:sessionId/upload" element={<OCRUploadPage />} />
          <Route path="/lecturer/ocr/upload" element={<CreateSessionPage />} />
          <Route path="/lecturer/sessions/:sessionId/ocr-review" element={<OCRReviewPage />} />
          <Route path="/lecturer/reports" element={<LecturerReportsPage />} />
        </Route>

        {/* Student */}
        <Route element={<ProtectedRoute allowedRoles={['student']}><AppLayout /></ProtectedRoute>}>
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/student/attendance" element={<StudentAttendancePage />} />
          <Route path="/student/report" element={<StudentReportPage />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
