import { useQuery } from '@tanstack/react-query'
import { Spinner } from '../../components/ui/Spinner'
import { PageHeader } from '../../components/ui/PageHeader'
import { EmptyState } from '../../components/ui/EmptyState'
import { attendanceApi } from '../../api/attendance'
import { format } from 'date-fns'

export default function StudentAttendancePage() {
  const { data: records = [], isLoading } = useQuery({
    queryKey: ['my-attendance'], queryFn: () => attendanceApi.myAttendance()
  })

  return (
    <div>
      <PageHeader title="My Attendance Records" subtitle={`${records.length} finalized records`} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       records.length === 0 ? <EmptyState title="No attendance records" description="Finalized attendance will appear here" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Session</th>
                <th className="table-th">Status</th>
                <th className="table-th">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map(r => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="table-td">{r.attendance_session_id}</td>
                  <td className="table-td">
                    <span className={r.status === 'present' ? 'badge-green' : 'badge-red'}>{r.status}</span>
                  </td>
                  <td className="table-td capitalize">{r.source_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
