# User Guide — Marsh Vantage

**Version:** 1.0 | **Last Updated:** 2026-04-01

---

## Getting Started

### Login

Navigate to the application URL. You'll see the login page with Marsh Vantage branding.

**Dev Mode Credentials:**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@variance-agent.dev | password123 |
| Analyst | analyst@variance-agent.dev | password123 |
| BU Leader | bu.leader@variance-agent.dev | password123 |
| Director | director@variance-agent.dev | password123 |
| CFO | cfo@variance-agent.dev | password123 |
| Board Viewer | board@variance-agent.dev | password123 |

**Azure AD:** If configured, a "Sign in with Microsoft" button appears for SSO.

---

## Personas

Each persona sees different data and has access to different features:

| Persona | Sees | Narrative Level | Access |
|---------|------|----------------|--------|
| **Analyst** | All variances, all statuses | Detail | Dashboard, P&L, Chat, Review, Reports |
| **BU Leader** | Own BU only, reviewed + approved | Midlevel | Dashboard, P&L, Chat, Reports |
| **Director** | All BUs, reviewed + approved | Midlevel | Dashboard, P&L, Chat, Approvals, Reports |
| **CFO** | All BUs, approved only | Summary | Dashboard, P&L, Chat, Approvals, Reports |
| **HR Finance** | HC domain only | Detail | Dashboard, P&L, Chat, Review |
| **Board Viewer** | Approved only | Board + Summary | Dashboard, Reports |
| **Admin** | Everything | All levels | All pages + Admin panel |

---

## Dashboard

The dashboard is the primary landing page showing variance analysis at a glance.

### KPI Cards
Top row shows key financial metrics: Revenue, EBITDA, Total Costs, etc. Each card displays actual vs. comparator with variance amount and percentage.

### Waterfall Chart
Bridges from comparator (Budget/Forecast/PY) to actual, showing which accounts contributed positively or negatively.

### Heatmap
Geographic variance matrix — rows are geographies, columns are accounts. Color intensity shows variance magnitude. Red = unfavorable, green = favorable.

### Trend Chart
12-month trailing trend for the selected metric. Shows actual, budget, and variance over time.

### Variance Table
Sortable, filterable table of material variances. Click any row to open the detail modal with decomposition, narratives, and drill-down.

### Filters
- **Business Unit:** Filter all dashboard sections by BU
- **View Type:** MTD (month), QTD (quarter), YTD (year)
- **Comparison Base:** Budget, Forecast, or Prior Year
- **Sidebar:** Geography/Segment/LOB/Cost Center tree filters

---

## P&L View

Hierarchical profit and loss statement with expand/collapse.

- Click any row to expand into child accounts
- Leaf rows show a narrative panel with AI-generated commentary
- Toggle "CFO Preview" to see the summary-level narrative
- Columns: Actual, Comparator, Variance ($), Variance (%)

---

## Chat

AI-powered conversational interface for variance analysis.

### Example Questions
- "How did revenue perform this quarter?"
- "Show me the P&L waterfall"
- "What are the trending variances?"
- "Break down the revenue drivers"
- "Are there any netting offsets?"
- "What's pending in the review queue?"

### How It Works
Messages are sent to the AI agent which classifies intent, queries the computation engine, and streams back a response with embedded data tables and charts.

---

## Review Workflow

*Available to: Analysts, Admin*

### Review Queue
Landing page showing all AI-generated narratives awaiting review. Sort by impact, SLA, or period.

### Actions
- **Edit:** Modify the AI-generated narrative text. Status changes to ANALYST_REVIEWED.
- **Escalate:** Flag for senior attention. Status changes to ESCALATED.
- **Dismiss:** Mark as not requiring commentary. Status changes to DISMISSED.

### Hypothesis Feedback
Each variance may have AI-generated hypotheses for root cause. Use thumbs up/down to provide feedback — this improves future AI suggestions via the RAG knowledge base.

---

## Approval Workflow

*Available to: Directors, CFO, Admin*

### Approval Queue
Shows items that analysts have reviewed (status: ANALYST_REVIEWED). Only reviewed items appear here — the review gate ensures quality.

### Actions
- **Approve:** Move to APPROVED status. The variance is now eligible for report distribution.
- **Bulk Approve:** Select multiple items and approve in batch.

### Report Gate
Reports can only be generated from APPROVED narratives. This ensures CFO and board-level reports contain vetted content only.

---

## Reports

Generate and download financial reports in 4 formats:

| Format | Content |
|--------|---------|
| **XLSX** | Summary + variance detail + per-BU tabs + P&L |
| **PDF** | Executive flash (1-page) or period-end (multi-page) |
| **PPTX** | 5-slide deck with KPIs, variances, risk items |
| **DOCX** | Board narrative with financial performance + recommendations |

### Scheduling
Reports can be scheduled for automatic generation (daily, weekly, monthly) with distribution via Teams, Slack, or email.

---

## Admin Panel

*Available to: Admin only*

### Thresholds
Edit materiality thresholds that control which variances surface as material:
- **Global:** Absolute ($) and percentage (%) thresholds
- **Domain overrides:** Tighter/looser thresholds per P&L category
- **Close week:** Tighter thresholds during financial close
- **Role overrides:** Higher thresholds for CFO/Board views

### Model Routing
Configure which LLM models are used for each task (narrative generation, intent classification, hypothesis generation). Adjust temperature and max_tokens per model.

### Users & Roles
- Create, edit, and deactivate user accounts
- Assign roles (analyst, director, cfo, etc.) with BU scope
- View system roles and their permissions

### Audit Log
Searchable, filterable log of all system events: logins, review actions, config changes, engine runs, LLM calls. Click any entry for full details.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Escape | Close modal / dialog |
| Tab navigation | Move between dashboard sections |

---

## Dark / Light Theme

Toggle between dark (default) and light themes using the sun/moon icon in the header. Your preference is saved to localStorage and persists across sessions.
