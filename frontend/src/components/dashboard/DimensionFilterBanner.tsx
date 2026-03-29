interface DimensionFilter {
  dimension: string
  value: string
}

interface DimensionFilterBannerProps {
  filter: DimensionFilter
  onClear: () => void
}

export function DimensionFilterBanner({ filter, onClear }: DimensionFilterBannerProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-button border border-teal/30 bg-[rgba(0,168,199,.06)] text-[10px] text-teal animate-fade-up">
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
      </svg>
      <span>
        Filtered: <span className="font-semibold">{filter.dimension}</span> = {filter.value}
      </span>
      <button
        onClick={onClear}
        className="ml-auto text-teal hover:text-teal-light transition-colors"
      >
        Clear
      </button>
    </div>
  )
}
