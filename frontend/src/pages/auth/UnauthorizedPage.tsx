import { useNavigate } from 'react-router-dom'
import { ShieldOff } from 'lucide-react'
import { useAuth } from '../../features/auth/AuthContext'

export default function UnauthorizedPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-red-100 rounded-2xl mb-6">
          <ShieldOff size={40} className="text-red-500" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Access Denied</h1>
        <p className="text-gray-500 mt-3">
          You don't have permission to view this page.
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <button className="btn-secondary" onClick={() => navigate(-1)}>Go Back</button>
          <button className="btn-primary" onClick={() => navigate(
            user?.role === 'admin' ? '/admin' : user?.role === 'lecturer' ? '/lecturer' : '/student'
          )}>Dashboard</button>
        </div>
      </div>
    </div>
  )
}
