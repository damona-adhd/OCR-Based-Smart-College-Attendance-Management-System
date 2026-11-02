interface Props { percentage: number; isShortage?: boolean }

export function AttendanceBadge({ percentage, isShortage }: Props) {
  const color = isShortage
    ? 'bg-red-100 text-red-700'
    : percentage >= 90
    ? 'bg-green-100 text-green-700'
    : 'bg-yellow-100 text-yellow-700'

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {percentage.toFixed(1)}%
      {isShortage && ' ⚠'}
    </span>
  )
}
