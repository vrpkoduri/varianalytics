/**
 * Audit log viewer tab.
 * Searchable, filterable, paginated audit trail.
 */

import { useCallback, useEffect, useState } from 'react'
import { api, buildParams } from '@/utils/api'

interface AuditEntry {
  auditId: string
  eventType: string
  userId: string
  service: string
  action: string
  details: Record<string, unknown>
  ipAddress: string | null
  timestamp: string
}

export function AdminAuditLogTab() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [eventFilter, setEventFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params = buildParams({
        page,
        page_size: 50,
        event_type: eventFilter || undefined,
        user: userFilter || undefined,
      })
      const data = await api.gateway.get<{
        entries: AuditEntry[]
        total: number
      }>(`/admin/audit-log${params}`)
      setEntries(data.entries || [])
      setTotal(data.total || 0)
    } catch {
      // fallback
    } finally {
      setLoading(false)
    }
  }, [page, eventFilter, userFilter])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const EVENT_TYPES = [
    '', 'auth', 'review_action', 'engine_run', 'llm_call',
    'config_change', 'data_access', 'role_assignment',
  ]

  return (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="section-label">AUDIT LOG</span>
        <span className="text-[9px] text-text-secondary">{total} total entries</span>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <select
          value={eventFilter}
          onChange={(e) => { setEventFilter(e.target.value); setPage(1) }}
          className="px-2 py-1 rounded bg-surface border border-border text-text text-[10px] focus:outline-none focus:ring-1 focus:ring-accent/50"
        >
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>{t || 'All events'}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filter by user..."
          value={userFilter}
          onChange={(e) => { setUserFilter(e.target.value); setPage(1) }}
          className="px-2 py-1 rounded bg-surface border border-border text-text text-[10px] flex-1 focus:outline-none focus:ring-1 focus:ring-accent/50"
        />
      </div>

      {/* Log entries */}
      {loading ? (
        <div className="text-center py-8 text-text-secondary text-[11px]">Loading audit log...</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-8 text-text-secondary text-[11px]">
          No audit entries found. Events will appear here as users interact with the system.
        </div>
      ) : (
        <div className="space-y-1">
          {entries.map((entry) => (
            <div
              key={entry.auditId}
              onClick={() => setSelectedEntry(entry)}
              className="flex items-center gap-3 p-2 rounded-lg bg-surface/30 border border-border/20 hover:border-accent/20 cursor-pointer transition-colors text-[10px]"
            >
              <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono text-[8px] shrink-0">
                {entry.eventType}
              </span>
              <span className="text-text-secondary shrink-0">{entry.service}</span>
              <span className="text-text flex-1 truncate">{entry.action}</span>
              <span className="text-text-secondary shrink-0">
                {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-2 py-1 rounded text-[10px] text-text-secondary border border-border hover:bg-surface disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-[10px] text-text-secondary py-1">
            Page {page} of {Math.ceil(total / 50)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 50)}
            className="px-2 py-1 rounded text-[10px] text-text-secondary border border-border hover:bg-surface disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}

      {/* Detail modal */}
      {selectedEntry && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50"
          onClick={() => setSelectedEntry(null)}
        >
          <div
            className="w-full max-w-lg p-4 rounded-2xl border border-border/30 max-h-[80vh] overflow-auto"
            style={{ background: 'var(--card)', backdropFilter: 'blur(16px)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[12px] font-semibold text-text">Audit Entry Detail</span>
              <button onClick={() => setSelectedEntry(null)} className="text-text-secondary hover:text-text text-[14px]">
                &#10005;
              </button>
            </div>
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between"><span className="text-text-secondary">ID:</span><span className="text-text font-mono">{selectedEntry.auditId}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">Event:</span><span className="text-accent">{selectedEntry.eventType}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">User:</span><span className="text-text">{selectedEntry.userId}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">Service:</span><span className="text-text">{selectedEntry.service}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">Action:</span><span className="text-text">{selectedEntry.action}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">IP:</span><span className="text-text">{selectedEntry.ipAddress || 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-text-secondary">Time:</span><span className="text-text">{new Date(selectedEntry.timestamp).toLocaleString()}</span></div>
              <div className="mt-2">
                <span className="text-text-secondary">Details:</span>
                <pre className="mt-1 p-2 rounded bg-surface border border-border text-[9px] text-text overflow-auto max-h-[200px]">
                  {JSON.stringify(selectedEntry.details, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
