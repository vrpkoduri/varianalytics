interface MarginGaugeProps {
  label: string
  value: number
  delta: string
  color: string
}

export function MarginGauge({ label, value, delta, color }: MarginGaugeProps) {
  const radius = 22
  const circumference = 2 * Math.PI * radius
  const progress = (value / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: 54, height: 54 }}>
        <svg
          width={54}
          height={54}
          viewBox="0 0 54 54"
          style={{ transform: 'rotate(-90deg)' }}
        >
          <circle
            cx={27}
            cy={27}
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth={3}
          />
          <circle
            cx={27}
            cy={27}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={3}
            strokeLinecap="round"
            strokeDasharray={`${progress} ${circumference}`}
          />
        </svg>
        <div
          className="absolute inset-0 flex items-center justify-center font-body text-[10px] font-bold"
          style={{ color }}
        >
          {value.toFixed(1)}%
        </div>
      </div>
      <div className="text-[7px] font-bold text-teal uppercase tracking-[0.6px]">
        {label}
      </div>
      <div className="text-[8px] font-semibold" style={{ color: 'var(--emerald)' }}>
        {delta}
      </div>
    </div>
  )
}
