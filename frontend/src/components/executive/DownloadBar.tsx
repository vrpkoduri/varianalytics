/**
 * Report download buttons for the Executive Summary page.
 */

export function DownloadBar() {
  return (
    <div className="glass-card p-4">
      <span className="section-label">EXPORT</span>
      <div className="flex gap-3 mt-3">
        <button
          className="flex-1 py-2.5 rounded-lg text-[11px] font-medium text-white transition-all hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--accent))' }}
          onClick={() => window.open('/api/reports/generate?format=pptx', '_blank')}
        >
          Download Board Deck (PPTX)
        </button>
        <button
          className="flex-1 py-2.5 rounded-lg text-[11px] font-medium text-white transition-all hover:opacity-90"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--cobalt))' }}
          onClick={() => window.open('/api/reports/generate?format=pdf', '_blank')}
        >
          Download Executive Flash (PDF)
        </button>
      </div>
    </div>
  );
}
