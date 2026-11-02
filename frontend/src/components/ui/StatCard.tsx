import React from 'react'

interface Props {
  label: string
  value: string | number
  icon?: React.ReactNode
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple'
  trend?: string
}

const colors = {
  blue:   'bg-blue-50 text-blue-600',
  green:  'bg-green-50 text-green-600',
  red:    'bg-red-50 text-red-600',
  yellow: 'bg-yellow-50 text-yellow-600',
  purple: 'bg-purple-50 text-purple-600',
}

export function StatCard({ label, value, icon, color = 'blue', trend }: Props) {
  return (
    <div className="card flex items-start gap-4">
      {icon && (
        <div className={`p-3 rounded-xl ${colors[color]}`}>
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-500 truncate">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        {trend && <p className="text-xs text-gray-400 mt-1">{trend}</p>}
      </div>
    </div>
  )
}
