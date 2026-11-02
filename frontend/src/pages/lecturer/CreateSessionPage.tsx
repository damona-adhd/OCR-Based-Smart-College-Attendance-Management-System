import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { assignmentsApi } from '../../api/assignments'
import { attendanceApi } from '../../api/attendance'

export default function CreateSessionPage() {
  const navigate = useNavigate()
  const [assignmentId, setAssignmentId] = useState('')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [sourceType, setSourceType] = useState<'manual' | 'ocr'>('manual')

  const { data: assignments = [], isLoading } = useQuery({ queryKey: ['my-assignments'], queryFn: () => assignmentsApi.list() })

  const createMut = useMutation({
    mutationFn: attendanceApi.createSession,
    onSuccess: (session) => {
      toast.success('Session created')
      if (sourceType === 'manual') {
        navigate(`/lecturer/sessions/${session.id}/manual`)
      } else {
        navigate(`/lecturer/sessions/${session.id}/upload`)
      }
    },
    onError: (e: any) => {
      const detail = e.response?.data?.detail || 'Failed to create session'
      if (e.response?.status === 409) {
        toast.error('A session already exists for this class, subject, and date. Choose a different date or view existing sessions.')
      } else {
        toast.error(detail)
      }
    },
  })

  const selected = assignments.find(a => String(a.id) === assignmentId)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected) return
    createMut.mutate({
      subject_id: selected.subject_id,
      class_id: selected.class_id,
      attendance_date: date,
      source_type: sourceType,
    })
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader title="Start Attendance" subtitle="Create a new attendance session" />

      <div className="card max-w-lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="label">Select Subject & Class</label>
            <select className="input" value={assignmentId} onChange={e => setAssignmentId(e.target.value)} required>
              <option value="">Choose assignment</option>
              {assignments.map(a => (
                <option key={a.id} value={a.id}>
                  {a.subject?.subject_code} — {a.subject?.subject_name} ({a.class_?.name})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Attendance Date</label>
            <input
              className="input"
              type="date"
              value={date}
              max={new Date().toISOString().split('T')[0]}
              onChange={e => setDate(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label">Entry Method</label>
            <div className="grid grid-cols-2 gap-3 mt-1">
              <button
                type="button"
                className={`p-4 rounded-xl border-2 text-left transition-colors ${sourceType === 'manual' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}
                onClick={() => setSourceType('manual')}
              >
                <p className="font-medium text-sm">Manual Entry</p>
                <p className="text-xs text-gray-400 mt-1">Mark each student present or absent</p>
              </button>
              <button
                type="button"
                className={`p-4 rounded-xl border-2 text-left transition-colors ${sourceType === 'ocr' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}
                onClick={() => setSourceType('ocr')}
              >
                <p className="font-medium text-sm">Upload Register (OCR)</p>
                <p className="text-xs text-gray-400 mt-1">Upload a photo of the attendance sheet</p>
              </button>
            </div>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={createMut.isPending}>
            {createMut.isPending ? <Spinner size="sm" /> : 'Create Session'}
          </button>
        </form>
      </div>
    </div>
  )
}
