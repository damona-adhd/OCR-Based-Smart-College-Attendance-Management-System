import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { EmptyState } from '../../components/ui/EmptyState'
import { reportsApi } from '../../api/reports'
import { format } from 'date-fns'

export default function AuditPage() {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ['audit'], queryFn: () => reportsApi.auditLogs({ limit: 100 })
  })

  return (
    <div>
      <PageHeader title="Audit Logs" subtitle="System activity trail" />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size="lg" /></div> :
       events.length === 0 ? <EmptyState title="No audit events" /> : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="table-th">Time</th>
                <th className="table-th">Actor</th>
                <th className="table-th">Action</th>
                <th className="table-th">Entity</th>
                <th className="table-th">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {events.map((ev: any) => (
                <tr key={ev.id} className="hover:bg-gray-50">
                  <td className="table-td text-xs whitespace-nowrap">
                    {format(new Date(ev.created_at), 'dd MMM yy HH:mm')}
                  </td>
                  <td className="table-td">{ev.actor_username || '—'}</td>
                  <td className="table-td"><span className="badge-blue">{ev.action}</span></td>
                  <td className="table-td">{ev.entity_type ? `${ev.entity_type} #${ev.entity_id}` : '—'}</td>
                  <td className="table-td text-xs text-gray-400 max-w-xs truncate">
                    {ev.details ? JSON.stringify(ev.details) : '—'}
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
