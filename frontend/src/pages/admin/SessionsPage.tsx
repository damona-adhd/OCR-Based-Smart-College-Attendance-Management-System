import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { EmptyState } from '../../components/ui/EmptyState'
import { attendanceApi } from '../../api/attendance'
import { format } from 'date-fns'

const statusBadge = (s: string) => ({
  draft:     'badge-yellow',
  finalized: 'badge-green',
  cancelled: 'badge-red',
}[s] || 'badge-gray')

export default function SessionsPage() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['sessions-all'],
    queryFn: () => attendanceApi.listSessions({ limit: 200 }),
  })

  return (
    <div>
      <PageHeader title="Attendance Sessions" subtitle={`${sessions.length} total sessions`} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       sessions.length === 0 ? <EmptyState title="No attendance sessions yet" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Date</th>
                <th className="table-th">Subject</th>
                <th className="table-th">Class</th>
                <th className="table-th">Source</th>
                <th className="table-th">Status</th>
                <th className="table-th">Finalized At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="table-td font-medium">{s.attendance_date}</td>
                  <td className="table-td">{s.subject_id}</td>
                  <td className="table-td">{s.class_id}</td>
                  <td className="table-td capitalize">{s.source_type}</td>
                  <td className="table-td"><span className={statusBadge(s.status)}>{s.status}</span></td>
                  <td className="table-td text-xs text-gray-400">
                    {s.finalized_at ? format(new Date(s.finalized_at), 'dd MMM yyyy HH:mm') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
