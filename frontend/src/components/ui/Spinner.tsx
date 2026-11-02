interface Props { size?: 'sm' | 'md' | 'lg'; className?: string }

export function Spinner({ size = 'md', className = '' }: Props) {
  const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-10 w-10' }
  return (
    <div className={`animate-spin rounded-full border-b-2 border-primary-600 ${sizes[size]} ${className}`} />
  )
}
