# User Guide — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04

---

## Getting Started

### Login
Navigate to the app URL. Use demo credentials or Azure AD SSO.

| Role | Email | Password |
|---|---|---|
| Admin | admin@variance-agent.dev | password123 |
| Analyst | analyst@variance-agent.dev | password123 |
| Director | director@variance-agent.dev | password123 |
| CFO | cfo@variance-agent.dev | password123 |
| BU Leader | bu.leader@variance-agent.dev | password123 |
| Board | board@variance-agent.dev | password123 |

### Navigation
Tabs visible depend on your role. CFO/Director see "Exec Summary" first. Analysts see full navigation.

### Global Filters
Available on every page in the context strip:
- **Period selector** — dropdown to switch months (Jun 2026, May 2026, etc.)
- **View type** — MTD / QTD / YTD
- **Comparison base** — Budget / Forecast / Prior Year
- **Persona pills** — Analyst / Director / CFO / BU Lead

---

## Executive Summary (CFO/Director/Board)
Your landing page. Tells the financial story at a glance.
- **Headline** — one-sentence period summary
- **KPI Cards** — Revenue, EBITDA, Gross Profit, Net Income
- **Section Cards** — Revenue narrative + Cost narrative with colored driver pills
- **Profitability** — circular margin gauges + narrative
- **Risk Items** — netting alerts + trending variances
- **Full Narrative** — 3-paragraph CFO-ready story
- **Downloads** — Board Deck (PPTX) + Executive Flash (PDF)

## Dashboard (All Users)
Operational view with charts, tables, and alerts. Click any variance row for detail modal with decomposition, hypotheses, and narrative.

## P&L View (All Users)
Hierarchical P&L with expand/collapse. Calculated rows auto-computed. Margin gauges. Narrative panel shows AI commentary at your persona's level.

## Chat (All Users)
Ask questions in natural language. Examples: "How did revenue perform?", "Show the waterfall", "What's trending?" Agent streams response with data tables.

## Review Queue (Analysts)
Your work queue. AI-drafted narratives sorted by impact. Edit text, provide hypothesis feedback (thumbs up/down), approve. Soft locking prevents concurrent edits. Edited narratives auto-cascade to parent summaries.

## Approval Queue (Directors/CFO)
Approve analyst-reviewed narratives. Bulk approve by analyst. "Regenerate Summary" button refreshes parents from approved children. Only approved content enters reports.

## Reports (All Users)
Generate XLSX, PDF, PPTX, DOCX. All pull from narrative pyramid (approved content only in reports). Schedule automated generation.

## Admin (Admin Only)
- **Thresholds** — edit materiality thresholds (persisted to YAML)
- **Model Routing** — configure LLM models per task
- **Users & Roles** — create/edit/deactivate users, assign roles
- **Audit Log** — searchable trail of all actions
- **Engine Control** — run variance analysis + narrative generation [Phase 3]

## Dark / Light Theme
Toggle via sun/moon icon in header. Persists across sessions.
