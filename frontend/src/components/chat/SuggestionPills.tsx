interface SuggestionPillsProps {
  pills: string[]
  onSelect: (text: string) => void
}

export function SuggestionPills({ pills, onSelect }: SuggestionPillsProps) {
  return (
    <div className="flex flex-wrap gap-1.5 justify-center">
      {pills.map((pill) => (
        <button
          key={pill}
          onClick={() => onSelect(pill)}
          className="px-3 py-1.5 text-[9px] rounded-full border border-border bg-card text-tx-secondary font-medium cursor-pointer transition-all hover:border-teal hover:text-teal hover:bg-[rgba(0,168,199,.06)]"
        >
          {pill}
        </button>
      ))}
    </div>
  )
}
