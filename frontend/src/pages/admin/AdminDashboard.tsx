import { useQuery } from '@tanstack/react-query'
import {
  Users,
  GraduationCap,
  BookOpen,
  Building2,
  CalendarCheck,
  BarChart3,
  TrendingUp,
  FileUp,
  PlusCircle,
  Clock,
  CheckCircle,
  ChevronRight,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatCard } from '../../components/ui/StatCard'
import { Spinner } from '../../components/ui/Spinner'
import { useAuth } from '../../features/auth/AuthContext'
import { dashboardsApi, type AdminDashboardData } from '../../api/dashboards'

const PIE_COLORS = ['#27845B', '#D9534F']

export default function AdminDashboard() {
  const { user } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: dashboardsApi.getAdmin,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size="lg" />
      </div>
    )
  }

  const summary = data?.summary || {
    total_students: 0,
    total_teachers: 0,
    total_classes: 0,
    total_subjects: 0,
    total_sessions: 0,
    finalized_sessions: 0,
    draft_sessions: 0,
    overall_percentage: 0,
    sessions_today: 0,
    today_present: 0,
    today_absent: 0,
    today_percentage: 0,
  }

  const trends = data?.trends || []
  const presentAbsent = data?.present_absent || []
  const classWise = data?.class_wise || []
  const recentActivity = data?.recent_activity || []

  return (
    <div>
      <PageHeader
        title="Administrator Dashboard"
        subtitle={`System Control Center &bull; Welcome, ${user?.username}`}
      />

      {/* QUICK ACTIONS BAR */}
      <div className="mb-8 flex flex-wrap items-center gap-3">
        <Link to="/admin/roster-import" className="btn-primary">
          <FileUp size={16} />
          <span>PDF Roster Import</span>
        </Link>
        <Link to="/admin/students" className="btn-secondary">
          <GraduationCap size={16} className="text-forest" />
          <span>Manage Students</span>
        </Link>
        <Link to="/admin/lecturers" className="btn-secondary">
          <Users size={16} className="text-forest" />
          <span>Manage Teachers</span>
        </Link>
        <Link to="/admin/classes" className="btn-secondary">
          <PlusCircle size={16} className="text-forest" />
          <span>Classes & Sections</span>
        </Link>
        <Link to="/admin/subjects" className="btn-secondary">
          <BookOpen size={16} className="text-forest" />
          <span>Subjects</span>
        </Link>
        <Link to="/admin/reports" className="btn-ghost">
          <BarChart3 size={16} />
          <span>Institutional Reports</span>
        </Link>
      </div>

      {/* LIVE METRIC SUMMARY CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Active Students"
          value={summary.total_students}
          icon={<GraduationCap size={22} />}
          color="blue"
        />
        <StatCard
          label="Active Faculty"
          value={summary.total_teachers}
          icon={<Users size={22} />}
          color="purple"
        />
        <StatCard
          label="Classes / Sections"
          value={summary.total_classes}
          icon={<Building2 size={22} />}
          color="green"
        />
        <StatCard
          label="Subjects Configured"
          value={summary.total_subjects}
          icon={<BookOpen size={22} />}
          color="yellow"
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Finalized Sessions"
          value={summary.finalized_sessions}
          icon={<CalendarCheck size={22} />}
          color="green"
        />
        <StatCard
          label="Draft Sessions"
          value={summary.draft_sessions}
          icon={<Clock size={22} />}
          color="yellow"
        />
        <StatCard
          label="Overall College Attendance"
          value={`${summary.overall_percentage}%`}
          icon={<TrendingUp size={22} />}
          color="blue"
        />
        <StatCard
          label="Today's Attendance Rate"
          value={`${summary.today_percentage}%`}
          icon={<CheckCircle size={22} />}
          color="green"
        />
      </div>

      {/* CHARTS ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Attendance Trend BarChart */}
        <div className="card lg:col-span-2">
          <h3 className="font-bold text-ink-primary text-base mb-4">Recent Daily Attendance Trend</h3>
          {trends.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-secondary">
              No finalized attendance sessions recorded yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="present" fill="#27845B" name="Present" radius={[4, 4, 0, 0]} />
                <Bar dataKey="absent" fill="#D9534F" name="Absent" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Present vs Absent Doughnut Chart */}
        <div className="card">
          <h3 className="font-bold text-ink-primary text-base mb-4">Present vs Absent Proportion</h3>
          {presentAbsent.every((p) => p.value === 0) ? (
            <div className="py-12 text-center text-sm text-ink-secondary">No records logged yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={presentAbsent}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {presentAbsent.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* CLASS-WISE ATTENDANCE COMPARISON */}
      {classWise.length > 0 && (
        <div className="card mb-8">
          <h3 className="font-bold text-ink-primary text-base mb-4">Class-Wise Attendance Comparison</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={classWise} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="class_name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(val: any) => [`${val}%`, 'Attendance Rate']} />
              <Bar dataKey="percentage" fill="#243630" radius={[4, 4, 0, 0]} name="Attendance %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* RECENT ATTENDANCE ACTIVITY TABLE */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-border flex items-center justify-between">
          <div>
            <h3 className="font-bold text-ink-primary text-base">Recent Institutional Attendance Sessions</h3>
            <p className="text-xs text-ink-secondary">Live stream of attendance sessions conducted by faculty.</p>
          </div>
          <Link to="/admin/sessions" className="text-xs font-semibold text-forest hover:underline">
            View All Sessions
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr>
                <th className="table-th w-16">#</th>
                <th className="table-th">Date</th>
                <th className="table-th">Class</th>
                <th className="table-th">Subject</th>
                <th className="table-th">Teacher</th>
                <th className="table-th">Status</th>
                <th className="table-th text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-border/60">
              {recentActivity.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-ink-secondary">
                    No attendance sessions recorded in the database yet.
                  </td>
                </tr>
              ) : (
                recentActivity.map((s, idx) => (
                  <tr key={s.id} className="hover:bg-gray-50/50">
                    <td className="table-td text-ink-secondary">{idx + 1}</td>
                    <td className="table-td font-medium">
                      {s.date}{' '}
                      <span className="text-xs text-ink-secondary">(P{s.period})</span>
                    </td>
                    <td className="table-td font-semibold text-ink-primary">{s.class_name}</td>
                    <td className="table-td">
                      {s.subject_name}{' '}
                      <span className="text-xs text-ink-secondary">({s.subject_code})</span>
                    </td>
                    <td className="table-td">{s.teacher_name}</td>
                    <td className="table-td">
                      <span
                        className={
                          s.status === 'finalized'
                            ? 'badge-green'
                            : s.status === 'draft'
                            ? 'badge-yellow'
                            : 'badge-red'
                        }
                      >
                        {s.status}
                      </span>
                    </td>
                    <td className="table-td text-right">
                      <Link
                        to={`/admin/sessions`}
                        className="text-xs font-semibold text-forest hover:underline"
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
