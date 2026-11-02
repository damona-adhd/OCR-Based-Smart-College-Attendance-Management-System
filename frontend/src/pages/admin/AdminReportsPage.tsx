import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { EmptyState } from '../../components/ui/EmptyState'
import { AttendanceBadge } from '../../components/ui/AttendanceBadge'
import { classesApi } from '../../api/classes'
import { subjectsApi } from '../../api/subjects'
import { reportsApi } from '../../api/reports'
import { Download } from 'lucide-react'

export default function AdminReportsPage() {
  const [classId, setClassId] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const { data: classes = [] } = useQuery({ queryKey: ['classes'], queryFn: () => classesApi.list() })
  const { data: subjects = [] } = useQuery({ queryKey: ['subjects'], queryFn: () => subjectsApi.list() })

  const { data: report, isLoading } = useQuery({
    queryKey: ['class-report', classId, subjectId, dateFrom, dateTo],
    queryFn: () => reportsApi.classReport({
      class_id: Number(classId), subject_id: Number(subjectId),
      date_from: dateFrom || undefined, date_to: dateTo || undefined,
    }),
    enabled: submitted && !!classId && !!subjectId,
  })

  const csvUrl = submitted && classId && subjectId
    ? reportsApi.classCSVUrl({ class_id: Number(classId), subject_id: Number(subjectId), date_from: dateFrom || undefined, date_to: dateTo || undefined })
    : ''

  return (
    <div>
      <PageHeader title="Attendance Reports" />

      <div className="card mb-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="label">Class</label>
            <select className="input" value={classId} onChange={e => { setClassId(e.target.value); setSubmitted(false) }}>
              <option value="">Select class</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Subject</label>
            <select className="input" value={subjectId} onChange={e => { setSubjectId(e.target.value); setSubmitted(false) }}>
              <option value="">Select subject</option>
              {subjects.map(s => <option key={s.id} value={s.id}>{s.subject_code} — {s.subject_name}</option>)}
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
          <button className="btn-primary" onClick={() => setSubmitted(true)} disabled={!classId || !subjectId}>Generate Report</button>
          {csvUrl && (
            <a href={csvUrl} download className="btn-secondary flex items-center gap-2">
              <Download size={16} />Export CSV
            </a>
          )}
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}

      {report && (
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <p className="font-medium">{report.class_name} — {report.subject_name}</p>
            <p className="text-sm text-gray-500">{report.rows.length} students</p>
          </div>
          {report.rows.length === 0 ? (
            <EmptyState title="No records for this selection" />
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="table-th">USN</th>
                  <th className="table-th">Name</th>
                  <th className="table-th">Attended</th>
                  <th className="table-th">Total</th>
                  <th className="table-th">Percentage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {report.rows.map(r => (
                  <tr key={r.student_id} className="hover:bg-gray-50">
                    <td className="table-td font-mono text-xs">{r.usn}</td>
                    <td className="table-td">{r.full_name}</td>
                    <td className="table-td">{r.attended}</td>
                    <td className="table-td">{r.total}</td>
                    <td className="table-td"><AttendanceBadge percentage={r.percentage} isShortage={r.is_shortage} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
