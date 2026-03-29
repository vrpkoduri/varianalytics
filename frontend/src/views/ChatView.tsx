export default function ChatView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          AI Chat
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Conversational interface for variance analysis powered by SSE streaming.
          Supports natural language queries, inline data tables, mini charts,
          drill-down suggestions, and review-status-aware responses. Persona-aware
          narrative depth adapts to the viewer role.
        </p>
      </div>
    </div>
  );
}
