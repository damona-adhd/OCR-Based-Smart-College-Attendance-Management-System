import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { CheckCircle, XCircle, CheckSquare, UserPlus, X } from 'lucide-react'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { attendanceApi } from '../../api/attendance'
import { studentsApi } from '../../api/students'
import { useQueryClient } from '@tanstack/react-query'
import type { AttendanceStatus } from '../../types'

export default function ManualAttendancePage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const id = Number(sessionId)

  const { data: session, isLoading: loadingSession } = useQuery({
    queryKey: ['session', id], queryFn: () => attendanceApi.getSession(id)
  })

  const { data: students = [], isLoading: loadingStudents } = useQuery({
    queryKey: ['class-roster', session?.class_id],
    queryFn: () => studentsApi.classRoster(session!.class_id),
    enabled: !!session?.class_id,
  })

  const [attendance, setAttendance] = useState<Record<number, AttendanceStatus>>({})
  const [showConfirm, setShowConfirm] = useState(false)
  const [showAddStudent, setShowAddStudent] = useState(false)
  const [newStudentName, setNewStudentName] = useState('')
  const [newStudentUsn, setNewStudentUsn] = useState('')
  const [addingStudent, setAddingStudent] = useState(false)

  // Initialize all to absent
  useEffect(() => {
    if (students.length > 0) {
      setAttendance(prev => {
        const init = { ...prev }
        students.forEach(s => {
          if (!init[s.id]) init[s.id] = 'absent'
        })
        return init
      })
    }
  }, [students])

  const saveMut = useMutation({
    mutationFn: () => attendanceApi.submitRecords(id, Object.entries(attendance).map(([sid, status]) => ({ student_id: Number(sid), status }))),
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed to save'),
  })

  const finalizeMut = useMutation({
    mutationFn: async () => {
      await saveMut.mutateAsync()
      return attendanceApi.finalizeSession(id)
    },
    onSuccess: () => {
      toast.success('Attendance finalized!')
      navigate(`/lecturer/sessions/${id}`)
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const toggleAll = (status: AttendanceStatus) => {
    const init: Record<number, AttendanceStatus> = {}
    students.forEach(s => { init[s.id] = status })
    setAttendance(init)
  }

  const presentCount = Object.values(attendance).filter(v => v === 'present').length
  const absentCount = Object.values(attendance).filter(v => v === 'absent').length

  if (loadingSession || loadingStudents) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>
  if (!session) return <p className="text-red-500">Session not found</p>
  if (session.status === 'finalized') return (
    <div className="card text-center py-8">
      <CheckCircle size={40} className="text-green-500 mx-auto mb-3" />
      <p className="font-medium">This session is already finalized.</p>
      <button className="btn-secondary mt-4" onClick={() => navigate(`/lecturer/sessions/${id}`)}>View Session</button>
    </div>
  )

  const handleAddStudentSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newStudentName.trim() || !newStudentUsn.trim()) {
      toast.error('Both name and USN are required')
      return
    }
    setAddingStudent(true)
    try {
      const res = await studentsApi.quickAdd({
        full_name: newStudentName.trim(),
        usn: newStudentUsn.trim().toUpperCase(),
        class_id: session!.class_id,
      })
      toast.success(`Student ${res.full_name} (${res.usn}) added to class!`)
      setNewStudentName('')
      setNewStudentUsn('')
      setShowAddStudent(false)
      queryClient.invalidateQueries({ queryKey: ['class-roster', session!.class_id] })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to add student')
    } finally {
      setAddingStudent(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Manual Attendance"
        subtitle={`${session.attendance_date} — ${students.length} students`}
        actions={
          <div className="flex gap-2">
            <button className="btn-secondary text-xs" onClick={() => setShowAddStudent(true)}>
              <UserPlus size={14} className="text-forest" />
              <span>Add Student</span>
            </button>
            <button className="btn-secondary text-xs" onClick={() => toggleAll('present')}>
              <CheckSquare size={14} />
              <span>All Present</span>
            </button>
            <button className="btn-secondary text-xs" onClick={() => toggleAll('absent')}>
              All Absent
            </button>
          </div>
        }
      />

      {/* Summary bar */}
      <div className="flex gap-4 mb-4">
        <div className="flex items-center gap-2 px-4 py-2 bg-green-50 rounded-lg">
          <CheckCircle size={16} className="text-green-500" />
          <span className="text-sm font-medium text-green-700">{presentCount} Present</span>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-red-50 rounded-lg">
          <XCircle size={16} className="text-red-500" />
          <span className="text-sm font-medium text-red-700">{absentCount} Absent</span>
        </div>
      </div>

      {/* Student list */}
      <div className="card p-0 overflow-hidden mb-6">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="table-th">#</th>
              <th className="table-th">USN</th>
              <th className="table-th">Name</th>
              <th className="table-th">Attendance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {students.map((student, i) => (
              <tr key={student.id} className="hover:bg-gray-50">
                <td className="table-td text-gray-400">{i + 1}</td>
                <td className="table-td font-mono text-xs">{student.usn}</td>
                <td className="table-td font-medium">{student.full_name}</td>
                <td className="table-td">
                  <div className="flex gap-2">
                    <button
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${attendance[student.id] === 'present' ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-green-100'}`}
                      onClick={() => setAttendance(a => ({ ...a, [student.id]: 'present' }))}
                    >Present</button>
                    <button
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${attendance[student.id] === 'absent' ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-red-100'}`}
                      onClick={() => setAttendance(a => ({ ...a, [student.id]: 'absent' }))}
                    >Absent</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          className="btn-secondary"
          onClick={() => { saveMut.mutate(); toast.success('Draft saved') }}
          disabled={saveMut.isPending}
        >
          {saveMut.isPending ? <Spinner size="sm" /> : 'Save Draft'}
        </button>
        <button className="btn-primary" onClick={() => setShowConfirm(true)}>
          Review & Finalize
        </button>
      </div>

      {showConfirm && (
        <ConfirmDialog
          title="Finalize Attendance"
          message={`Finalize attendance for ${session.attendance_date}? ${presentCount} present, ${absentCount} absent. This cannot be undone without an authorized correction.`}
          onConfirm={() => { setShowConfirm(false); finalizeMut.mutate() }}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      {/* Modal: Teacher adds student directly to this session's class */}
      {showAddStudent && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-ink-border animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-ink-border mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-forest-50 flex items-center justify-center">
                  <UserPlus size={18} className="text-forest" />
                </div>
                <h3 className="text-lg font-bold text-ink-primary">Add Student to Roster</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddStudent(false)}
                className="text-ink-secondary hover:text-ink-primary p-1 rounded-lg hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddStudentSubmit} className="space-y-4">
              <div>
                <label className="label" htmlFor="m-student-name">
                  Student Name <span className="text-coral">*</span>
                </label>
                <input
                  id="m-student-name"
                  type="text"
                  className="input"
                  placeholder="e.g. Vikramaditya Rao"
                  value={newStudentName}
                  onChange={(e) => setNewStudentName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="label" htmlFor="m-student-usn">
                  USN (University Seat Number) <span className="text-coral">*</span>
                </label>
                <input
                  id="m-student-usn"
                  type="text"
                  className="input font-mono"
                  placeholder="e.g. 1CS21CS099"
                  value={newStudentUsn}
                  onChange={(e) => setNewStudentUsn(e.target.value)}
                  required
                />
                <p className="mt-1 text-xs text-ink-secondary">
                  Must be unique across the college database.
                </p>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-ink-border">
                <button
                  type="button"
                  onClick={() => setShowAddStudent(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingStudent}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  {addingStudent ? (
                    <>
                      <Spinner size="sm" />
                      <span>Adding...</span>
                    </>
                  ) : (
                    <span>Add Student</span>
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
