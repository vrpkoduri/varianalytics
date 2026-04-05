# Light Mode Visual Audit — Complete Findings

**Date:** 2026-04-05
**Method:** Page-by-page visual inspection + CSS property inspection in light mode with live backend data
**Pages Tested:** All 8 (Dashboard, Exec Summary, P&L, Chat, Review, Approval, Reports, Admin)

---

## Overall Assessment

The app was designed dark-first. Light mode was added via CSS variable overrides on `.light` class. While the base colors switch correctly (`--bg`, `--card`, `--tx-primary`), the **overall light mode feels washed out, low-contrast, and lacks visual hierarchy**. The dark mode's depth comes from glassmorphism (blur + translucent backgrounds + glow borders), which translates poorly to light backgrounds.

### Core Problem: The Light Palette Lacks Depth

In dark mode, the visual hierarchy is:
- **Background** (#030B1A) → **Surface** (#0A1628) → **Card** (#0F1D32) → **Text** (#E8EDF5)
- Cards "pop" via glassmorphism glow, teal border accents, and the 2px gradient stripe

In light mode, the equivalent is:
- **Background** (#F4F7FC) → **Surface** (#FFFFFF) → **Card** (#FFFFFF) → **Text** (#0A1628)
- Cards and surface are BOTH white → **no depth, everything flattens**
- Glassmorphism blur on white-on-white is invisible
- Teal border glow at 8% opacity is invisible on white

---

## Issues Found (organized by category)

### A. Global / Cross-Page Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L1 | **Persona/context strip dark band** | High | `bg-[rgba(0,26,77,.35)]` creates a dark navy band over light background — visually jarring, looks like a rendering glitch |
| L2 | **Inactive filter buttons invisible** | High | QTD, YTD, Fcst, PY use `color: rgba(255,255,255,0.3)` — 30% white on dark strip = near-invisible text |
| L3 | **Subtitle/context text invisible** | Medium | "ANALYST WORKSPACE", "JUN 2026 VS BUDGET", "DIRECTOR APPROVAL QUEUE", "MTD VS BUDGET" labels use `text-tx-tertiary` which is `#8B9AB5` — too light on white |
| L4 | **Glass cards have no visual weight** | High | White cards on white background with transparent borders = no depth. Cards merge with page. Needs subtle shadow or border in light mode |
| L5 | **Status badges (AI Draft) invisible** | Medium | Very pale gray background/border on white — barely visible |

### B. Dashboard-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L6 | **Chart axis labels low contrast** | Medium | `var(--tx-tertiary)` = `#8B9AB5` on white cards. Waterfall X-axis labels and Y-axis values are faint |
| L7 | **Heatmap loses heat effect** | Medium | Cell background tints (emerald/coral at 5-20% opacity) are invisible on white. No visual "heat" in the heatmap |
| L8 | **Revenue Trend area fill invisible** | Low | The teal gradient fill under the actual line is transparent in light mode |
| L9 | **KPI card numbers lack hierarchy** | Low | All 5 KPI cards are white boxes with dark numbers — no visual distinction between them |

### C. P&L-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L10 | **Table rows lack separation** | Medium | No alternating row colors or clear borders between rows. Rows blend together |
| L11 | **Margin gauge rings faint** | Low | Donut rings use teal/emerald/amber at low opacity — barely visible on white |

### D. Review-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L12 | **Review item cards lack separation** | Medium | All items are white with no border/shadow distinction. Only the left teal accent bar separates them |
| L13 | **Checkboxes nearly invisible** | Medium | Light gray border on white background — very hard to see |
| L14 | **Status counter cards flat** | Low | 50/0/0/50 cards are plain white boxes — no visual depth or card effect |

### E. Chat-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L15 | **Send button washed out** | Medium | Teal gradient barely visible. Button lacks prominence |
| L16 | **Suggestion pills ghost-like** | Low | Very faint gray borders, low visual weight |
| L17 | **Chat input card merges with page** | Medium | Glass card background rgba(255,255,255,0.7) on white page = invisible |

### F. Approval-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L18 | **Report gate banner faint** | Medium | Amber/warning background tint is almost invisible on light |
| L19 | **Approve/Hold buttons washed** | Medium | Teal approve button is pastel; coral Hold button has faint border only |
| L20 | **Variance badge containers invisible** | Low | Emerald/coral background tints at 6-8% opacity = invisible on white |

### G. Admin-Specific

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| L21 | **Active tab indicator too subtle** | Low | Barely distinguishable from inactive tabs |

---

## Color Palette Analysis & Recommendations

### Current Light Mode Palette (CSS variables)

```
--bg:           #F4F7FC  (very light blue-gray)
--surface:      #FFFFFF  (white)
--card:         #FFFFFF  (white — SAME as surface!)
--card-alt:     #F0F4FA  (barely different from bg)
--border:       #D4DCE8  (light gray)
--border-hover: #B8C4D6  (medium gray)
--tx-primary:   #0A1628  (dark navy — good)
--tx-secondary: #5A6B84  (medium gray — OK)
--tx-tertiary:  #8B9AB5  (light gray — TOO LIGHT for labels)
--glass:        rgba(255,255,255,.7)  (invisible on white)
--glass-border: rgba(0,44,119,.08)    (invisible on white)
```

### Root Problems

1. **`--card` and `--surface` are both `#FFFFFF`** — no depth between cards and page
2. **`--glass` is 70% white on white** — glassmorphism effect completely disappears
3. **`--glass-border` at 8% opacity** — invisible border on white cards
4. **`--tx-tertiary` `#8B9AB5`** — too light for any functional label text
5. **Data semantic surfaces (6-10% opacity tints)** — designed for dark backgrounds, invisible on white

### Recommended Light Palette Changes

```css
.light {
  /* Add depth: card should be distinct from background */
  --bg: #F0F3F8;           /* slightly darker blue-gray page */
  --surface: #FFFFFF;       /* white surface */
  --card: #FFFFFF;          /* keep white */
  --card-alt: #F7F8FC;     /* subtle alt */

  /* Stronger borders for card definition */
  --border: #C8D1E0;       /* darker border */
  --border-hover: #A0ADBE; /* more visible hover */

  /* Tertiary text needs more contrast */
  --tx-tertiary: #6B7A90;  /* darker — meets WCAG AA for labels */

  /* Glass effect: use shadow instead of blur on white */
  --glass: rgba(255,255,255,.95);
  --glass-border: rgba(0,44,119,.15);  /* doubled opacity */

  /* Data semantic surfaces: stronger tints */
  --gold-surface: rgba(191,135,0,.12);     /* was .08 */
  --emerald-surface: rgba(13,147,115,.10); /* was .06 */
  --coral-surface: rgba(207,34,46,.10);    /* was .06 */
  --amber-surface: rgba(202,138,4,.10);    /* was .06 */
  --purple-surface: rgba(124,58,237,.10);  /* was .06 */
}
```

### Additional CSS Changes Needed

1. **Add card shadow in light mode:**
```css
.light .glass-card {
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  border: 1px solid var(--border);
}
```

2. **Persona/context strip — lighter in light mode:**
```css
.light .context-strip {
  background: rgba(0,26,77,.08);  /* was .35 — way too dark */
  color: var(--tx-primary);       /* dark text instead of white */
}
```

3. **Inactive filter buttons — dark text in light mode:**
The inline `rgba(255,255,255,.3)` on QTD/YTD/Fcst/PY needs to be `var(--tx-tertiary)` in light mode.

4. **Heatmap cell backgrounds — stronger tints:**
The cell color function returns `bg-emerald/5` etc. — needs `bg-emerald/15` in light mode for visible heat.

---

## Priority Summary

| Priority | Count | Description |
|----------|-------|-------------|
| **High** | 3 | Context strip dark band, invisible filter buttons, cards have no depth |
| **Medium** | 10 | Faint labels, flat cards across all pages, washed buttons, heatmap no heat |
| **Low** | 8 | Gauge rings, badge containers, area fills, tab indicators |

**Recommendation:** Fix the 5 root CSS variable issues (bg, border, tx-tertiary, glass-border, data surfaces) + add light-mode card shadow + fix context strip. This single palette fix will resolve ~80% of the individual issues automatically since they all stem from the same low-contrast root cause.
