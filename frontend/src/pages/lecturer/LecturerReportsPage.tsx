import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { AttendanceBadge } from '../../components/ui/AttendanceBadge'
import { assignmentsApi } from '../../api/assignments'
import { reportsApi } from '../../api/reports'
import { Download } from 'lucide-react'

export default function LecturerReportsPage() {
  const [assignmentId, setAssignmentId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const { data: assignments = [] } = useQuery({ queryKey: ['my-assignments'], queryFn: () => assignmentsApi.list() })
  const selected = assignments.find(a => String(a.id) === assignmentId)

  const { data: report, isLoading } = useQuery({
    queryKey: ['lecturer-report', assignmentId, dateFrom, dateTo],
    queryFn: () => reportsApi.classReport({
      class_id: selected!.class_id, subject_id: selected!.subject_id,
      date_from: dateFrom || undefined, date_to: dateTo || undefined,
    }),
    enabled: submitted && !!selected,
  })

  const csvUrl = submitted && selected
    ? reportsApi.classCSVUrl({ class_id: selected.class_id, subject_id: selected.subject_id, date_from: dateFrom || undefined, date_to: dateTo || undefined })
    : ''

  return (
    <div>
      <PageHeader title="Attendance Reports" />

      <div className="card mb-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div>
            <label className="label">Subject & Class</label>
            <select className="input" value={assignmentId} onChange={e => { setAssignmentId(e.target.value); setSubmitted(false) }}>
              <option value="">Select assignment</option>
              {assignments.map(a => <option key={a.id} value={a.id}>{a.subject?.subject_code} — {a.class_?.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">From Date</label>
            <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="label">To Date</label>
            <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button className="btn-primary" onClick={() => setSubmitted(true)} disabled={!assignmentId}>Generate</button>
          {csvUrl && <a href={csvUrl} download className="btn-secondary flex items-center gap-2"><Download size={16} />CSV</a>}
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}

      {report && (
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <p className="font-medium">{report.class_name} — {report.subject_name}</p>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">USN</th>
                <th className="table-th">Name</th>
                <th className="table-th">Attended / Total</th>
                <th className="table-th">Percentage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {report.rows.map(r => (
                <tr key={r.student_id} className="hover:bg-gray-50">
                  <td className="table-td font-mono text-xs">{r.usn}</td>
                  <td className="table-td">{r.full_name}</td>
                  <td className="table-td">{r.attended} / {r.total}</td>
                  <td className="table-td"><AttendanceBadge percentage={r.percentage} isShortage={r.is_shortage} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
