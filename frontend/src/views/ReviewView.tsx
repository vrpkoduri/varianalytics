export default function ReviewView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          Review Queue
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Analyst landing page for reviewing AI-generated variance narratives.
          Sort by impact, SLA indicators, batch actions. Includes NarrativeEditor
          with edit, diff, and hypothesis feedback (thumbs up/down). Supports
          transitions from AI_DRAFT to ANALYST_REVIEWED status.
        </p>
      </div>
    </div>
  );
}
