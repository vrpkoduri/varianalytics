export default function AdminView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          Administration
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          System administration panel for threshold configuration (YAML),
          model routing, persona management, hierarchy maintenance,
          audit log viewer, and engine run controls.
        </p>
      </div>
    </div>
  );
}
