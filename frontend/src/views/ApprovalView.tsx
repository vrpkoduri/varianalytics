export default function ApprovalView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          Approval Queue
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Director bulk approval interface. Only shows ANALYST_REVIEWED items.
          Report distribution gate ensures only APPROVED narratives are distributed.
          Supports escalation and dismissal workflows.
        </p>
      </div>
    </div>
  );
}
