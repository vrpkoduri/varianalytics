# Marsh Vantage — Production Design Specification

## For Claude Code: Build the React + FastAPI app to match this spec exactly.

Reference prototype: `FPA_Variance_Agent_UI.html` (136KB, single-file working prototype)
This document extracts every design decision from that prototype.

---

## 1. Design Tokens

### 1.1 Color System (Dark Theme — Default)

```
Backgrounds:
  --bg:    #030B1A     (page background)
  --sf:    #0A1628     (surface / sidebar)
  --cd:    #0F1D32     (card background — uses glassmorphism)
  --cd2:   #132440     (secondary card / hover tint)
  --bd:    #1A2A42     (border default)
  --bd2:   #243552     (border hover)

Text hierarchy:
  --tx:    #E8EDF5     (primary text)
  --t2:    #8B9AB5     (secondary text — narratives, descriptions)
  --t3:    #5A6B84     (tertiary text — labels, timestamps, hints)

Marsh brand chrome:
  --cb:    #002C77     (Marsh Cobalt — header, primary brand)
  --cbL:   #003A99     (Cobalt lighter)
  --tl:    #00A8C7     (Marsh Teal — accents, active states, section headers)
  --tlL:   #00BCDB     (Teal lighter)
  --mb:    #016D9E     (Medium Persian Blue — gradients)
  --ml:    #A7E2F0     (Blizzard Blue — light accents)

Data semantic colors (DO NOT use for chrome):
  --gd:    #E3A547     (Gold — materiality, edited badges)
  --gdS:   rgba(227,165,71,.1)
  --em:    #2DD4A8     (Emerald — favorable, approved, positive)
  --emS:   rgba(45,212,168,.08)
  --cr:    #F97066     (Coral — unfavorable, negative, errors)
  --crS:   rgba(249,112,102,.08)
  --am:    #FBBF24     (Amber — trending, warnings)
  --amS:   rgba(251,191,36,.08)
  --pr:    #A78BFA     (Purple — netting, special)
  --prS:   rgba(167,139,250,.08)

Gradient:
  --gA:    #002C77     (gradient start — Cobalt)
  --gB:    #00A8C7     (gradient end — Teal)

Glass effect:
  --glass:     rgba(15,29,50,.65)
  --glassBd:   rgba(0,168,199,.12)
  --glassBlur: blur(16px)
```

### 1.2 Color System (Light Theme)

```
  --bg:    #F4F7FC     --sf:    #FFFFFF     --cd:    #FFFFFF
  --cd2:   #F0F4FA     --bd:    #D4DCE8     --bd2:   #B8C4D6
  --tx:    #0A1628     --t2:    #5A6B84     --t3:    #8B9AB5
  --gd:    #BF8700     --em:    #0D9373     --cr:    #CF222E
  --am:    #9A6700     --pr:    #8250DF
  --glass: rgba(255,255,255,.7)
  --glassBd: rgba(0,44,119,.08)
  --glassBlur: blur(12px)
```

### 1.3 Typography

```
Body:     'DM Sans', sans-serif  (Google Fonts import)
Display:  'Playfair Display', Georgia, serif  (Google Fonts import)

Sizes:
  Page title:     22px  Playfair Display 700
  Section title:  15px  Playfair Display 700
  Card title:     12px  Playfair Display 700
  KPI number:     28px  Playfair Display 700 (with glow animation)
  Modal big num:  30px  Playfair Display 700 (with text-shadow glow)
  Table var num:  11px  Playfair Display 700
  Body text:      13px  DM Sans 400
  Table text:     11px  DM Sans 400
  Labels:         9-10px DM Sans 600
  Section label:  8px   DM Sans 700, uppercase, letter-spacing 0.9-1.2px, color: --tl
  Badge/pill:     9px   DM Sans 600, letter-spacing 0.2px
  Micro text:     7-8px DM Sans 700
```

### 1.4 Spacing

```
Page padding:      20px 24px (content area)
Card padding:      14-16px 16-18px
Card border-radius: 14px
Card gap:          10-12px
Section gap:       16-22px (generous breathing room)
KPI grid:          5 columns, 10px gap (responsive: 3 col at 1100px, 2 col at 700px)
Button padding:    5px 12px (secondary), 5px 14px (primary)
Button radius:     6px
Pill radius:       16px
Badge radius:      10px
```

### 1.5 Animations (15 keyframes)

```
fu (fadeUp):       translateY(16px)→0, opacity 0→1, 0.45s cubic-bezier(.22,1,.36,1)
  Stagger delays:  .d0=0s, .d1=.05s, .d2=.1s ... .d7=.35s

si (slideIn):      translateX(100%)→0, 0.25s cubic-bezier(.22,1,.36,1) — modal entrance

fi (fadeIn):       opacity 0→1, 0.15-0.2s ease — overlays

pulse:             opacity 1→.4→1, 2s infinite — notification dot, SLA red badges

expandIn:          max-height 0→600px + opacity + padding, 0.3s cubic-bezier(.22,1,.36,1)

blink:             opacity 1→0→1, 0.8s infinite — streaming cursor

slideDown:         translateY(-8px)→0 + opacity, 0.2s ease — dropdown menus

glow:              drop-shadow 8px→16px→8px rgba(0,168,199), 3s ease infinite — KPI numbers

headerGrad:        background-position 0%→100%→0%, 8s ease infinite — header shimmer

confetti:          translateY(0)→(-60px) + rotate(0→720deg) + opacity 1→0, 0.8s ease-out

borderPulse:       opacity 0.6→1→0.6, 2s ease infinite — alert card borders, red SLA

breathe:           box-shadow 0→6px→0 rgba(0,168,199), 1.5s ease infinite — chat avatar

typingBounce:      translateY(0)→(-4px)→0, 1.2s ease infinite — typing indicator dots
  Stagger: dot2=.15s, dot3=.3s

barSlide:          width 0→var(--bar-w), 0.5s cubic-bezier(.22,1,.36,1) — decomposition bars
  Stagger: 100ms per bar

shimmer:           background-position -200%→200%, for loading states
```

### 1.6 Glassmorphism Pattern

Every `.cd` card uses:
```css
background: var(--glass);          /* rgba(15,29,50,.65) */
backdrop-filter: var(--glassBlur); /* blur(16px) */
border: 1px solid var(--glassBd);  /* rgba(0,168,199,.12) */
border-radius: 14px;
```
Hover: `border-color: rgba(0,168,199,.2)`
Clickable cards add: `transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.12)`

### 1.7 Gradient Stripe

Top of every card:
```css
position: absolute; top: 0; left: 0; right: 0; height: 2px;
background: linear-gradient(90deg, #002C77, #00A8C7);
opacity: 0.6;
```

---

## 2. Layout Architecture

### 2.1 Two-Tier Header

**Layer 1 — Identity Bar (58px, Marsh Cobalt)**
```
Background: linear-gradient(135deg, #002C77, #001A4D, #002C77)
  background-size: 200% 200%; animation: headerGrad 8s ease infinite

Left:   [M logo SVG 30px] Marsh (Playfair 18px bold) Vantage (Playfair 18px 400)
        Below: VARIANCE INTELLIGENCE (8.5px, #A7E2F0 at 55% opacity, letter-spacing 2.5px)

Center: Tab bar (6 tabs in a pill container)
        Active tab: gradient(#00A8C7, #016D9E), white text, box-shadow
        Inactive: rgba(255,255,255,.4)

Right:  Bell (30px, notification dot), Theme toggle (dark/light), Clock (11px)
```

**Layer 2 — Context Strip (40px, translucent navy)**
```
Background: rgba(0,26,77,.35); backdrop-filter: blur(8px)

Left:   Persona pills (4) — pill shape with circle icon + label
        Active: teal gradient fill, teal border, teal icon/label
        Icons: ▦ Analyst, ◉ Director, ◈ CFO, ▣ BU Lead

Center: Time aggregation (MTD/QTD/YTD) · "vs" · Base (Budget/Fcst/PY)

Right:  Focus mode button
```

### 2.2 Page Layout

```
┌─────────────────────────────────────────┐
│ Header Layer 1 (58px)                   │
│ Header Layer 2 (40px)                   │
├──────────┬──────────────────────────────┤
│ Sidebar  │ Content area                 │
│ (210px)  │ (flex: 1, max-width: 1300px) │
│          │ padding: 20px 24px           │
│ Tree +   │                              │
│ Donut +  │ [Page content renders here]  │
│ BU list  │                              │
│          │                              │
│          │ [Marsh footer at bottom]     │
└──────────┴──────────────────────────────┘
```

Sidebar hides on Chat tab. Focus mode hides header + sidebar.

### 2.3 Sidebar Components

1. **Donut progress chart** (SVG 48px) — 3 segments: approved (emerald), reviewed (gold), draft (gray)
2. **BU list** — flat list with variance count badges (gold)
3. **4 hierarchy trees** — Geography, Segment, LOB, Cost Center
   - Expand/collapse per node with chevron rotation (spring easing: cubic-bezier(.34,1.56,.64,1))
   - Active node: teal background, teal text
   - Geo nodes show material variance counts
   - Click = set dimension filter + expand children

---

## 3. Page Specifications

### 3.1 Dashboard

Order of elements (top to bottom):
1. Breadcrumb with greeting: "Good afternoon, FP&A Analyst · Detail · MTD vs Budget"
2. Timestamp bar: green pulse dot + "Actuals as of Jun 30, 2026 · Engine: 18 min · Coverage: 100% · Last refreshed Nm ago"
3. Dimension filter banner (if active): teal border, "🔍 Filtered: Geo = APAC · N variances" + Clear button
4. Persona scope banner (BU Leader: "🔒 Marsh — reviewed & approved for your BU" / CFO: "✓ Approved only — N of M board-ready")
5. Success metrics bar: Cycle time: 18 min · Coverage: 100% · Root cause: 81% · Commentary: N%
6. Executive summary card: teal left border, persona-aware narrative (4 variants), "AI DETAIL/MID-LEVEL/EXECUTIVE/BU SUMMARY" badge
7. **KPI cards** (5, persona-specific):
   - Analyst: Revenue, EBITDA, OpIncome, HC Plan, Risk Items
   - Director: Revenue, EBITDA, Pending, Approved, Risk Items
   - CFO: Revenue, EBITDA, Report Ready, Risk Items, Commentary %
   - BU Leader: Marsh Rev, Marsh Costs, Variances, D&A Savings, Risk Items
   - Each card has: gradient stripe, label (8px teal), counter-animated number (28px Playfair), sparkline watermark SVG (6% opacity), delta with ▲/▼ arrow, sub-label, period comparison (Apr/May/Jun)
8. **CFO Top Items** (CFO only): ranked list of top 6 variances with one-line summary, clickable
9. Alert cards (persona-aware):
   - Analyst/Director: Netting (purple) + Trend (amber) with pulsing borders
   - CFO: Board Ready (emerald) + Key Risk (coral)
   - BU Leader: Trend + BU Highlight
10. **Charts** (2-column grid, 5:4 ratio):
    - EBITDA Waterfall (Chart.js bar, stacked, custom Marsh tooltip)
    - Revenue Trend (Chart.js line, actual solid green + budget dashed teal, gradient fill)
11. **Heatmap** (BU × 5 categories): cell glow on hover, clickable to filter table, BU Leader sees own BU only
12. **Variance table**: sortable columns (account, BU, varpct, status), search bar, sparklines, edge badges (New, No budget, N/A PY, edited), persona filtering
13. Marsh footer

### 3.2 P&L

1. Breadcrumb with time aggregation context
2. BU scope banner (BU Leader only)
3. Income Statement title (Playfair 15px)
4. P&L grid (7 columns): Account, ACT, BUD, VAR$, %, FAV, TYPE
   - Expandable parent rows (Revenue, COR, OpEx) with chevron
   - Detail rows indented 34px
   - Calculated rows (GROSS PROFIT, EBITDA, NET INCOME): Playfair bold, teal color, gradient background band
   - Alternating row tints (even rows: 1% teal)
   - Sign convention: `sg:'i'` = costs favorable when negative
   - Significance dot (5px circle) on rows with >5% variance
   - Click detail rows → open modal
5. **Margin radial gauges** (5 SVG donut charts): Gross 70.6%, EBITDA 30.6%, Op 28.3%, Tax 25.0%, Net 20.5%
6. Marsh footer

### 3.3 Chat

1. Breadcrumb
2. Header card: "Marsh Vantage" (Playfair 22px), greeting, persona depth, context inference label ("Inferred: MTD vs Budget · Jun 2026 · All BUs"), 4 suggestion pills
3. Message thread:
   - User messages: right-aligned, dark card, rounded 14px 14px 4px 14px
   - Agent messages: left-aligned, glass card with teal left border, "M" avatar (cobalt→teal gradient), rounded 4px 14px 14px 14px
   - Default conversation includes: confidence badge ("Confidence: 92%"), review status badge ("3 approved · 2 draft"), inline SVG mini-chart (6-month trend), variance callout cards (emerald favorable, coral unfavorable), netting alert (purple), inline data table with status column
   - Suggestion pills after each agent response
4. **Typing indicator**: 3 bouncing dots (typingBounce animation, 800ms before streaming starts)
5. **SSE streaming**: token-by-token with blinking cursor, 15-35ms per 3 chars
6. Chat input: focus glow (3px teal ring), Enter key sends
7. Chat history clears on persona switch

### 3.4 Review Queue

1. Breadcrumb with persona label
2. **Segmented progress bar**: 3 colored flex segments (emerald=approved, gold=reviewed, gray=draft) with animated flex transitions
3. 4 status counter cards (Awaiting, Reviewed, Approved, All)
4. **Batch action bar** (appears when checkboxes selected): "N selected" + "Mark reviewed" button
5. Sort control: toggle between Impact/SLA/Name
6. Search bar
7. Variance list (persona-filtered for BU Leader):
   - Checkbox, color bar, account name, badges (type, status, edited, synth, New), BU · Geo, variance number (Playfair 17px), SLA badge (green <12h, amber <24h, red >48h with pulse)
   - Expandable detail: narrative, decomposition with animated bars, **hypothesis feedback (✓/✗ buttons with state tracking)**
   - Working Confirm button (mutates status, fires confetti)
8. Marsh footer with SLA legend tooltip

### 3.5 Approvals

1. Breadcrumb
2. **Report gate indicator**: green "All approved — ready for distribution" OR amber "N pending — distribution blocked" with working "Approve all reviewed" button
3. Analyst groups (Sarah Chen, James Park):
   - Avatar circle (teal tint), name, "Approve (N)" bulk button
   - Per-item rows: status dot, account, variance pill, edited badge
   - Working approve/hold buttons (mutate status, fire confetti)
4. Marsh footer with report gate tooltip

### 3.6 Reports

1. Breadcrumb
2. BU scope banner (BU Leader only)
3. **3 sub-tabs**: Reports, Schedules, Templates
4. **Reports list** (persona-filtered):
   - Report name (Playfair 12px), status badge (Ready/Draft/Sent)
   - **Working Preview buttons** → open full-screen report overlay
   - Distribute (ready only), Download buttons
5. **Schedules**: frequency, next run date, Active/Paused badge, Edit button
6. **Templates**: type badge (PDF+PPTX, XLSX, DOCX), description, **Working Generate buttons** → open report overlay
7. Marsh footer

---

## 4. Report Preview System

### 4.1 Overlay Structure

```
Full-screen overlay (z-index 600):
  Background: rgba(0,0,0,.8) with backdrop-filter blur(8px)

  Toolbar (48px, #002C77):
    Left: Report title (Playfair 14px) + time aggregation badge
    Right: Print, Email, Download PDF (primary gradient), Close (×)

  Scroll area (centered, 32px padding):
    White paper pages (800px wide, min-height 1000px)
    Paper shadow: 0 8px 40px rgba(0,0,0,.4)
    Multiple pages stacked with 24px gap
```

### 4.2 Executive Flash (1 page)

- Marsh cobalt header stripe with logo + generation date
- Title: "Executive Flash Report" (Playfair 22px, #002C77)
- 4 KPI boxes (left cobalt border, #f4f7fc background)
- AI narrative block (teal left border)
- Top 6 variance table (with fav/unfav coloring)
- Risk flags (red left border, #fef2f2 background)
- Footer: "Marsh · Vantage v1.0 · Confidential"

### 4.3 Period-End Package (4 pages)

- **Page 1 — Cover**: Full cobalt→navy gradient, centered logo (Playfair 36px), title (28px), period, metadata, "CONFIDENTIAL" stamp
- **Page 2 — Summary**: KPIs, executive narrative, margin analysis table
- **Page 3 — Detail**: Every variance with decomposition, narrative, status
- **Page 4 — Risk**: Risk assessment blocks, outlook with numbered recommendations, methodology appendix

### 4.4 Board Narrative (1 page, research-note style)

- Marsh letterhead
- **Financial Performance** section with floating sidebar callout boxes (right-aligned, #f4f7fc, 180px, cobalt top border)
- Long-form board-ready prose paragraphs (11.5px, line-height 2)
- **Areas of Attention** section with red-accented callout
- **Outlook & Recommendations** with numbered action items
- AI generation disclosure

---

## 5. Modal / Detail Panel

Width: 500px, slides in from right (si animation), dark backdrop with blur.

Order of sections:
1. Header: type pill, status pill, edge badges (New, No budget, N/A PY), account name (Playfair 14px), metadata line
2. Big number card: counter-animated variance (Playfair 30px) with text-shadow glow (green for fav, red for unfav), percentage, Favorable/Unfavorable pill, confidence bar (4px teal), projected YE impact (amber card)
3. Decomposition: flex-wrap cards with animated bars (barSlide, 100ms stagger)
4. Correlations: cards with account name, hypothesis, confidence percentage
5. Narrative: AI generated/Analyst edited/Synthesized badge, narrative level label, text block, **working editor** (textarea toggle with separate Save/Cancel), CFO preview button (analysts only), Show reasoning toggle (reveals AI reasoning panel)
6. Hypotheses: cards with confidence-colored dot, text, confidence level, **working ✓/✗ feedback buttons** that persist state
7. Period trend: 3 mini-boxes (Apr/May/Jun) with values
8. **Working action buttons**: Confirm & review / Escalate / Dismiss (for drafts), Approve / Hold (for reviewed), "✓ Approved" (for approved), "↻ Auto-closed" (for autoclosed) — all mutate state + fire confetti on positive actions

---

## 6. Persona-RBAC Rules

| Persona | Dashboard | P&L | Chat | Review | Reports | Narrative Level |
|---------|-----------|-----|------|--------|---------|-----------------|
| Analyst | Full, all statuses | Full | Full | Full | Generate+View | Detail |
| Director | Full, all statuses | Full | Full | Full | Approve | Mid-level |
| CFO | Approved only | Full | Full | N/A | Full | Summary |
| BU Leader | Own BU, reviewed+approved | Own BU banner | Own BU | Own BU | Assigned only | Mid-level |

Filter chain: `VARS → filterByPersona() → filterByDim() → heatmap/search → sorted → rendered`

---

## 7. State Management

```typescript
V: string          // active view: 'dash'|'pl'|'chat'|'review'|'approve'|'reports'
P: string          // persona: 'analyst'|'director'|'cfo'|'bu'
TH: string         // theme: 'dark'|'light'
BASE: string       // comparison base: 'bud'|'fcast'|'py'
TAGG: string       // time aggregation: 'mtd'|'qtd'|'ytd'
MEETING: boolean   // focus mode
NOTIF_OPEN: boolean
SORT_COL: string|null   // dashboard table sort column
SORT_DIR: string        // 'asc'|'desc'
SEARCH_Q: string        // dashboard search query
HEATMAP_FILTER: object|null  // {bu, cat}
DIM_FILTER: object|null      // {dim, id, name}
RPT_TAB: string         // 'list'|'schedule'|'templates'
RV_SORT: string         // review queue sort: 'varpct'|'sla'|'account'
RV_SEARCH: string       // review queue search
BATCH_CHECKED: Set<number>  // checked review items
chatHistory: array      // [{role:'user'|'agent', text, streaming?, pills?}]
chatStreaming: boolean
PX: Set<string>         // expanded P&L parent rows
RX: Set<number>         // expanded review queue items
TEXP: Set<string>       // expanded tree nodes
BU_HOME: 'Marsh'        // BU Leader's assigned BU
```

---

## 8. Data Model

### 8.1 Variance Object (VARS array)

```typescript
interface Variance {
  a: string       // Account name
  bu: string      // Business unit (Marsh, Mercer, Marsh Re, Oliver Wyman, Marsh Corporate)
  g: string       // Geography
  v: number       // Variance $ (thousands)
  p: number       // Variance %
  tp: 'material' | 'netted' | 'trending'
  st: 'draft' | 'reviewed' | 'approved' | 'autoclosed'
  f: 0 | 1        // 1=favorable, 0=unfavorable
  sp: number[]    // 6-month sparkline data
  edited: 0 | 1
  editedBy: string
  editedNr: string
  sla: number     // Hours in queue
  isNew: 0 | 1
  noBud: 0 | 1    // No budget line
  noPY: 0 | 1     // No prior year
  synth: 0 | 1    // Synthesized narrative
  synthCount: number
  nr: {
    detail: string
    midlevel: string
    summary: string
    board: string
  }
  dc: Array<{l: string, v: number, p: number}>  // Decomposition
  hy: Array<{t: string, c: 'High'|'Medium'|'Low', fb: -1|0|1}>  // Hypotheses with feedback
  proj?: {ye: number, conf: string}  // Projected impact
  corr: Array<{a: string, p: number, f: boolean, hyp: string, conf: number}>  // Correlations
}
```

### 8.2 Business Units (2026 Rebrand)

```
Marsh, Mercer, Marsh Re, Oliver Wyman, Marsh Corporate
```

---

## 9. Event Architecture

Zero inline onclick handlers (except 3 minor toggles). All interaction through event delegation on `document`.

45 unique `data-*` attribute types handle all interactions. Key patterns:
- `data-nav="dash"` — tab navigation
- `data-per="analyst"` — persona switch
- `data-modal="3"` — open variance detail modal (index into VARS)
- `data-st-action="approve" data-st-idx="3"` — status transition
- `data-rpt-preview="flash"` — open report preview
- `data-hy-fb data-hy-vi="0" data-hy-hi="1" data-hy-fb="1"` — hypothesis feedback

---

## 10. Background Effects

```css
/* Radial ambient glow */
body::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse at 20% 20%, rgba(0,44,119,.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(0,168,199,.08) 0%, transparent 50%);
  pointer-events: none; z-index: 0;
}

/* Noise texture overlay */
body::after {
  content: '';
  position: fixed; inset: 0;
  background: url("data:image/svg+xml,...fractalNoise...");
  pointer-events: none; z-index: 0; opacity: .4;
}
```

---

## 11. Key Interaction Behaviors

1. **Tab switch**: Content fades to 30% opacity (150ms), re-renders, fades back — `transitionRender()`
2. **Persona switch**: Clears chat history, re-renders all views with filtered data
3. **Modal open**: Dark backdrop with blur, panel slides from right, big number counter-animates, decomposition bars cascade
4. **Approve/Confirm**: Status mutates, confetti burst (20 particles in brand colors), modal closes, re-render
5. **Chat send**: Typing dots (800ms) → streaming starts → token-by-token → suggestion pills appear
6. **Tree node click**: Toggle expand + set dimension filter (or clear if same node)
7. **Heatmap cell click**: Set BU×category filter on variance table
8. **Report preview**: Full-screen overlay with paper document, toolbar with Print/Email/Download

---

## 12. Tooltip Content (16 rich ⓘ icons)

Every II() tooltip has 50+ characters of substantive content explaining the feature, data source, or methodology. See prototype for exact text. Key tooltips cover: materiality OR logic, decomposition algebra, RAG learning pipeline, correlation scan, sign convention, report gate, SLA thresholds, persona adaptation.

---

## 13. Print Support

```css
@media print {
  body::before, .hdr, .tree, .bell, .ctl, .tabs, .bt, .search-bar { display: none !important }
  .cd { border: 1px solid #ddd; backdrop-filter: none; background: #fff; break-inside: avoid }
  .kp strong { animation: none; filter: none }
  * { color: #000; background: transparent }
  .fn::after { content: ' — Printed from Marsh Vantage' }
}
```

---

## 14. File References

- `FPA_Variance_Agent_UI.html` — Working 136KB prototype (this spec's source of truth)
- `FPA_Master_Spec_v1.docx` — Product + solution design (15 sections, 50 endpoints)
- `CLAUDE.md` — Project context, architecture, coding conventions
- `synthetic-data-spec.json` — Dimension hierarchies and data generation rules
- `UI_Enhancement_Brief.md` — Original 19 enhancement items

When building the React app, open `FPA_Variance_Agent_UI.html` in a browser as the visual reference. Every component, color, spacing, and animation in this spec was extracted from that prototype.
