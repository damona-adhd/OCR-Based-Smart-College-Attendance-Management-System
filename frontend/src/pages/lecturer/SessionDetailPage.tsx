import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import { useState } from 'react'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { Modal } from '../../components/ui/Modal'
import { attendanceApi } from '../../api/attendance'
import { format } from 'date-fns'
import type { AttendanceStatus } from '../../types'

export default function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const id = Number(sessionId)

  const [correcting, setCorrecting] = useState<{ studentId: number; name: string } | null>(null)
  const [newStatus, setNewStatus] = useState<AttendanceStatus>('present')
  const [reason, setReason] = useState('')

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', id], queryFn: () => attendanceApi.getSession(id)
  })

  const correctMut = useMutation({
    mutationFn: () => attendanceApi.correctRecord(id, correcting!.studentId, newStatus, reason),
    onSuccess: () => {
      toast.success('Record corrected')
      qc.invalidateQueries({ queryKey: ['session', id] })
      setCorrecting(null)
      setReason('')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>
  if (!session) return <p className="text-red-500">Session not found</p>

  const presentCount = session.records?.filter(r => r.status === 'present').length || 0
  const absentCount = session.records?.filter(r => r.status === 'absent').length || 0

  return (
    <div>
      <button className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4" onClick={() => navigate(-1)}>
        <ArrowLeft size={16} />Back
      </button>

      <PageHeader
        title={`Attendance — ${session.attendance_date}`}
        subtitle={`${session.subject_name || ''} · ${session.class_name || ''} · ${session.source_type.toUpperCase()}`}
        actions={
          <span className={
            session.status === 'finalized' ? 'badge-green' :
            session.status === 'draft' ? 'badge-yellow' : 'badge-red'
          }>{session.status}</span>
        }
      />

      <div className="flex gap-4 mb-6">
        <div className="px-4 py-3 bg-green-50 rounded-lg">
          <p className="text-xs text-gray-500">Present</p>
          <p className="text-xl font-bold text-green-600">{presentCount}</p>
        </div>
        <div className="px-4 py-3 bg-red-50 rounded-lg">
          <p className="text-xs text-gray-500">Absent</p>
          <p className="text-xl font-bold text-red-600">{absentCount}</p>
        </div>
        {session.finalized_at && (
          <div className="px-4 py-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Finalized</p>
            <p className="text-sm font-medium">{format(new Date(session.finalized_at), 'dd MMM yyyy HH:mm')}</p>
          </div>
        )}
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="table-th">USN</th>
              <th className="table-th">Name</th>
              <th className="table-th">Status</th>
              {session.status === 'finalized' && <th className="table-th">Correct</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {session.records?.map(rec => (
              <tr key={rec.id} className="hover:bg-gray-50">
                <td className="table-td font-mono text-xs">{rec.student_usn}</td>
                <td className="table-td">{rec.student_name}</td>
                <td className="table-td">
                  <span className={rec.status === 'present' ? 'badge-green' : 'badge-red'}>
                    {rec.status}
                  </span>
                </td>
                {session.status === 'finalized' && (
                  <td className="table-td">
                    <button
                      className="btn-ghost text-xs py-1 px-2"
                      onClick={() => { setCorrecting({ studentId: rec.student_id, name: rec.student_name || '' }); setNewStatus(rec.status === 'present' ? 'absent' : 'present') }}
                    >Correct</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {correcting && (
        <Modal title="Correct Attendance Record" onClose={() => setCorrecting(null)}>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Correcting record for <strong>{correcting.name}</strong>.</p>
            <div>
              <label className="label">New Status</label>
              <select className="input" value={newStatus} onChange={e => setNewStatus(e.target.value as AttendanceStatus)}>
                <option value="present">Present</option>
                <option value="absent">Absent</option>
              </select>
            </div>
            <div>
              <label className="label">Reason for Correction *</label>
              <textarea className="input" rows={3} value={reason} onChange={e => setReason(e.target.value)} placeholder="Provide a reason for this correction" required />
            </div>
            <div className="flex gap-3 justify-end">
              <button className="btn-secondary" onClick={() => setCorrecting(null)}>Cancel</button>
              <button className="btn-primary" onClick={() => correctMut.mutate()} disabled={!reason || correctMut.isPending}>
                {correctMut.isPending ? <Spinner size="sm" /> : 'Apply Correction'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
