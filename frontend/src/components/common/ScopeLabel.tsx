interface ScopeLabelProps {
  label: string
}

export function ScopeLabel({ label }: ScopeLabelProps) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[7px] font-medium text-tx-tertiary border border-border">
      {label}
    </span>
  )
}
