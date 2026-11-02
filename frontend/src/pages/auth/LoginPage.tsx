import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Shield,
  GraduationCap,
  User,
  ArrowLeft,
  Eye,
  EyeOff,
  CheckCircle2,
  Lock,
  ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../features/auth/AuthContext'
import { Spinner } from '../../components/ui/Spinner'
import type { UserRole } from '../../types'

type SelectedRole = 'admin' | 'teacher' | 'student' | null

const schema = z.object({
  username: z.string().min(1, 'Username or USN is required'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

function getRoleHome(role: UserRole): string {
  if (role === 'admin') return '/admin'
  if (role === 'lecturer') return '/lecturer'
  return '/student'
}

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Selected role determines whether cards are shown or role-specific form
  const [selectedRole, setSelectedRole] = useState<SelectedRole>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  // If already authenticated and visiting /login, auto-redirect to role dashboard
  useEffect(() => {
    if (user) {
      navigate(getRoleHome(user.role), { replace: true })
    }
  }, [user, navigate])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const handleSelectRole = (role: SelectedRole) => {
    setSelectedRole(role)
    reset()
    setShowPassword(false)
  }

  const handleBackToRoles = () => {
    setSelectedRole(null)
    reset()
  }

  const onSubmit = async (data: FormData) => {
    if (!selectedRole) return
    setLoading(true)
    try {
      await login(data.username, data.password, selectedRole)
      const stored = localStorage.getItem('user')
      const authenticatedUser = stored ? JSON.parse(stored) : null
      const destination = (location.state as any)?.from?.pathname || getRoleHome(authenticatedUser?.role || 'student')
      toast.success(`Welcome, ${authenticatedUser?.username || 'User'}!`)
      navigate(destination, { replace: true })
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Invalid login credentials or role mismatch'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const roleCardConfig = {
    admin: {
      title: 'Administrator',
      subtitle: 'System Administration',
      desc: 'Manage students, teachers, classes, subjects, and attendance records.',
      icon: <Shield className="w-8 h-8 text-forest" />,
      badgeColor: 'bg-forest-100 text-forest',
      identifierLabel: 'Username or Admin ID',
      identifierPlaceholder: 'e.g. admin',
      buttonText: 'Continue as Administrator',
    },
    teacher: {
      title: 'Teacher',
      subtitle: 'Faculty & Lecturer Portal',
      desc: 'Mark attendance, process registers, and view assigned class reports.',
      icon: <GraduationCap className="w-8 h-8 text-forest" />,
      badgeColor: 'bg-emerald-50 text-emerald-800',
      identifierLabel: 'Employee ID or Username',
      identifierPlaceholder: 'e.g. dr.sharma or EMP001',
      buttonText: 'Continue as Teacher',
    },
    student: {
      title: 'Student',
      subtitle: 'Student Portal',
      desc: 'View personal attendance and subject-wise attendance percentages.',
      icon: <User className="w-8 h-8 text-forest" />,
      badgeColor: 'bg-cyan-light text-cyan-900',
      identifierLabel: 'USN (University Seat Number)',
      identifierPlaceholder: 'e.g. 1CS21CS001',
      buttonText: 'Continue as Student',
    },
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-between py-10 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto w-full text-center">
        <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-forest-100 border border-forest-500/20 text-forest text-xs font-semibold tracking-wide uppercase mb-4">
          <CheckCircle2 size={15} className="text-forest" />
          College Attendance Management System
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-ink-primary tracking-tight">
          Smart College Attendance
        </h1>
        <p className="mt-2 text-base text-ink-secondary max-w-xl mx-auto">
          Secure, verified digital attendance tracking with integrated document processing and role-based analytics.
        </p>
      </div>

      {/* Main Content Area */}
      <div className="max-w-4xl mx-auto w-full my-8">
        {!selectedRole ? (
          /* THREE ROLE CARDS SELECTION VIEW */
          <div>
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-ink-primary">Select Your Role to Continue</h2>
              <p className="text-sm text-ink-secondary">Choose your institutional role to open the verified portal.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1: Administrator */}
              <div
                onClick={() => handleSelectRole('admin')}
                className="group relative bg-white rounded-2xl p-7 border border-ink-border hover:border-forest/50 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="w-14 h-14 rounded-2xl bg-forest-50 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                    {roleCardConfig.admin.icon}
                  </div>
                  <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-forest-100 text-forest mb-3">
                    Institutional Control
                  </div>
                  <h3 className="text-xl font-bold text-ink-primary mb-2 group-hover:text-forest transition-colors">
                    {roleCardConfig.admin.title}
                  </h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    {roleCardConfig.admin.desc}
                  </p>
                </div>
                <div className="mt-8 pt-4 border-t border-ink-border/60">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectRole('admin')
                    }}
                    className="w-full btn-primary py-2.5 text-sm flex items-center justify-center gap-2"
                  >
                    <span>{roleCardConfig.admin.buttonText}</span>
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>

              {/* Card 2: Teacher */}
              <div
                onClick={() => handleSelectRole('teacher')}
                className="group relative bg-white rounded-2xl p-7 border border-ink-border hover:border-forest/50 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="w-14 h-14 rounded-2xl bg-forest-50 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                    {roleCardConfig.teacher.icon}
                  </div>
                  <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 mb-3">
                    Faculty & Registers
                  </div>
                  <h3 className="text-xl font-bold text-ink-primary mb-2 group-hover:text-forest transition-colors">
                    {roleCardConfig.teacher.title}
                  </h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    {roleCardConfig.teacher.desc}
                  </p>
                </div>
                <div className="mt-8 pt-4 border-t border-ink-border/60">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectRole('teacher')
                    }}
                    className="w-full btn-primary py-2.5 text-sm flex items-center justify-center gap-2"
                  >
                    <span>{roleCardConfig.teacher.buttonText}</span>
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>

              {/* Card 3: Student */}
              <div
                onClick={() => handleSelectRole('student')}
                className="group relative bg-white rounded-2xl p-7 border border-ink-border hover:border-forest/50 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="w-14 h-14 rounded-2xl bg-forest-50 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                    {roleCardConfig.student.icon}
                  </div>
                  <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-light text-cyan-900 mb-3">
                    Attendance Portal
                  </div>
                  <h3 className="text-xl font-bold text-ink-primary mb-2 group-hover:text-forest transition-colors">
                    {roleCardConfig.student.title}
                  </h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    {roleCardConfig.student.desc}
                  </p>
                </div>
                <div className="mt-8 pt-4 border-t border-ink-border/60">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectRole('student')
                    }}
                    className="w-full btn-primary py-2.5 text-sm flex items-center justify-center gap-2"
                  >
                    <span>{roleCardConfig.student.buttonText}</span>
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* ROLE-SPECIFIC LOGIN FORM VIEW */
          <div className="max-w-md mx-auto">
            <button
              type="button"
              onClick={handleBackToRoles}
              className="inline-flex items-center gap-2 text-sm font-medium text-ink-secondary hover:text-ink-primary mb-6 transition-colors"
            >
              <ArrowLeft size={16} />
              <span>Back to Role Selection</span>
            </button>

            <div className="card">
              {/* Card Title & Icon */}
              <div className="flex items-center gap-4 pb-5 mb-5 border-b border-ink-border">
                <div className="w-12 h-12 rounded-xl bg-forest-50 flex items-center justify-center">
                  {roleCardConfig[selectedRole].icon}
                </div>
                <div>
                  <div className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-forest-100 text-forest mb-1">
                    {roleCardConfig[selectedRole].subtitle}
                  </div>
                  <h2 className="text-xl font-bold text-ink-primary">
                    {roleCardConfig[selectedRole].title} Login
                  </h2>
                </div>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
                <div>
                  <label className="label" htmlFor="username">
                    {roleCardConfig[selectedRole].identifierLabel}
                  </label>
                  <input
                    id="username"
                    type="text"
                    autoComplete="username"
                    className={`input ${errors.username ? 'input-error' : ''}`}
                    placeholder={roleCardConfig[selectedRole].identifierPlaceholder}
                    {...register('username')}
                  />
                  {errors.username && (
                    <p className="mt-1.5 text-xs text-status-absent">{errors.username.message}</p>
                  )}
                </div>

                <div>
                  <label className="label" htmlFor="password">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      className={`input pr-10 ${errors.password ? 'input-error' : ''}`}
                      placeholder="Enter your account password"
                      {...register('password')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-secondary hover:text-ink-primary transition-colors"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="mt-1.5 text-xs text-status-absent">{errors.password.message}</p>
                  )}
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full btn-primary py-3 text-sm font-semibold flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Spinner size="sm" />
                        <span>Verifying {roleCardConfig[selectedRole].title} Credentials...</span>
                      </>
                    ) : (
                      <>
                        <Lock size={16} />
                        <span>Sign In as {roleCardConfig[selectedRole].title}</span>
                      </>
                    )}
                  </button>
                </div>
              </form>

              {/* Dev hint / credentials reminder */}
              <div className="mt-6 pt-4 border-t border-ink-border text-center">
                <p className="text-xs text-ink-secondary">
                  Default credentials: <br />
                  <span className="font-mono text-ink-primary">
                    {selectedRole === 'admin' && 'admin / Admin@SecurePass123'}
                    {selectedRole === 'teacher' && 'dr.sharma / Lecturer@123'}
                    {selectedRole === 'student' && '1cs21cs001 / Student@123'}
                  </span>
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-ink-secondary max-w-4xl mx-auto w-full pt-6 border-t border-ink-border/50">
        <p>Smart College Attendance Management System &copy; {new Date().getFullYear()} — Institutional Attendance Engine</p>
      </div>
    </div>
  )
}
