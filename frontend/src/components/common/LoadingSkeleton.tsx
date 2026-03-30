interface SkeletonProps {
  width?: string
  height?: string
  rounded?: boolean
  className?: string
}

export function LoadingSkeleton({ width = '100%', height = '16px', rounded = true, className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-shimmer ${rounded ? 'rounded-lg' : ''} ${className}`}
      style={{
        width, height,
        background: 'linear-gradient(90deg, var(--card) 25%, var(--card-alt) 50%, var(--card) 75%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}
