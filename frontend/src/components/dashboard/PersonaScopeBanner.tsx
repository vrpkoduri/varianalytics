import { cn } from '@/utils/theme'

interface PersonaScopeBannerProps {
  type: 'bu' | 'cfo'
  buName?: string
  approvedCount?: number
  totalCount?: number
}

export function PersonaScopeBanner({ type, buName, approvedCount, totalCount }: PersonaScopeBannerProps) {
  const isBU = type === 'bu'

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-button text-[10px] animate-fade-up',
        isBU
          ? 'border border-persian/30 bg-[rgba(1,109,158,.06)] text-persian'
          : 'border border-emerald/30 bg-emerald-surface text-emerald',
      )}
    >
      <span className="font-semibold">
        {isBU
          ? `Scope: ${buName ?? 'Your BU'} only`
          : `${approvedCount ?? 0} of ${totalCount ?? 0} variances approved for distribution`}
      </span>
    </div>
  )
}
