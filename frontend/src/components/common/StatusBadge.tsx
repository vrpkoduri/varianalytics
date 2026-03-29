import { ReviewStatus } from '@/types/index';
import { cn } from '@/utils/theme';

interface StatusBadgeProps {
  status: ReviewStatus;
  className?: string;
}

const STATUS_STYLES: Record<ReviewStatus, string> = {
  [ReviewStatus.AI_DRAFT]:
    'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  [ReviewStatus.ANALYST_REVIEWED]:
    'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  [ReviewStatus.APPROVED]:
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  [ReviewStatus.ESCALATED]:
    'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  [ReviewStatus.DISMISSED]:
    'bg-gray-100 text-gray-600 dark:bg-gray-800/30 dark:text-gray-400',
  [ReviewStatus.AUTO_CLOSED]:
    'bg-gray-100 text-gray-500 dark:bg-gray-800/30 dark:text-gray-500',
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
