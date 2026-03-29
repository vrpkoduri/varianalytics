export default function DashboardView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          Variance Dashboard
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Executive summary of material variances with KPI cards, waterfall charts,
          top variance tables, and heat maps. Displays real-time review status and
          materiality indicators across all business units.
        </p>
      </div>

      {/* Placeholder KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {['Total Variances', 'Material', 'Favorable', 'Pending Review'].map(
          (label) => (
            <div
              key={label}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4"
            >
              <p className="text-sm text-[var(--color-text-muted)]">{label}</p>
              <p className="mt-1 text-2xl font-semibold text-[var(--color-text-primary)]">
                --
              </p>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
