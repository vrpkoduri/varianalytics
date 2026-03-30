import { cn } from '@/utils/theme'

interface ReviewCheckboxProps {
  checked: boolean
  onChange: () => void
}

export function ReviewCheckbox({ checked, onChange }: ReviewCheckboxProps) {
  return (
    <button
      type="button"
      className={cn(
        'w-[15px] h-[15px] rounded flex items-center justify-center shrink-0 transition-all duration-150',
        checked
          ? 'bg-teal border-teal text-white'
          : 'border-[1.5px] border-[var(--border-hover)] bg-[var(--card)]',
      )}
      onClick={(e) => {
        e.stopPropagation()
        onChange()
      }}
      aria-label={checked ? 'Deselect item' : 'Select item'}
    >
      {checked && (
        <span className="text-[9px] leading-none font-bold">{'\u2713'}</span>
      )}
    </button>
  )
}
