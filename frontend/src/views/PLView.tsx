export default function PLView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          P&L View
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Full income statement with expandable hierarchy rows, inline variance
          columns, conditional formatting, and drill-down to account-level
          decomposition. Supports MTD/QTD/YTD views with Budget, Forecast, and
          Prior Year comparison bases.
        </p>
      </div>
    </div>
  );
}
