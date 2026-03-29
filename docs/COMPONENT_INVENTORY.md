# Marsh Vantage — React Component Inventory

## How to use this with Claude Code

### Setup Instructions

1. Add all 4 files to your Claude Code project's `/docs/` folder:
   - `VANTAGE_DESIGN_SPEC.md` — Complete design specification (557 lines)
   - `FPA_Variance_Agent_UI.html` — Working 136KB prototype (open in browser as visual reference)
   - `design-tokens.ts` — Drop into `frontend/src/theme/tokens.ts`
   - `COMPONENT_INVENTORY.md` — This file (component→prototype mapping)

2. Update your `CLAUDE.md` to add this section:
   ```
   ## Design Reference
   - Open `docs/FPA_Variance_Agent_UI.html` in a browser — this is the pixel-perfect target
   - `docs/VANTAGE_DESIGN_SPEC.md` — Every color, spacing, animation, and interaction spec
   - `docs/design-tokens.ts` → copy to `frontend/src/theme/tokens.ts`
   - `docs/COMPONENT_INVENTORY.md` — Maps prototype functions to React components
   ```

3. Tell Claude Code:
   > "Build the frontend to match the prototype exactly. Use VANTAGE_DESIGN_SPEC.md
   > for all design decisions. Use design-tokens.ts for colors and typography.
   > Use COMPONENT_INVENTORY.md for the React component structure.
   > Open FPA_Variance_Agent_UI.html in a browser as your visual reference."

---

## Component Tree

```
App
├── ThemeProvider (dark/light, CSS variables from tokens.ts)
├── GlobalBackground (radial gradients + noise texture)
├── Header/
│   ├── IdentityBar (Layer 1: logo, tabs, bell, theme, clock)
│   └── ContextStrip (Layer 2: persona pills, time agg, base, focus)
├── Sidebar/
│   ├── DonutProgress (SVG donut chart — approved/reviewed/draft)
│   ├── BUList (flat list with variance count badges)
│   └── HierarchyTree × 4 (Geography, Segment, LOB, CostCenter)
│       └── TreeNode (recursive, with expand/collapse + spring chevron)
├── ContentArea/
│   ├── PageTransition (opacity crossfade wrapper)
│   ├── DashboardPage/
│   │   ├── Breadcrumb
│   │   ├── TimestampBar (green dot, live refresh timer)
│   │   ├── ScopeBanner (persona-conditional)
│   │   ├── MetricsBar (4 inline metrics)
│   │   ├── ExecSummary (persona-aware AI narrative)
│   │   ├── KPIGrid (5 cards, persona-specific data)
│   │   │   └── KPICard (counter animation, sparkline watermark, delta arrow)
│   │   ├── CFOTopItems (CFO only — ranked variance list)
│   │   ├── AlertCards (netting + trend, animated borders)
│   │   ├── ChartGrid/
│   │   │   ├── WaterfallChart (Recharts/D3, custom Marsh tooltip)
│   │   │   └── TrendChart (Recharts/D3, solid+dashed, gradient fill)
│   │   ├── Heatmap (BU × categories, cell glow, drill-through click)
│   │   ├── VarianceTable (sortable, searchable, sparklines, edge badges)
│   │   │   └── EmptyState (shown when 0 results)
│   │   └── MarsFooter
│   ├── PLPage/
│   │   ├── Breadcrumb (with time agg context)
│   │   ├── ScopeBanner (BU Leader only)
│   │   ├── PLGrid/
│   │   │   ├── PLHeaderRow
│   │   │   ├── PLParentRow (expandable: Revenue, COR, OpEx)
│   │   │   ├── PLDetailRow (indented, clickable → modal)
│   │   │   └── PLCalculatedRow (EBITDA, GP, Net Income — dramatic treatment)
│   │   ├── MarginGauges (5 × RadialGauge SVG components)
│   │   └── MarshFooter
│   ├── ChatPage/
│   │   ├── ChatHeader (greeting, persona depth, context inference badge)
│   │   ├── SuggestionPills (initial + after each response)
│   │   ├── MessageThread/
│   │   │   ├── UserMessage (right-aligned dark bubble)
│   │   │   └── AgentMessage (left-aligned glass bubble with:)
│   │   │       ├── AgentAvatar (M logo, breathing animation when streaming)
│   │   │       ├── ConfidenceBadge
│   │   │       ├── ReviewStatusBadge
│   │   │       ├── InlineMiniChart (SVG sparkline)
│   │   │       ├── VarianceCalloutCard (emerald/coral)
│   │   │       ├── NettingAlert (purple)
│   │   │       └── InlineDataTable (with status column)
│   │   ├── TypingIndicator (3 bouncing dots)
│   │   ├── ChatInput (focus glow, Enter to send)
│   │   └── MarshFooter
│   ├── ReviewPage/
│   │   ├── Breadcrumb (with persona label)
│   │   ├── SegmentedProgressBar (3-color flex bar: emerald/gold/gray)
│   │   ├── StatusCounterGrid (4 cards: Awaiting/Reviewed/Approved/All)
│   │   ├── BatchActionBar (conditional — appears when items checked)
│   │   ├── SortControl + SearchBar
│   │   ├── ReviewList (persona-filtered)/
│   │   │   └── ReviewItem/
│   │   │       ├── Checkbox, ColorBar, AccountName, Badges, SLABadge
│   │   │       └── ReviewItemExpanded/
│   │   │           ├── NarrativeBlock
│   │   │           ├── DecompositionBars (animated)
│   │   │           └── HypothesisList (with ✓/✗ feedback buttons)
│   │   └── MarshFooter
│   ├── ApprovalsPage/
│   │   ├── ReportGateIndicator (green=ready / amber=blocked)
│   │   ├── AnalystGroup × N/
│   │   │   ├── AnalystHeader (avatar, name, bulk approve)
│   │   │   └── ApprovalItem × N (status dot, variance pill, approve/hold)
│   │   └── MarshFooter
│   ├── ReportsPage/
│   │   ├── ScopeBanner (BU Leader only)
│   │   ├── ReportSubTabs (Reports/Schedules/Templates)
│   │   ├── ReportList (persona-filtered, Preview→overlay)
│   │   ├── ScheduleList (frequency, next run, active/paused)
│   │   ├── TemplateList (type badge, Generate→overlay)
│   │   └── MarshFooter
│   └── NotificationDropdown (7 items, mark all read)
├── VarianceModal (slide-in from right)/
│   ├── ModalHeader (type, status, edge badges, account name)
│   ├── BigNumberCard (counter animation, text-shadow glow, confidence bar)
│   ├── DecompositionSection (animated bars with cascade)
│   ├── CorrelationCards
│   ├── NarrativeSection/
│   │   ├── NarrativeBadge (AI generated / Analyst edited / Synthesized)
│   │   ├── NarrativeText
│   │   ├── NarrativeEditor (textarea with Save/Cancel)
│   │   ├── CFOPreviewBox (analysts only)
│   │   └── ReasoningPanel (AI transparency toggle)
│   ├── HypothesisCards (with confirm/reject feedback)
│   ├── PeriodTrend (Apr/May/Jun mini boxes)
│   └── ActionButtons (Confirm/Escalate/Dismiss or Approve/Hold)
├── ReportPreviewOverlay/
│   ├── ReportToolbar (title, badge, Print/Email/Download/Close)
│   ├── ReportScroll/
│   │   ├── ExecutiveFlashReport (1 page)
│   │   ├── PeriodEndReport (4 pages with cover)
│   │   └── BoardNarrativeReport (1 page, research-note style)
│   └── ReportPage (white paper with shadow, Marsh header/footer)
└── ConfettiContainer (burst on approve/confirm)
```

---

## Mapping: Prototype Function → React Component

| Prototype Function | React Component | Notes |
|---|---|---|
| `renderHdr()` | `Header/IdentityBar` + `Header/ContextStrip` | Two-tier sticky header |
| `renderTree()` | `Sidebar/*` | Donut + BU list + 4 trees |
| `rD(el)` | `DashboardPage/*` | 13 sub-components |
| `rP(el)` | `PLPage/*` | Recursive grid + margin gauges |
| `rC(el)` | `ChatPage/*` | SSE streaming, typing indicator |
| `rR(el)` | `ReviewPage/*` | Sortable, searchable, persona-filtered |
| `rA(el)` | `ApprovalsPage/*` | Report gate + analyst groups |
| `rRp(el)` | `ReportsPage/*` | 3 sub-tabs + persona filtering |
| `openModal(idx)` | `VarianceModal` | Slide-in panel with all sections |
| `openReport(type)` | `ReportPreviewOverlay` | Full-screen with paper pages |
| `rptFlash()` | `ExecutiveFlashReport` | 1 page |
| `rptPeriod()` | `PeriodEndReport` | 4 pages with cover |
| `rptBoard()` | `BoardNarrativeReport` | Research-note style |
| `sendChat()` | `useChatStream` hook | Typing dots → SSE streaming |
| `filterByPersona()` | `usePersonaFilter` hook | RBAC filtering |
| `filterByDim()` | `useDimensionFilter` hook | Tree node filtering |
| `countUp()` | `useCountUp` hook | Animated number counter |
| `kpiWatermark()` | `KPICard` sub-component | SVG sparkline at 6% opacity |
| `donutChart()` | `DonutProgress` | SVG donut with 3 segments |
| `radialGauge()` | `RadialGauge` | SVG gauge for P&L margins |
| `transitionRender()` | `PageTransition` wrapper | 150ms opacity crossfade |
| `fireConfetti()` | `ConfettiContainer` | 20 particles in brand colors |

---

## State Management → React Context

| Prototype Variable | React Context / Hook | Scope |
|---|---|---|
| `V` (view) | React Router or `useView` | Global |
| `P` (persona) | `usePersona` context | Global |
| `TH` (theme) | `useTheme` context | Global |
| `BASE` (comparison) | `useFilters` context | Global |
| `TAGG` (time agg) | `useFilters` context | Global |
| `MEETING` (focus) | `useFocusMode` | Global |
| `SORT_COL/DIR` | `useSortState` | Dashboard local |
| `SEARCH_Q` | `useSearchState` | Dashboard local |
| `HEATMAP_FILTER` | `useHeatmapFilter` | Dashboard local |
| `DIM_FILTER` | `useDimensionFilter` | Global (sidebar) |
| `BATCH_CHECKED` | `useBatchSelect` | Review local |
| `chatHistory` | `useChatStream` | Chat local |
| `PX` (P&L expanded) | `useExpandState` | P&L local |
| `RX` (review expanded) | `useExpandState` | Review local |
| `TEXP` (tree expanded) | `useTreeState` | Sidebar local |
| `VARS` (data) | `useVariances` + API | Global, from backend |

---

## Critical Implementation Notes

1. **Color discipline**: Cobalt/Teal for chrome ONLY. Gold/Emerald/Coral for data semantics ONLY. Never mix.
2. **Glassmorphism on every card**: background blur + translucent + teal border glow on hover.
3. **Playfair Display for numbers**: KPIs, big variance amounts, section titles. DM Sans for everything else.
4. **Persona filtering is the first operation**: Always filter data through persona RBAC before any rendering.
5. **All state transitions fire confetti**: Confirm and Approve both trigger the confetti burst.
6. **Report gate is live**: Distribution buttons should be disabled when not all variances are approved.
7. **Chat clears on persona switch**: Fresh context for each persona.
8. **Enter key sends chat**: Not just the Send button.
9. **No inline onclick**: Use React's normal onClick props (equivalent to the prototype's event delegation).
10. **16 rich tooltips**: Every ⓘ icon has 50+ characters of substantive help text.
