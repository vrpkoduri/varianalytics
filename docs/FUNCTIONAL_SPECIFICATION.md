# Functional Specification — Marsh Vantage

**FP&A Variance Analysis Platform**
**Version:** 1.0 | **Last Updated:** 2026-04-01

---

## 1. Application Overview

Marsh Vantage is an AI-powered platform that automatically detects material variances across the P&L, generates root-cause narratives, and routes them through a review/approval workflow before distribution to leadership.

**Core flow:** Engine computes variances → AI generates narratives → Analysts review → Directors approve → Reports distributed

---

## 2. Persona Journeys — What Each Role Does & Gets

### 2.1 Analyst (FP&A / Financial Planning & Analysis)

**Job function:** Investigate variances, draft commentary, explain root causes to leadership.

**Daily workflow in Vantage:**
1. **Open Dashboard** → see which variances are material this period, scan KPI cards for revenue/cost misses
2. **Click into variance table** → sort by impact, identify the top 5 variances needing attention
3. **Open detail modal** → read AI-generated hypothesis, check decomposition (was it volume? price? FX?), review the 6-period trend
4. **Navigate to Review queue** → AI has pre-drafted narratives for all 4,400+ material variances. Edit the text, refine the root cause, give thumbs-up/down on hypotheses
5. **Mark reviewed** → sends to Director for approval
6. **Ask the Chat agent** → "Why is APAC consulting revenue down?" → gets a streamed response with data tables

**Value:** Saves 10-15 hours per close cycle by automating variance detection and narrative first-drafts. Analyst focuses on judgment calls, not data gathering.

---

### 2.2 Director (Finance Director / VP Finance)

**Job function:** Approve analyst commentary, ensure narrative quality, gate report distribution.

**Daily workflow in Vantage:**
1. **Open Dashboard** → quick scan of enterprise-level KPIs. Only sees REVIEWED + APPROVED items (no raw drafts).
2. **Navigate to Approval queue** → items grouped by analyst. See who has reviewed what.
3. **Review narratives** → read analyst-edited commentary. Check if root cause is plausible. Preview how it reads at midlevel.
4. **Approve or Hold** → Approve sends to APPROVED (eligible for reports). Hold sends back for revision.
5. **Bulk approve** → "Approve all from Sarah Chen" button for trusted analysts
6. **Check Chat** → "What are the risk items for the board?" → get a targeted summary

**Value:** Reduces approval bottleneck from days to hours. Ensures only quality-checked narratives reach leadership. Synthesis auto-generates parent summaries from approved children.

---

### 2.3 CFO (Chief Financial Officer)

**Job function:** Understand the financial story at summary level. Focus on what matters — approved, vetted insights only.

**Workflow in Vantage:**
1. **Open Dashboard** → sees only APPROVED variances. Summary-level narratives (not analyst detail).
2. **P&L View** → full P&L with margin gauges. Expand any line to see the approved narrative.
3. **Approval queue** → can approve or hold if Director escalates. Final authority.
4. **Reports** → generate Board-ready PDF/PPTX with only approved content. The report gate ensures nothing unapproved leaks into board materials.
5. **Chat** → "Summarize revenue performance for the board" → gets a CFO-appropriate summary

**Value:** Confidence that every number in the board deck has been reviewed and approved. No surprises. Single source of truth for the financial narrative.

---

### 2.4 BU Leader (Business Unit Head)

**Job function:** Understand own BU's variance picture. Cannot see other BUs.

**Workflow in Vantage:**
1. **Open Dashboard** → automatically scoped to own BU (e.g., Marsh only). KPIs, waterfall, heatmap show BU-specific data.
2. **P&L View** → BU-level P&L with midlevel narratives
3. **Chat** → "How did Marsh consulting perform this quarter?" → scoped response
4. **Reports** → download BU-specific reports

**Value:** Self-serve visibility into own BU without waiting for FP&A. Midlevel narratives written for a BU audience, not the full enterprise detail.

**Restriction:** Cannot see other BUs' data. Sidebar BU selector is disabled/filtered.

---

### 2.5 HR Finance (Headcount / Compensation Specialist)

**Job function:** Analyze headcount-related cost variances only.

**Workflow in Vantage:**
1. **Dashboard** → filtered to HC domain accounts (Salaries & Wages, Employee Benefits, Contractor Costs, Training & Development, Recruitment)
2. **Review queue** → only HC-domain variances to review. Same edit/approve workflow as analyst.
3. **Chat** → "Why are contractor costs up 12% in EMEA?" → domain-scoped response

**Value:** Focus on their domain without noise from revenue or other OpEx categories.

---

### 2.6 Board Viewer (Board Member / Non-Executive Director)

**Job function:** Consume the final financial narrative. Read-only, highest-level view.

**Workflow in Vantage:**
1. **Dashboard** → sees only APPROVED variances at board + summary narrative level
2. **Reports** → download Board Narrative (DOCX) or Executive Flash (PDF)

**Value:** Single page with the approved financial story. No need to understand the detail — the narrative has been through analyst review and director approval.

**Restriction:** Cannot access Review, Approval, Chat, P&L, or Admin. Most restricted persona.

---

### 2.7 Admin (System Administrator)

**Job function:** Configure the platform, manage users, monitor system health.

**Workflow in Vantage:**
1. **All pages accessible** — full analyst view plus Admin panel
2. **Admin → Thresholds** → adjust materiality thresholds (what counts as "material"). Changes persisted to YAML, affect next engine run.
3. **Admin → Model Routing** → swap LLM models (Claude Sonnet ↔ GPT-4o), adjust temperature/tokens
4. **Admin → Users & Roles** → create accounts, assign roles (analyst/director/cfo/etc.), set BU scope
5. **Admin → Audit Log** → investigate who did what, when. Search by user, event type, date range.

**Value:** Full control over the platform without code changes. Threshold tuning, model selection, and user provisioning from the UI.

---

### 2.8 Who Sees What (Summary)


| | Dashboard | P&L | Chat | Review | Approval | Reports | Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Analyst** | ✅ | ✅ | ✅ | ✅ | - | ✅ | - |
| **BU Leader** | ✅ own BU | ✅ own BU | ✅ | - | - | ✅ own BU | - |
| **Director** | ✅ | ✅ | ✅ | - | ✅ | ✅ | - |
| **CFO** | ✅ | ✅ | ✅ | - | ✅ | ✅ | - |
| **HR Finance** | ✅ HC only | ✅ HC only | ✅ | ✅ HC only | - | - | - |
| **Board Viewer** | ✅ | - | - | - | - | ✅ | - |
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.2 Data Filtering by Persona

| Persona | Variance Statuses | Narrative Level | BU Scope | Account Scope |
|---------|------------------|-----------------|----------|---------------|
| Analyst | All (Draft, Reviewed, Approved, Escalated, Dismissed) | Detail | All BUs | All accounts |
| BU Leader | Reviewed + Approved only | Midlevel | Own BU only | All accounts |
| Director | Reviewed + Approved only | Midlevel | All BUs | All accounts |
| CFO | Approved only | Summary | All BUs | All accounts |
| HR Finance | Draft + Reviewed + Approved | Detail | All BUs | HC domain only* |
| Board Viewer | Approved only | Board + Summary | All BUs | All accounts |

*HC domain: Salaries & Wages, Employee Benefits, Contractor Costs, Training & Development, Recruitment, Headcount

---

## 3. Global Filters

Available on every page. Applied to all data queries.

| Filter | Options | Default | Effect |
|--------|---------|---------|--------|
| **Business Unit** | Marsh, Mercer, Guy Carpenter, Oliver Wyman, MMC Corporate, All | All | Scopes all data to selected BU |
| **View Type** | MTD, QTD, YTD | MTD | Changes time aggregation window |
| **Comparison Base** | Budget, Forecast, Prior Year | Budget | Changes the comparator for variance calculation |
| **Period** | 2024-01 through 2026-12 | Latest closed | Sets the analysis period |
| **Dimension** | Geography / Segment / LOB / Cost Center tree nodes | None | Filters data to selected hierarchy node |

**Propagation:** Changing any filter re-fetches all data on the current page. Filters persist across page navigation within the same session.

---

## 4. Pages & Sections

### 4.1 Login Page (`/login`)

**Purpose:** Authenticate users before accessing the platform.

| Element | Description |
|---------|-------------|
| **Email / Password form** | Dev mode local authentication |
| **"Sign in with Microsoft" button** | Azure AD SSO (shown when configured) |
| **Demo credentials panel** | Shows 6 demo accounts for testing |
| **Register toggle** | Create new account (dev mode only) |
| **Error display** | Shows invalid credentials / network errors |

**Background:** On submit, calls `POST /auth/login` → returns JWT pair (access + refresh). Token stored in memory, auto-refreshes 5 min before expiry.

---

### 4.2 Dashboard (`/`)

**Purpose:** Executive summary of variance analysis at a glance.

| Section | What It Shows | Interactive |
|---------|--------------|-------------|
| **KPI Cards** (top row) | Revenue, COGS, OpEx, Net Income — each with actual, comparator, variance $, variance %, 6-period sparkline | Click card → opens detail modal |
| **Success Metrics Bar** | Cycle time, coverage %, root cause %, commentary % | Read-only badges |
| **Executive Summary** | AI-generated 2-3 sentence narrative of key variances | Read-only |
| **Alert Cards** | Netting alerts (offsetting variances) + Trend alerts (consecutive-period patterns) | Click → opens detail |
| **Waterfall Chart** | Bridges from comparator to actual — shows which P&L lines drove the variance | Hover for values |
| **Heatmap** | 2D grid: rows = geographies, columns = accounts. Color intensity = variance magnitude (red = unfavorable, green = favorable) | Click cell → opens detail modal |
| **Variance Table** | Sortable, searchable table of all material variances. Columns: Account, BU, Variance $, %, Status, Type | Click row → opens detail modal. Sort by any column. Search by account name. |
| **Trend Chart** | 12-month trailing trend: actual vs budget with variance shaded area | Hover for period values |

**Background processes feeding this page:**
- `GET /dashboard/summary` → KPI cards
- `GET /dashboard/waterfall` → waterfall chart
- `GET /dashboard/heatmap` → heatmap grid
- `GET /dashboard/trends` → trend chart
- `GET /variances/?page_size=50` → variance table
- `GET /dashboard/alerts/netting` → netting alert cards
- `GET /dashboard/alerts/trends` → trend alert cards

---

### 4.3 P&L View (`/pl`)

**Purpose:** Full P&L statement with hierarchical expand/collapse and narrative panel.

| Section | What It Shows | Interactive |
|---------|--------------|-------------|
| **P&L Grid** | Hierarchical rows: Revenue → Gross Profit → OpEx → EBITDA → EBIT → EBT → Net Income. Columns: Actual, Comparator, Variance $, Variance % | Click parent row → expand/collapse children. Click leaf → opens detail modal. |
| **Calculated Rows** | Gross Profit, EBITDA, EBIT, EBT, Net Income — computed from children in dependency order | Auto-calculated, not editable |
| **Margin Gauges** | 5 circular gauges: Gross Margin, Operating Margin, EBITDA Margin, EBIT Margin, Net Margin | Read-only visualization |
| **Narrative Panel** | AI-generated commentary for selected row. Shows detail/midlevel/summary based on persona. | Read-only (editing in Review page) |

**Background:** `GET /pl/statement` returns nested tree. Calculated rows resolved server-side in dependency order (Gross Profit before EBITDA before Net Income).

---

### 4.4 Chat (`/chat`)

**Purpose:** Conversational AI agent for ad-hoc variance analysis questions.

| Element | Description |
|---------|-------------|
| **Message list** | Scrollable history of user messages and agent responses |
| **Chat input** | Text field with send button (Enter to send) |
| **Streaming response** | Agent response appears token-by-token via SSE |
| **Suggestion pills** | Quick-action buttons (e.g. "How did revenue perform?", "Show the P&L waterfall") |
| **Inline data tables** | Agent can embed variance tables in responses |
| **Variance callouts** | Highlighted boxes for specific variances discussed |
| **Netting alerts** | Inline warnings about offsetting variances |
| **Typing indicator** | Animated dots while agent is processing |

**How the agent works:**
1. User message → `POST /chat/messages`
2. Gateway classifies intent (revenue? P&L? trend? decomposition? review status?)
3. Routes to domain agent (RevenueAgent, PLAgent, ReviewAgent)
4. Agent calls computation service tools (summary, waterfall, drilldown, etc.)
5. Response streamed back as SSE events: `token`, `data_table`, `suggestion`, `done`
6. Frontend renders tokens in real-time

**Supported intents:** revenue overview, variance detail, P&L summary, waterfall, heatmap, trend, drill-down, decomposition, review status, netting, general

---

### 4.5 Review Queue (`/review`)

**Purpose:** Analysts review AI-generated narratives, edit text, provide hypothesis feedback.

| Section | What It Shows | Interactive |
|---------|--------------|-------------|
| **Progress Bar** | Segmented bar: Draft / Reviewed / Approved counts | Read-only |
| **Status Counters** | Cards: AI_DRAFT (pending), ANALYST_REVIEWED, ESCALATED, DISMISSED counts | Read-only |
| **Sort Bar** | Sort by: impact, SLA, period, edit date | Click to change sort |
| **Review List** | Expandable cards — collapsed shows account + variance + status. Expanded shows full detail. | Click to expand/collapse |
| **Narrative Editor** | Text area with the AI-generated narrative. Edit freely. | Type to edit |
| **Hypothesis Cards** | 3-5 AI-generated root cause hypotheses with confidence %. Thumbs up/down feedback. | Click thumbs up/down |
| **Action Buttons** | "Mark Reviewed", "Escalate", "Dismiss" | Click to change status |
| **Batch Actions** | Select multiple items → "Batch Mark Reviewed" | Checkbox + batch button |
| **SLA Badge** | Hours remaining in review SLA (48h target) | Read-only |

**Workflow states:**
```
AI_DRAFT → (edit/approve) → ANALYST_REVIEWED → (director_approve) → APPROVED
         → (escalate)     → ESCALATED       → (review again)     → ANALYST_REVIEWED
         → (dismiss)      → DISMISSED       → (reopen)           → AI_DRAFT
```

**Background:** `POST /review/actions` with action = edit | approve | escalate | dismiss. On edit, the edited narrative is stored alongside the original (diff tracked).

---

### 4.6 Approval Queue (`/approval`)

**Purpose:** Directors/CFO approve analyst-reviewed narratives before report distribution.

| Section | What It Shows | Interactive |
|---------|--------------|-------------|
| **Report Gate** | Banner: "{N} items ready for approval" with "Approve All" button | Click to bulk approve all |
| **Analyst Groups** | Items grouped by reviewing analyst. Each group has a header with analyst name + count. | Expand/collapse groups |
| **Approval Items** | Card per variance: account, variance $, synthesis status, narrative preview | Read-only preview |
| **Approve / Hold buttons** | Per item or per group | Click to approve or hold |
| **Bulk Approve** | "Approve All from {Analyst}" button per group | Approves entire group |

**What happens on approval:**
1. Status → APPROVED (terminal state)
2. Narrative stored in knowledge base (for future RAG retrieval)
3. Synthesis triggered: parent-level narratives auto-generated from approved children
4. Notification sent (Teams / Slack / Email)
5. Variance now eligible for report distribution

---

### 4.7 Reports (`/reports`)

**Purpose:** Generate, schedule, and download financial reports.

| Tab | What It Shows | Interactive |
|-----|--------------|-------------|
| **Reports** | History of generated reports with status (Ready, Processing, Failed), format, date | Download / Preview buttons |
| **Schedules** | Active report schedules: name, frequency (daily/weekly/monthly), next run, last run | Edit / Delete / Enable/Disable |
| **Templates** | Report template library: Executive Flash, Period-End, Board Narrative | "Generate" button, preview overlay |

**Report formats:**

| Format | Content |
|--------|---------|
| **XLSX** | Summary sheet + variance detail + per-BU tabs + full P&L. Marsh branding colors. |
| **PDF** | Executive Flash (1-page KPI summary) or Period-End (multi-page with variance tables, decomposition, hypotheses) |
| **PPTX** | 5 slides: Title → KPI Summary → Top Variances → Risk Items → Summary Narrative |
| **DOCX** | Board narrative: Financial Performance table + Executive Summary + Areas of Attention |

**Report gate:** Only APPROVED narratives are included in reports. Unapproved items are excluded.

**Scheduling:** Asyncio-based scheduler checks every 60 seconds for due schedules, triggers auto-generation, and distributes via configured channels.

---

### 4.8 Admin Panel (`/admin`)

**Purpose:** System configuration and user management. Admin-only.

| Tab | What It Configures | Persistence |
|-----|-------------------|-------------|
| **Thresholds** | Global absolute ($50K) and percentage (3%) thresholds. Domain overrides (Revenue: 2%, T&E: 5%). Close-week overrides. Role overrides (CFO: $100K/5%, Board: $500K/10%). Netting ratio (3x). Trend consecutive periods (3). | Written to `thresholds.yaml` |
| **Model Routing** | LLM model per task: narrative generation, intent classification, hypothesis generation, oneliner, embedding. Temperature and max_tokens per model. | Written to `model_routing.yaml` |
| **Users & Roles** | User list (name, email, roles, BU scope, status). Create / edit / deactivate users. Assign roles. 7 system roles: admin, analyst, bu_leader, director, cfo, hr_finance, board_viewer. | PostgreSQL |
| **Audit Log** | Searchable log of all system events: logins, review actions, config changes, engine runs, LLM calls. Filter by event type, user, service, date. Click for full JSON details. | PostgreSQL (read-only) |

---

## 5. Variance Detail Modal

**Triggered from:** Dashboard (click variance table row, heatmap cell, KPI card), P&L (click leaf row), Review (expand item), Approval (click item).

| Section | Content |
|---------|---------|
| **Header** | Account name, BU, geography, period, status badge |
| **Big Number** | Variance $ and % in large font. Green = favorable, red = unfavorable. |
| **Period Trend** | 6-period mini chart showing variance history with threshold line |
| **Decomposition** | Root cause breakdown — Revenue: Volume + Price + Mix + FX. COGS: Rate + Volume + Mix. OpEx: Rate + Volume + Timing + One-time. Shows % contribution of each driver. |
| **Correlations** | Related variances that moved together (pairwise correlation analysis) |
| **Hypotheses** | 3-5 AI-generated root cause hypotheses with confidence % and feedback buttons |
| **Narrative** | AI-generated commentary (level depends on persona). Editable in review mode. |
| **Actions** | Confirm / Confirm & Synthesize / Reject / Request Revision (context-dependent) |

---

## 6. Background Processes

### 6.1 Computation Engine (5.5-Pass Pipeline)

Runs on demand or on schedule. Processes 49K+ financial rows.

| Pass | What It Does | Output |
|------|-------------|--------|
| **1. Raw Variance** | Computes actual − comparator at every Account × BU × Geo × Period intersection. Rolls up hierarchy. Resolves calculated rows (Gross Profit, EBITDA, etc.) in dependency order. | 300K+ variance rows |
| **1.5 Netting** | Detects parent nodes that hide offsetting children. 4 checks: gross offset (gross > 3× net), dispersion (std dev > 10pp), directional split, cross-account. | Netting flags |
| **2.5 Trend** | Identifies multi-period patterns. Rule 1: 3+ consecutive same-direction periods. Rule 2: cumulative YTD breach. | Trend flags |
| **2. Threshold** | Filters to material variances using OR logic: exceeds $ threshold OR % threshold OR is netted OR is trending. Domain/role/close-week overrides apply. | 4,400+ material variances |
| **3. Decomposition** | Breaks each material variance into drivers. Revenue: Vol×Price×Mix×FX. COGS: Rate×Vol×Mix. OpEx: Rate×Vol×Timing×One-time. Fallback proportional split when unit data unavailable. | Decomposition components |
| **4. Correlation** | Pairwise scan of material variances. Batched LLM hypothesis generation for root cause. | Correlation pairs + hypotheses |
| **5. Narrative** | RAG-enhanced multi-level text: detail (analyst), midlevel (BU leader), summary (CFO), oneliner (dashboard), board (on-demand). Creates AI_DRAFT review entries. | 4,400+ narratives |

### 6.2 Synthesis (Post-Approval)

Triggered when an analyst approves a variance. Bottom-up: approved child narratives are synthesized into parent-level summaries automatically.

### 6.3 Knowledge Base Population

On approval, the narrative + context is embedded and stored in the vector database. Future narrative generation retrieves similar approved commentaries as few-shot examples (RAG). Weighted retrieval: 70% semantic similarity + 15% account match + 15% magnitude match.

### 6.4 Report Scheduling

Asyncio scheduler checks every 60 seconds. When a schedule is due, triggers report generation → storage → distribution via configured channels.

### 6.5 Notifications

| Event | Channels | Content |
|-------|----------|---------|
| Engine complete | Teams, Slack | "{N} material variances computed for {period}" |
| Review needed | Teams, Slack, Email | "{N} AI-drafted narratives ready for analyst review" |
| Approval needed | Teams, Slack | "{N} reviewed narratives pending director approval" |
| Report ready | Email | Report attached, download link |
| SLA warning | Teams | "Review SLA approaching for {N} items" |

---

## 7. Data Model (15 Tables)

| Table | Type | Purpose |
|-------|------|---------|
| `dim_hierarchy` | Dimension | Parent-child trees: Geography (26 nodes), Segment (13), LOB (13), Cost Center (20) |
| `dim_business_unit` | Dimension | 5 BUs: Marsh, Mercer, Guy Carpenter, Oliver Wyman, MMC Corporate |
| `dim_account` | Dimension | 36 accounts: 28 detail + 8 calculated rows. Includes calc formulas, variance signs, P&L categories |
| `dim_period` | Dimension | 36 months (2024-01 to 2026-12) with fiscal year/quarter/month flags |
| `dim_view` | Dimension | 3 views: MTD, QTD, YTD |
| `dim_comparison_base` | Dimension | 3 bases: Budget, Forecast, Prior Year |
| `fact_financials` | Base Fact | MTD atomic grain: actual, budget, forecast, prior_year, FX columns. ~49K rows |
| `fact_variance_material` | Computed | Material variances with flags (is_material, is_netted, is_trending). ~4,400 rows |
| `fact_decomposition` | Computed | Volume/Price/Mix/FX components per variance. ~2,600 rows |
| `fact_netting_flags` | Computed | Netting detection results. ~11 rows |
| `fact_trend_flags` | Computed | Trend detection results. ~9,700 rows |
| `fact_correlations` | Computed | Pairwise correlations with hypotheses. ~20 rows |
| `fact_review_status` | Workflow | AI_DRAFT → ANALYST_REVIEWED → APPROVED lifecycle. ~4,400 rows |
| `knowledge_commentary` | Knowledge | Approved narratives with embeddings for RAG retrieval |
| `audit_log` | Audit | Every engine run, LLM call, review action, config change, login |

**Auth tables (PostgreSQL):**

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, password_hash, Azure AD OID) |
| `roles` | 7 system roles with persona/narrative mapping |
| `user_roles` | User ↔ role assignments with BU scope |
| `permissions` | Fine-grained resource/action permissions per role |

---

## 8. API Endpoints (64 total)

### Gateway (35 endpoints, port 8000)

| Group | Endpoints | Auth |
|-------|-----------|------|
| **Auth** | login, login/azure-ad, register, logout, me, refresh, azure-ad/config | Public (login/register), Auth (others) |
| **Chat** | send message, stream SSE, list conversations, delete conversation | Any authenticated |
| **Dimensions** | hierarchies/{name}, business-units, accounts, periods | Any authenticated |
| **Config** | GET thresholds, PUT thresholds, GET model-routing | Read: any auth. Write: admin |
| **Review** | queue, actions, stats | Analyst + Admin |
| **Approval** | queue, bulk actions, stats | Director + CFO + Admin |
| **Admin** | users CRUD, roles list, role assign/remove, audit-log | Admin only |
| **Notifications** | test send, get/put config | Admin only |

### Computation (17 endpoints, port 8001)

| Group | Endpoints |
|-------|-----------|
| **Dashboard** | summary, waterfall, heatmap, trends, alerts/netting, alerts/trends |
| **Variances** | list, detail, by-account |
| **Drilldown** | by-node, decomposition, correlations, netting |
| **P&L** | statement, account detail |
| **Synthesis** | trigger, status |

### Reports (12 endpoints, port 8002)

| Group | Endpoints |
|-------|-----------|
| **Reports** | generate, templates, history, status, download |
| **Scheduling** | list, create, update, delete |
| **Distribution** | recipients, add recipient, send |
