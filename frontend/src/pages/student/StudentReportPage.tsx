import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { AttendanceBadge } from '../../components/ui/AttendanceBadge'
import { reportsApi } from '../../api/reports'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Printer } from 'lucide-react'

export default function StudentReportPage() {
  const { data: report, isLoading } = useQuery({
    queryKey: ['my-report'], queryFn: reportsApi.myReport
  })

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>
  if (!report) return null

  const chartData = report.subjects.map(s => ({
    name: s.subject_code,
    percentage: Number(s.attendance_percentage.toFixed(1)),
    shortage: s.is_shortage,
  }))

  return (
    <div>
      <PageHeader
        title="My Attendance Report"
        subtitle={`${report.full_name} — ${report.usn}`}
        actions={
          <button className="btn-secondary" onClick={() => window.print()}>
            <Printer size={16} />Print Report
          </button>
        }
      />

      {/* Overall */}
      <div className="card mb-6">
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-4xl font-bold text-gray-900">{report.overall_percentage.toFixed(1)}%</p>
            <p className="text-sm text-gray-500 mt-1">Overall Attendance</p>
          </div>
          <div className="h-12 w-px bg-gray-200" />
          <div className="flex-1 space-y-1">
            <p className="text-sm text-gray-600">Total Subjects: <strong>{report.subjects.length}</strong></p>
            <p className="text-sm text-gray-600">
              Classes Attended: <strong>{report.subjects.reduce((s, sub) => s + sub.attended_sessions, 0)}</strong> / {report.subjects.reduce((s, sub) => s + sub.total_sessions, 0)}
            </p>
            <p className="text-sm text-red-600">
              Shortages: <strong>{report.subjects.filter(s => s.is_shortage).length}</strong>
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-semibold mb-4">Subject-wise Attendance (%)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip formatter={(v: number) => `${v}%`} />
              <Bar dataKey="percentage" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.shortage ? '#f87171' : entry.percentage >= 90 ? '#22c55e' : '#facc15'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detail table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="table-th">Code</th>
              <th className="table-th">Subject</th>
              <th className="table-th">Attended</th>
              <th className="table-th">Total</th>
              <th className="table-th">Percentage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {report.subjects.map(s => (
              <tr key={s.subject_id} className="hover:bg-gray-50">
                <td className="table-td font-mono text-xs">{s.subject_code}</td>
                <td className="table-td">{s.subject_name}</td>
                <td className="table-td">{s.attended_sessions}</td>
                <td className="table-td">{s.total_sessions}</td>
                <td className="table-td"><AttendanceBadge percentage={s.attendance_percentage} isShortage={s.is_shortage} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
