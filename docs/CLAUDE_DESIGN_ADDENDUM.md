# CLAUDE.md — Design Addendum

## Add this section to your existing CLAUDE.md:

---

## Design Reference (Sprint 1+)

The UI has been fully prototyped and spec'd. These 4 files are the design source of truth:

| File | What | Size |
|------|------|------|
| `docs/FPA_Variance_Agent_UI.html` | **Working prototype** — open in browser as pixel-perfect visual target | 136KB |
| `docs/VANTAGE_DESIGN_SPEC.md` | **Design specification** — every color, spacing, animation, interaction, tooltip | 557 lines |
| `docs/design-tokens.ts` | **Design tokens** — copy to `frontend/src/theme/tokens.ts` | TypeScript |
| `docs/COMPONENT_INVENTORY.md` | **Component map** — prototype functions → React components + state mapping | 200 lines |

### Design Rules (non-negotiable)
1. **Color split**: Cobalt (#002C77) + Teal (#00A8C7) for chrome. Gold/Emerald/Coral/Amber/Purple for data semantics only. Never cross.
2. **Typography**: Playfair Display for numbers and titles. DM Sans for everything else.
3. **Glassmorphism**: Every card uses `backdrop-filter: blur(16px)` + translucent background + teal border glow on hover.
4. **Persona-first**: All data passes through persona RBAC filter before rendering. CFO sees approved only. BU Leader sees own BU only.
5. **Gradient stripe**: 2px cobalt→teal gradient at top of every card.
6. **Animation**: fadeUp entrance (0.45s, 50ms stagger), crossfade tab transitions (150ms), counter animations on KPIs, decomposition bar cascade.

### Build Order (Frontend)
1. Theme + tokens + global styles (background, glassmorphism, typography)
2. Header (two-tier) + Sidebar (donut, trees)
3. Dashboard (KPIs, charts, heatmap, variance table)
4. Modal (the detail panel — used from every page)
5. P&L (recursive grid + margin gauges)
6. Chat (SSE streaming + typing indicator)
7. Review Queue (sortable, searchable, persona-filtered + hypothesis feedback)
8. Approvals (report gate + analyst groups)
9. Reports (3 sub-tabs + 3 report preview templates)
10. Polish (transitions, confetti, tooltips, print CSS)
