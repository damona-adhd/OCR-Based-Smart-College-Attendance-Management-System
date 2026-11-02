import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { EmptyState } from '../../components/ui/EmptyState'
import { attendanceApi } from '../../api/attendance'
import { Eye } from 'lucide-react'

const statusBadge = (s: string) => ({ draft: 'badge-yellow', finalized: 'badge-green', cancelled: 'badge-red' }[s] || 'badge-gray')

export default function SessionsListPage() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['my-sessions'], queryFn: () => attendanceApi.listSessions({ limit: 200 })
  })

  return (
    <div>
      <PageHeader title="Attendance Sessions" subtitle={`${sessions.length} sessions`} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       sessions.length === 0 ? <EmptyState title="No sessions yet" description="Create your first attendance session" action={<Link to="/lecturer/attendance/new" className="btn-primary">New Session</Link>} /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Date</th>
                <th className="table-th">Source</th>
                <th className="table-th">Status</th>
                <th className="table-th w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="table-td font-medium">{s.attendance_date}</td>
                  <td className="table-td capitalize">{s.source_type}</td>
                  <td className="table-td"><span className={statusBadge(s.status)}>{s.status}</span></td>
                  <td className="table-td">
                    <Link to={`/lecturer/sessions/${s.id}`} className="btn-ghost p-1.5" title="View"><Eye size={15} /></Link>
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
