import { ReviewStatus } from '@/types/index';
import { cn } from '@/utils/theme';

interface StatusBadgeProps {
  status: ReviewStatus;
  className?: string;
}

const STATUS_STYLES: Record<ReviewStatus, string> = {
  [ReviewStatus.AI_DRAFT]:
    'bg-teal/10 text-teal',
  [ReviewStatus.ANALYST_REVIEWED]:
    'bg-amber/10 text-amber',
  [ReviewStatus.APPROVED]:
    'bg-emerald/10 text-emerald',
  [ReviewStatus.ESCALATED]:
    'bg-coral/10 text-coral',
  [ReviewStatus.DISMISSED]:
    'bg-surface text-tx-tertiary',
  [ReviewStatus.AUTO_CLOSED]:
    'bg-surface text-tx-tertiary',
};

const STATUS_LABELS: Record<ReviewStatus, string> = {
  [ReviewStatus.AI_DRAFT]: 'AI Draft',
  [ReviewStatus.ANALYST_REVIEWED]: 'Reviewed',
  [ReviewStatus.APPROVED]: 'Approved',
  [ReviewStatus.ESCALATED]: 'Escalated',
  [ReviewStatus.DISMISSED]: 'Dismissed',
  [ReviewStatus.AUTO_CLOSED]: 'Auto-Closed',
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_STYLES[status],
        className,
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
