import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CalendarCheck,
  BookOpen,
  CheckCircle,
  Clock,
  UserPlus,
  PlusCircle,
  Upload,
  BarChart3,
  Users,
  ChevronRight,
  AlertCircle,
  X,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../../features/auth/AuthContext'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatCard } from '../../components/ui/StatCard'
import { Spinner } from '../../components/ui/Spinner'
import { dashboardsApi, type TeacherDashboardData } from '../../api/dashboards'
import { studentsApi } from '../../api/students'
import { subjectsApi } from '../../api/subjects'

export default function LecturerDashboard() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  // Modal states
  const [showAddStudentModal, setShowAddStudentModal] = useState(false)
  const [showAddSubjectModal, setShowAddSubjectModal] = useState(false)

  // Add Student form state
  const [studentName, setStudentName] = useState('')
  const [studentUsn, setStudentUsn] = useState('')
  const [studentClassId, setStudentClassId] = useState<number | ''>('')
  const [studentSubmitting, setStudentSubmitting] = useState(false)

  // Add Subject form state
  const [subjectName, setSubjectName] = useState('')
  const [subjectCode, setSubjectCode] = useState('')
  const [subjectClassId, setSubjectClassId] = useState<number | ''>('')
  const [subjectSubmitting, setSubjectSubmitting] = useState(false)

  // Fetch real database aggregated teacher dashboard data
  const { data, isLoading } = useQuery({
    queryKey: ['teacher-dashboard'],
    queryFn: dashboardsApi.getTeacher,
  })

  // Handle Add Student Submit
  const handleAddStudentSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanName = studentName.trim()
    const cleanUsn = studentUsn.trim().toUpperCase()

    if (!cleanName) {
      toast.error('Student Name is required')
      return
    }
    if (!cleanUsn) {
      toast.error('USN is required')
      return
    }

    const targetClassId = studentClassId || (data?.assignments[0]?.class_id ?? '')
    if (!targetClassId) {
      toast.error('Please assign student to a class')
      return
    }

    setStudentSubmitting(true)
    try {
      await studentsApi.quickAdd({
        full_name: cleanName,
        usn: cleanUsn,
        class_id: Number(targetClassId),
      })
      toast.success(`Student ${cleanName} (${cleanUsn}) added successfully!`)
      setStudentName('')
      setStudentUsn('')
      setShowAddStudentModal(false)
      queryClient.invalidateQueries({ queryKey: ['teacher-dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['class-roster'] })
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to add student'
      toast.error(msg)
    } finally {
      setStudentSubmitting(false)
    }
  }

  // Handle Add Subject Submit
  const handleAddSubjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanName = subjectName.trim()
    const cleanCode = subjectCode.trim().toUpperCase()

    if (!cleanName) {
      toast.error('Subject Name is required')
      return
    }
    if (!cleanCode) {
      toast.error('Subject Code is required')
      return
    }

    setSubjectSubmitting(true)
    try {
      await subjectsApi.quickAdd({
        subject_name: cleanName,
        subject_code: cleanCode,
        class_id: subjectClassId ? Number(subjectClassId) : undefined,
      })
      toast.success(`Subject ${cleanName} (${cleanCode}) created successfully!`)
      setSubjectName('')
      setSubjectCode('')
      setShowAddSubjectModal(false)
      queryClient.invalidateQueries({ queryKey: ['teacher-dashboard'] })
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create subject'
      toast.error(msg)
    } finally {
      setSubjectSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size="lg" />
      </div>
    )
  }

  const summary = data?.summary || {
    assigned_subjects: 0,
    assigned_classes: 0,
    total_students: 0,
    total_sessions: 0,
    finalized_sessions: 0,
    draft_sessions: 0,
    average_attendance: 0,
  }

  return (
    <div>
      <PageHeader
        title="Teacher Dashboard"
        subtitle={`Welcome, ${data?.teacher?.name || user?.username} (${data?.teacher?.employee_id || 'Faculty'})`}
      />

      {/* QUICK ACTIONS BAR */}
      <div className="mb-8 flex flex-wrap items-center gap-3">
        <Link to="/lecturer/attendance/new" className="btn-primary">
          <CalendarCheck size={16} />
          <span>Take Attendance</span>
        </Link>
        <button
          type="button"
          onClick={() => {
            setShowAddStudentModal(true)
            if (data?.assignments?.[0]?.class_id) {
              setStudentClassId(data.assignments[0].class_id)
            }
          }}
          className="btn-secondary"
        >
          <UserPlus size={16} className="text-forest" />
          <span>Add Student</span>
        </button>
        <button
          type="button"
          onClick={() => setShowAddSubjectModal(true)}
          className="btn-secondary"
        >
          <PlusCircle size={16} className="text-forest" />
          <span>Add Subject</span>
        </button>
        <Link to="/lecturer/ocr/upload" className="btn-secondary">
          <Upload size={16} className="text-forest" />
          <span>Upload Register</span>
        </Link>
        <Link to="/lecturer/reports" className="btn-ghost">
          <BarChart3 size={16} />
          <span>View Reports</span>
        </Link>
      </div>

      {/* SESSIONS AWAITING REVIEW BANNER */}
      {data?.needs_review && data.needs_review.length > 0 && (
        <div className="bg-[#FEF6EC] border border-status-warning/40 rounded-2xl p-4 mb-6 flex items-start gap-3">
          <AlertCircle size={20} className="text-status-warning shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-bold text-ink-primary text-sm">
              {data.needs_review.length} Session(s) Awaiting Review and Finalization
            </h4>
            <p className="text-xs text-ink-secondary mt-0.5">
              Draft attendance sessions are not included in official student attendance reports until finalized.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.needs_review.map((s) => (
                <Link
                  key={s.id}
                  to={`/lecturer/sessions/${s.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1 bg-white rounded-lg border border-ink-border text-xs font-semibold text-ink-primary hover:border-forest transition-colors shadow-sm"
                >
                  <span>
                    {s.subject_name} ({s.date})
                  </span>
                  <ChevronRight size={14} className="text-forest" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* METRIC SUMMARY CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Assigned Classes"
          value={summary.assigned_classes}
          icon={<Users size={22} />}
          color="blue"
        />
        <StatCard
          label="Total Students"
          value={summary.total_students}
          icon={<BookOpen size={22} />}
          color="purple"
        />
        <StatCard
          label="Sessions Finalized"
          value={summary.finalized_sessions}
          icon={<CheckCircle size={22} />}
          color="green"
        />
        <StatCard
          label="Average Attendance"
          value={`${summary.average_attendance}%`}
          icon={<Clock size={22} />}
          color="yellow"
        />
      </div>

      {/* MAIN TWO PANELS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Assigned Subjects & Classes */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-ink-primary text-base">My Assigned Classes & Subjects</h3>
            <span className="badge-forest text-xs">{data?.assignments?.length || 0} Assignments</span>
          </div>

          {!data?.assignments || data.assignments.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-ink-secondary">No teaching assignments found.</p>
              <p className="text-xs text-ink-secondary mt-1">
                An administrator must assign you to classes and subjects before you can conduct sessions.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.assignments.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-canvas border border-ink-border/50 hover:border-forest/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-forest-50 flex items-center justify-center">
                      <BookOpen size={18} className="text-forest" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-ink-primary">{a.subject_name}</p>
                      <p className="text-xs text-ink-secondary">
                        {a.subject_code} &bull; {a.class_name} (Sem {a.semester})
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/lecturer/attendance/new?class_id=${a.class_id}&subject_id=${a.subject_id}`}
                    className="btn-secondary text-xs py-1.5 px-3"
                  >
                    <span>Mark</span>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Attendance Sessions */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-ink-primary text-base">Recent Attendance Sessions</h3>
            <Link to="/lecturer/sessions" className="text-xs font-semibold text-forest hover:underline">
              View All
            </Link>
          </div>

          {!data?.recent_sessions || data.recent_sessions.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-ink-secondary">No attendance sessions conducted yet.</p>
              <Link to="/lecturer/attendance/new" className="btn-primary mt-3 inline-flex text-xs py-2">
                Create First Session
              </Link>
            </div>
          ) : (
            <div className="space-y-2.5">
              {data.recent_sessions.map((s) => (
                <Link
                  key={s.id}
                  to={`/lecturer/sessions/${s.id}`}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-canvas border border-ink-border/50 hover:bg-white hover:border-forest/40 transition-all shadow-none hover:shadow-sm"
                >
                  <div>
                    <p className="text-sm font-semibold text-ink-primary">
                      {s.subject_name} &bull; {s.class_name}
                    </p>
                    <p className="text-xs text-ink-secondary">
                      Date: {s.date} (Period {s.period}) &bull;{' '}
                      <span className="capitalize">{s.source_type}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={
                        s.status === 'finalized'
                          ? 'badge-green'
                          : s.status === 'draft'
                          ? 'badge-yellow'
                          : 'badge-red'
                      }
                    >
                      {s.status}
                    </span>
                    <ChevronRight size={14} className="text-ink-secondary" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ----------------- MODAL: TEACHER CAN ADD A STUDENT ----------------- */}
      {showAddStudentModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-ink-border animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-ink-border mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-forest-50 flex items-center justify-center">
                  <UserPlus size={18} className="text-forest" />
                </div>
                <h3 className="text-lg font-bold text-ink-primary">Add Student</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddStudentModal(false)}
                className="text-ink-secondary hover:text-ink-primary p-1 rounded-lg hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddStudentSubmit} className="space-y-4">
              <div>
                <label className="label" htmlFor="student-name">
                  Student Name <span className="text-coral">*</span>
                </label>
                <input
                  id="student-name"
                  type="text"
                  className="input"
                  placeholder="e.g. Rahul Sharma"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="label" htmlFor="student-usn">
                  USN (University Seat Number) <span className="text-coral">*</span>
                </label>
                <input
                  id="student-usn"
                  type="text"
                  className="input font-mono"
                  placeholder="e.g. 1CS21CS045"
                  value={studentUsn}
                  onChange={(e) => setStudentUsn(e.target.value)}
                  required
                />
                <p className="mt-1 text-xs text-ink-secondary">
                  Must be unique across the college database.
                </p>
              </div>

              {/* Class association */}
              {data?.assignments && data.assignments.length > 0 && (
                <div>
                  <label className="label" htmlFor="student-class">
                    Assigned Class <span className="text-coral">*</span>
                  </label>
                  <select
                    id="student-class"
                    className="input"
                    value={studentClassId}
                    onChange={(e) => setStudentClassId(Number(e.target.value))}
                    required
                  >
                    {data.assignments.map((a) => (
                      <option key={a.class_id} value={a.class_id}>
                        {a.class_name} (Sem {a.semester})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-ink-border">
                <button
                  type="button"
                  onClick={() => setShowAddStudentModal(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={studentSubmitting}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  {studentSubmitting ? (
                    <>
                      <Spinner size="sm" />
                      <span>Saving Student...</span>
                    </>
                  ) : (
                    <span>Save Student</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- MODAL: TEACHER CAN ADD SUBJECT ----------------- */}
      {showAddSubjectModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-ink-border animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-ink-border mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-forest-50 flex items-center justify-center">
                  <PlusCircle size={18} className="text-forest" />
                </div>
                <h3 className="text-lg font-bold text-ink-primary">Add Subject</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddSubjectModal(false)}
                className="text-ink-secondary hover:text-ink-primary p-1 rounded-lg hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddSubjectSubmit} className="space-y-4">
              <div>
                <label className="label" htmlFor="subject-name">
                  Subject Name <span className="text-coral">*</span>
                </label>
                <input
                  id="subject-name"
                  type="text"
                  className="input"
                  placeholder="e.g. Computer Networks"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="label" htmlFor="subject-code">
                  Subject Code <span className="text-coral">*</span>
                </label>
                <input
                  id="subject-code"
                  type="text"
                  className="input font-mono"
                  placeholder="e.g. CS501"
                  value={subjectCode}
                  onChange={(e) => setSubjectCode(e.target.value)}
                  required
                />
                <p className="mt-1 text-xs text-ink-secondary">
                  Unique subject code configured for institutional curriculum.
                </p>
              </div>

              {/* Optional Class association */}
              {data?.assignments && data.assignments.length > 0 && (
                <div>
                  <label className="label" htmlFor="subject-class">
                    Associate with Class (Optional)
                  </label>
                  <select
                    id="subject-class"
                    className="input"
                    value={subjectClassId}
                    onChange={(e) => setSubjectClassId(e.target.value ? Number(e.target.value) : '')}
                  >
                    <option value="">-- No immediate class binding --</option>
                    {data.assignments.map((a) => (
                      <option key={a.class_id} value={a.class_id}>
                        {a.class_name} (Sem {a.semester})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-ink-border">
                <button
                  type="button"
                  onClick={() => setShowAddSubjectModal(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={subjectSubmitting}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  {subjectSubmitting ? (
                    <>
                      <Spinner size="sm" />
                      <span>Creating Subject...</span>
                    </>
                  ) : (
                    <span>Save Subject</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
