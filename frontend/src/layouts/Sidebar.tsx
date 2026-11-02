import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import {
  LayoutDashboard, Users, GraduationCap, BookOpen, Building2,
  CalendarCheck, FileText, Settings, LogOut, ClipboardList,
  UserSquare2, Link2, AlertCircle, BarChart3, Upload, FileUp,
} from 'lucide-react'
import type { UserRole } from '../types'

interface NavItem { label: string; to: string; icon: React.ReactNode }

function adminNav(): NavItem[] {
  return [
    { label: 'Dashboard',         to: '/admin',                   icon: <LayoutDashboard size={18} /> },
    { label: 'Students',          to: '/admin/students',          icon: <GraduationCap size={18} /> },
    { label: 'Teachers',          to: '/admin/lecturers',         icon: <UserSquare2 size={18} /> },
    { label: 'Departments',       to: '/admin/departments',       icon: <Building2 size={18} /> },
    { label: 'Classes',           to: '/admin/classes',           icon: <Users size={18} /> },
    { label: 'Subjects',          to: '/admin/subjects',          icon: <BookOpen size={18} /> },
    { label: 'Assignments',       to: '/admin/assignments',       icon: <Link2 size={18} /> },
    { label: 'PDF Roster Import', to: '/admin/roster-import',     icon: <FileUp size={18} /> },
    { label: 'Sessions',          to: '/admin/sessions',          icon: <CalendarCheck size={18} /> },
    { label: 'Reports',           to: '/admin/reports',           icon: <BarChart3 size={18} /> },
    { label: 'Audit Logs',        to: '/admin/audit',             icon: <AlertCircle size={18} /> },
    { label: 'Settings',          to: '/admin/settings',          icon: <Settings size={18} /> },
  ]
}

function lecturerNav(): NavItem[] {
  return [
    { label: 'Dashboard',         to: '/lecturer',                icon: <LayoutDashboard size={18} /> },
    { label: 'My Assignments',    to: '/lecturer/assignments',    icon: <BookOpen size={18} /> },
    { label: 'Take Attendance',   to: '/lecturer/attendance/new', icon: <CalendarCheck size={18} /> },
    { label: 'Sessions',          to: '/lecturer/sessions',       icon: <ClipboardList size={18} /> },
    { label: 'Upload Register',   to: '/lecturer/ocr/upload',     icon: <Upload size={18} /> },
    { label: 'Reports',           to: '/lecturer/reports',        icon: <BarChart3 size={18} /> },
  ]
}

function studentNav(): NavItem[] {
  return [
    { label: 'Dashboard',         to: '/student',                 icon: <LayoutDashboard size={18} /> },
    { label: 'My Attendance',     to: '/student/attendance',      icon: <CalendarCheck size={18} /> },
    { label: 'Reports',           to: '/student/report',          icon: <FileText size={18} /> },
  ]
}

function navByRole(role: UserRole): NavItem[] {
  if (role === 'admin') return adminNav()
  if (role === 'lecturer') return lecturerNav()
  return studentNav()
}

export function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null
  const nav = navByRole(user.role)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 min-h-screen bg-white border-r border-gray-200 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <GraduationCap size={18} className="text-white" />
          </div>
          <span className="font-bold text-gray-900 text-sm leading-tight">Smart Attendance</span>
        </div>
      </div>

      {/* User info */}
      <div className="px-4 py-4 border-b border-gray-100">
        <p className="text-sm font-medium text-gray-900 truncate">{user.username}</p>
        <span className="badge badge-blue capitalize">{user.role}</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to.split('/').length <= 2}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-3 border-t border-gray-200">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
