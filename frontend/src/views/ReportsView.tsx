export default function ReportsView() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-6">
        <h2 className="mb-2 text-lg font-semibold text-[var(--color-text-primary)]">
          Reports
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Export and distribution center for variance analysis reports. Supports
          Excel (.xlsx), PowerPoint (.pptx from template), PDF, and Word (.docx)
          formats. Includes scheduling and distribution list management with
          Teams/Slack/SMTP integration.
        </p>
      </div>
    </div>
  );
}
