interface SectionLabelProps {
  children: React.ReactNode
  className?: string
}

export function SectionLabel({ children, className = '' }: SectionLabelProps) {
  return (
    <div className={`text-[8px] font-bold text-teal uppercase tracking-[1.2px] mb-1.5 ${className}`}>
      {children}
    </div>
  )
}
