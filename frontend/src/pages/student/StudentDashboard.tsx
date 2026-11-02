import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  GraduationCap,
  CalendarCheck,
  AlertTriangle,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  X,
  FileQuestion,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import toast from 'react-hot-toast'
import { useAuth } from '../../features/auth/AuthContext'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatCard } from '../../components/ui/StatCard'
import { Spinner } from '../../components/ui/Spinner'
import { dashboardsApi, type StudentDashboardData } from '../../api/dashboards'
import { correctionsApi } from '../../api/corrections'

export default function StudentDashboard() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  // Correction Request modal state
  const [selectedRecord, setSelectedRecord] = useState<{
    record_id: number
    subject_name: string
    date: string
    current_status: string
  } | null>(null)
  const [requestedStatus, setRequestedStatus] = useState<'present' | 'absent'>('present')
  const [correctionReason, setCorrectionReason] = useState('')
  const [requestSubmitting, setRequestSubmitting] = useState(false)

  // Fetch real aggregated student attendance from backend
  const { data, isLoading } = useQuery({
    queryKey: ['student-dashboard'],
    queryFn: dashboardsApi.getStudent,
  })

  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedRecord) return
    if (!correctionReason.trim()) {
      toast.error('Please specify a reason for the correction request')
      return
    }

    setRequestSubmitting(true)
    try {
      await correctionsApi.submitRequest({
        attendance_record_id: selectedRecord.record_id,
        requested_status: requestedStatus,
        reason: correctionReason.trim(),
      })
      toast.success('Correction request submitted for review!')
      setSelectedRecord(null)
      setCorrectionReason('')
      queryClient.invalidateQueries({ queryKey: ['student-dashboard'] })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit correction request')
    } finally {
      setRequestSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size="lg" />
      </div>
    )
  }

  const student = data?.student || {
    usn: user?.username || 'N/A',
    full_name: 'Student',
    class_name: 'Class',
    semester: 1,
    academic_year: '2024-25',
  }

  const summary = data?.summary || {
    overall_percentage: 0,
    total_conducted: 0,
    total_attended: 0,
    total_missed: 0,
    min_threshold: 75,
    has_shortage: false,
  }

  const subjects = data?.subjects || []
  const recentHistory = data?.recent_history || []
  const shortageSubjects = subjects.filter((s) => s.is_shortage)

  // Chart data
  const chartData = subjects.map((s) => ({
    name: s.subject_code || s.subject_name.slice(0, 10),
    fullName: s.subject_name,
    percentage: s.percentage,
    conducted: s.conducted,
    attended: s.attended,
  }))

  return (
    <div>
      <PageHeader
        title="Student Attendance Portal"
        subtitle={`${student.full_name} &bull; USN: ${student.usn} &bull; Class: ${student.class_name} (Sem ${student.semester})`}
      />

      {/* SUMMARY STAT CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Overall Attendance"
          value={`${summary.overall_percentage}%`}
          icon={<TrendingUp size={22} />}
          color={summary.has_shortage ? 'red' : 'green'}
        />
        <StatCard
          label="Total Conducted"
          value={summary.total_conducted}
          icon={<Clock size={22} />}
          color="blue"
        />
        <StatCard
          label="Classes Attended"
          value={summary.total_attended}
          icon={<CalendarCheck size={22} />}
          color="green"
        />
        <StatCard
          label="Classes Missed"
          value={summary.total_missed}
          icon={<AlertTriangle size={22} />}
          color={summary.total_missed > 0 ? 'yellow' : 'green'}
        />
      </div>

      {/* SHORTAGE WARNING ALERT */}
      {summary.has_shortage && (
        <div className="bg-[#FDF0EF] border border-status-absent/30 rounded-2xl p-5 mb-8 flex items-start gap-3">
          <AlertTriangle size={24} className="text-status-absent shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-bold text-status-absent text-sm">Attendance Shortage Alert</h4>
            <p className="text-sm text-ink-primary mt-1">
              Your overall attendance ({summary.overall_percentage}%) is below the college minimum requirement of{' '}
              {summary.min_threshold}%.
            </p>
            {shortageSubjects.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {shortageSubjects.map((s) => (
                  <span key={s.subject_id} className="badge-red text-xs">
                    {s.subject_code} &bull; {s.percentage}% ({s.attended}/{s.conducted})
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBJECT ATTENDANCE COMPARISON CHART & BREAKDOWN */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Chart */}
        <div className="card">
          <h3 className="font-bold text-ink-primary text-base mb-4">Subject Attendance Percentage vs Requirement</h3>
          {chartData.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-secondary">
              No finalized attendance sessions recorded yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val: any) => [`${val}%`, 'Attendance']}
                  labelFormatter={(name: string) => {
                    const row = chartData.find((c) => c.name === name)
                    return row ? `${row.fullName} (${row.attended}/${row.conducted} classes)` : name
                  }}
                />
                <ReferenceLine
                  y={summary.min_threshold}
                  stroke="#FF685F"
                  strokeDasharray="4 4"
                  label={{ value: `${summary.min_threshold}% Min`, fill: '#FF685F', fontSize: 10, position: 'insideTopRight' }}
                />
                <Bar dataKey="percentage" fill="#243630" radius={[6, 6, 0, 0]} name="Percentage" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Subject-wise Cards / List */}
        <div className="card">
          <h3 className="font-bold text-ink-primary text-base mb-4">Subject Attendance Breakdown</h3>
          {subjects.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-secondary">
              No courses configured for this semester.
            </div>
          ) : (
            <div className="space-y-3">
              {subjects.map((sub) => (
                <div
                  key={sub.subject_id}
                  className="p-3.5 rounded-xl bg-canvas border border-ink-border/60 flex items-center justify-between"
                >
                  <div className="flex-1 min-w-0 mr-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-bold text-ink-primary truncate">{sub.subject_name}</span>
                      <span className="text-xs font-semibold text-ink-secondary">
                        {sub.attended}/{sub.conducted} attended
                      </span>
                    </div>
                    {/* Progress Bar */}
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          sub.is_shortage
                            ? 'bg-status-absent'
                            : sub.percentage >= 85
                            ? 'bg-status-present'
                            : 'bg-status-warning'
                        }`}
                        style={{ width: `${Math.min(sub.percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={`text-sm font-extrabold ${
                        sub.is_shortage ? 'text-status-absent' : 'text-status-present'
                      }`}
                    >
                      {sub.percentage}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* RECENT SESSION HISTORY TABLE */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-border flex items-center justify-between">
          <div>
            <h3 className="font-bold text-ink-primary text-base">Recent Attendance Session History</h3>
            <p className="text-xs text-ink-secondary">
              Official records finalized by faculty. You can request attendance corrections if an error occurred.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr>
                <th className="table-th w-16">#</th>
                <th className="table-th">Date</th>
                <th className="table-th">Period</th>
                <th className="table-th">Subject</th>
                <th className="table-th">Status</th>
                <th className="table-th text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-border/60">
              {recentHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-sm text-ink-secondary">
                    No attendance sessions conducted for your class yet.
                  </td>
                </tr>
              ) : (
                recentHistory.map((rec, idx) => (
                  <tr key={rec.record_id} className="hover:bg-gray-50/50">
                    <td className="table-td text-ink-secondary">{idx + 1}</td>
                    <td className="table-td font-medium">{rec.date}</td>
                    <td className="table-td">Period {rec.period}</td>
                    <td className="table-td font-semibold text-ink-primary">
                      {rec.subject_name}{' '}
                      <span className="text-xs font-normal text-ink-secondary">({rec.subject_code})</span>
                    </td>
                    <td className="table-td">
                      {rec.status === 'present' ? (
                        <span className="badge-green flex items-center gap-1 w-fit">
                          <CheckCircle2 size={12} />
                          <span>Present</span>
                        </span>
                      ) : (
                        <span className="badge-red flex items-center gap-1 w-fit">
                          <XCircle size={12} />
                          <span>Absent</span>
                        </span>
                      )}
                      {rec.is_corrected && (
                        <span className="ml-2 badge-yellow text-[10px]">Corrected</span>
                      )}
                    </td>
                    <td className="table-td text-right">
                      <button
                        type="button"
                        onClick={() =>
                          setSelectedRecord({
                            record_id: rec.record_id,
                            subject_name: rec.subject_name,
                            date: rec.date,
                            current_status: rec.status,
                          })
                        }
                        className="text-xs font-semibold text-forest hover:text-forest-700 underline"
                      >
                        Request Correction
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ----------------- MODAL: STUDENT CORRECTION REQUEST ----------------- */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-ink-border animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-ink-border mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-forest-50 flex items-center justify-center">
                  <FileQuestion size={18} className="text-forest" />
                </div>
                <h3 className="text-lg font-bold text-ink-primary">Request Attendance Correction</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRecord(null)}
                className="text-ink-secondary hover:text-ink-primary p-1 rounded-lg hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="bg-canvas p-3.5 rounded-xl text-xs text-ink-secondary mb-4 space-y-1 border border-ink-border/50">
              <p>
                <strong className="text-ink-primary">Subject:</strong> {selectedRecord.subject_name}
              </p>
              <p>
                <strong className="text-ink-primary">Session Date:</strong> {selectedRecord.date}
              </p>
              <p>
                <strong className="text-ink-primary">Current Recorded Status:</strong>{' '}
                <span className="capitalize font-semibold">{selectedRecord.current_status}</span>
              </p>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4">
              <div>
                <label className="label" htmlFor="requested-status">
                  Requested Attendance Status <span className="text-coral">*</span>
                </label>
                <select
                  id="requested-status"
                  className="input"
                  value={requestedStatus}
                  onChange={(e) => setRequestedStatus(e.target.value as 'present' | 'absent')}
                >
                  <option value="present">Present</option>
                  <option value="absent">Absent</option>
                </select>
              </div>

              <div>
                <label className="label" htmlFor="correction-reason">
                  Reason for Correction <span className="text-coral">*</span>
                </label>
                <textarea
                  id="correction-reason"
                  rows={3}
                  className="input"
                  placeholder="e.g. Attended on duty / Technical glitch during register scan"
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  required
                />
                <p className="mt-1 text-xs text-ink-secondary">
                  Requests are sent to the assigned teacher or administrator for verification.
                </p>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-ink-border">
                <button
                  type="button"
                  onClick={() => setSelectedRecord(null)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={requestSubmitting}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  {requestSubmitting ? (
                    <>
                      <Spinner size="sm" />
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <span>Submit Request</span>
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
