import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <p className="text-8xl font-bold text-primary-200">404</p>
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-2xl my-4">
          <Search size={28} className="text-primary-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Page not found</h1>
        <p className="text-gray-500 mt-2">The page you're looking for doesn't exist.</p>
        <button className="btn-primary mt-6" onClick={() => navigate('/')}>Go Home</button>
      </div>
    </div>
  )
}
