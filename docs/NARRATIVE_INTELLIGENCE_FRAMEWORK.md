# Narrative Intelligence Framework — Marsh Vantage

**Version:** 1.0 | **Date:** 2026-04-01 | **Status:** Approved Design

---

## 1. Vision

Transform FP&A variance commentary from isolated, manually-written explanations into a **layered, context-aware narrative pyramid** that builds intelligence bottom-up — mirroring how a human analyst thinks, but at machine scale.

**Core principle:** Each narrative layer consumes the approved output of the layer below, creating progressively richer context as it moves up toward leadership.

---

## 2. The Narrative Pyramid

```
                    ┌─────────────────┐
                    │  BOARD NARRATIVE │  Layer 7 (on-demand)
                    │  Strategic frame │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ EXEC SUMMARY    │  Layer 6
                    │ CFO headline +  │
                    │ full narrative   │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │      SECTION NARRATIVES     │  Layer 5
              │ Revenue | COGS | OpEx | P&L │
              └──────────────┬──────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │         PARENT SUMMARIES (MTD)        │  Layer 4
         │  References approved child narratives  │
         └───────────────────┬───────────────────┘
                             │
    ┌────────────────────────▼────────────────────────┐
    │           LEAF DETAIL NARRATIVES (MTD)          │  Layer 3
    │  Decomposition + correlations + trends + RAG    │
    └────────────────────────┬────────────────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │         QTD NARRATIVES                │  Layer 2
         │  Built from MTD narratives per month   │
         └───────────────────┬───────────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │         YTD NARRATIVES                │  Layer 1
         │  Built from QTD narratives             │
         └───────────────────────────────────────┘
```

### Generation Order (Bottom-Up)

| Step | Layer | Input | Output |
|------|-------|-------|--------|
| 5A | Leaf Detail (MTD) | Variance data + decomposition + correlations + RAG examples + carry-forward from prior period | Detail narrative per leaf account × BU × geo |
| 5B | Parent Summary (MTD) | Approved/generated child narratives + parent variance data | Midlevel + summary referencing children |
| 5C | Section Narratives | All parent narratives within P&L section | 2-3 sentence section synthesis |
| 5D | Executive Summary | All section narratives + KPI data + risk items + cross-BU themes | CFO-ready headline + full narrative |
| 5E | QTD Narratives | MTD narratives for each month in quarter + QTD variance data | Quarter progression narrative |
| 5F | YTD Narratives | QTD narratives + YTD variance data | Full year perspective |
| 5G | Board Narrative | Approved exec summary + strategic context | Board-appropriate language (on-demand) |

---

## 3. Data Architecture

### 3.1 New Tables

```
fact_executive_summary
├── summary_id          (deterministic hash: period + base + view)
├── period_id
├── base_id             (BUDGET / FORECAST / PRIOR_YEAR)
├── view_id             (MTD / QTD / YTD)
├── headline            (1-2 sentences — the big story)
├── full_narrative       (2-3 paragraphs — detailed executive narrative)
├── carry_forward_note   (comparison vs prior period)
├── key_risks           (JSON array of risk items)
├── cross_bu_themes     (JSON array of cross-BU patterns)
├── status              (AI_DRAFT / REVIEWED / APPROVED)
├── narrative_source    (llm / template)
├── narrative_confidence (0.0-1.0)
├── created_at
└── approved_at

fact_section_narrative
├── section_id          (deterministic hash: period + section + base + view)
├── period_id
├── section_name        (Revenue / COGS / OpEx / Below-the-Line / Profitability)
├── base_id
├── view_id
├── narrative           (2-3 sentences synthesizing the section)
├── key_drivers         (JSON array: [{account, amount, direction}])
├── status              (AI_DRAFT / REVIEWED / APPROVED)
├── narrative_confidence (0.0-1.0)
├── created_at
└── approved_at

narrative_version_history (append-only audit trail)
├── version_id          (auto-increment)
├── variance_id         (FK to fact_variance_material OR section_id OR summary_id)
├── entity_type         (variance / section / executive / board)
├── version_number      (1, 2, 3...)
├── narrative_text      (full text at this version)
├── changed_by          (user_id)
├── change_type         (ai_generated / analyst_edit / director_feedback / regen / approval)
├── change_reason       (factual_correction / added_context / style / removed_hallucination / simplified)
├── created_at
└── (IMMUTABLE — no updates, no deletes)
```

### 3.2 Modified Tables

```
fact_variance_material (existing — key changes)
├── variance_id         CHANGED: deterministic hash instead of random UUID
│                       hash(period_id + account_id + bu_id + costcenter + geo + segment + lob + view_id + base_id)
├── narrative_confidence NEW: 0.0-1.0 based on decomposition quality
├── ... all existing columns preserved
└── Approved narratives PRESERVED across engine re-runs

fact_review_status (existing — key changes)
├── variance_id         CHANGED: deterministic (matches new variance_id)
├── edited_narrative    CLARIFIED: always contains LATEST version (overwritten on each edit)
├── version_count       NEW: number of edits (for quick display)
├── locked_by           NEW: user_id of analyst currently editing (soft lock)
├── locked_until        NEW: timestamp when lock expires (30 min)
└── original_narrative  PRESERVED: what AI generated (never changes)
```

### 3.3 Table Relationships

```
fact_variance_material (leaf + parent variances)
    │ variance_id (deterministic)
    ├──► fact_review_status (1:1 — review workflow state)
    ├──► fact_decomposition (1:1 — root cause drivers)
    ├──► fact_correlations (1:N — related variances)
    └──► narrative_version_history (1:N — edit audit trail)

fact_section_narrative (5 sections per period)
    │ section_id (deterministic)
    └──► narrative_version_history (1:N — edit audit trail)

fact_executive_summary (1 per period × base × view)
    │ summary_id (deterministic)
    └──► narrative_version_history (1:N — edit audit trail)

knowledge_commentary_history (RAG vector store)
    └── ALWAYS stores LATEST approved text from fact_review_status.edited_narrative
```

---

## 4. Quality Guardrails

### 4.1 Numerical Accuracy Validation

After LLM generates narrative text:
1. Extract dollar amounts and percentages via regex
2. Cross-reference against source variance data
3. If mismatch > 5% tolerance → reject LLM output, use template fallback
4. Log as "hallucination_detected" in audit

### 4.2 Confidence Scoring

| Condition | Confidence | Narrative Language |
|-----------|-----------|-------------------|
| Real decomposition (unit data available) | 0.9+ | "Driven by volume increase of $X" |
| Fallback decomposition (proportional split) | 0.5-0.7 | "Likely driven by volume factors" |
| High residual (>40% unexplained) | 0.3-0.5 | "Partially explained by... Remaining $X requires investigation" |
| No decomposition available | 0.1-0.3 | "Variance of $X observed. Further analysis needed." |

### 4.3 Comparison-Base-Aware Tone

| Base | Framing | Example |
|------|---------|---------|
| **BUDGET** | Performance vs plan, accountability | "Revenue fell short of plan by $200K due to delayed APAC project starts" |
| **PRIOR_YEAR** | Growth trajectory, market context | "Revenue grew 15% year-over-year, driven by new client acquisitions in EMEA" |
| **FORECAST** | Execution gap, re-forecasting | "Tracking $200K below latest forecast; recommend adjusting Q4 outlook" |

### 4.4 Summary-Level Materiality

When building section and executive narratives:
- Include top N variances by absolute amount (configurable, default: 5)
- Or all variances above X% of section total (configurable, default: 10%)
- Rollup excluded items: "...and 12 other items totaling $340K favorable"
- Narrative length budgets: detail (300 words), section (100 words), executive (500 words)

---

## 5. Carry-Forward Intelligence

### 5.1 Prior Period Context

When generating Month T's narratives:
- Fetch Month T-1's APPROVED narrative for the same variance (same deterministic ID minus period)
- Include in LLM prompt: "Last month: [approved text]. This month the variance is [new data]. Explain what changed."
- If prior month was corrected after approval, use the corrected version

### 5.2 Temporal Coherence

- If prior month said "one-time consulting fee" and the same account varies again → note "previously attributed to one-time; recurrence suggests structural change"
- If variance direction reversed → note "reversed from [prior direction]"
- If variance accelerated/decelerated → note magnitude change

---

## 6. Review Workflow (Enhanced)

### 6.1 Version History Flow

```
v1: AI generates     → narrative_version_history (type=ai_generated)
                     → fact_review_status.original_narrative = text
                     → fact_review_status.edited_narrative = NULL

v2: Analyst edits    → narrative_version_history (type=analyst_edit, reason=added_context)
                     → fact_review_status.edited_narrative = NEW text (overwrites)
                     → fact_review_status.version_count = 2

v3: Director rejects → narrative_version_history (type=director_feedback)
                     → fact_review_status.status = AI_DRAFT (sent back)

v4: Analyst re-edits → narrative_version_history (type=analyst_edit)
                     → fact_review_status.edited_narrative = NEWER text (overwrites v2)
                     → fact_review_status.version_count = 4

v5: Director approves → narrative_version_history (type=approval)
                      → fact_review_status.status = APPROVED
                      → knowledge_commentary_history = LATEST edited_narrative
                      → Enables parent summary regeneration
```

### 6.2 Concurrent Editing

- Soft lock: when analyst opens variance for editing, set `locked_by` + `locked_until` (30 min)
- Other analysts see "Being edited by Sarah Chen" — can view but not edit
- Lock auto-expires after 30 minutes
- Optimistic locking: `version_count` checked on save — if changed since load, show conflict

### 6.3 Analyst Assignment

- Variances assignable to specific analysts (by BU, by account domain, or manual)
- Review queue shows "My Items" vs "All Items"
- SLA tracking per analyst (48-hour target)

### 6.4 On-Demand Summary Regeneration

After analysts approve leaf narratives:
1. Director sees "Regenerate Summary" button on parent accounts
2. System collects all APPROVED child narratives
3. LLM generates fresh parent narrative using updated children as context
4. New narrative enters as AI_DRAFT → goes through approval again
5. Same cascade available at section and executive levels

---

## 7. Executive Summary Page

### 7.1 Persona-Based Landing

| Persona | Landing Page | Navigation |
|---------|-------------|------------|
| Analyst | Dashboard (operational detail) | Full nav |
| BU Leader | Dashboard (BU-scoped) | Reduced nav |
| Director | Executive Summary or Dashboard (choice) | Full nav |
| CFO | Executive Summary | Reduced nav |
| Board Viewer | Executive Summary (read-only) | Minimal nav |
| Admin | Dashboard | Full nav + Admin |

### 7.2 Page Layout

| Section | Content Source | Visual |
|---------|--------------|--------|
| Headline | `fact_executive_summary.headline` | Large text, cobalt |
| KPI Cards | `GET /dashboard/summary` (existing) | 4 cards with sparklines |
| Revenue Section | `fact_section_narrative` (Revenue) | Narrative + mini waterfall |
| Cost Section | `fact_section_narrative` (COGS + OpEx) | Narrative + mini waterfall |
| Profitability | `fact_section_narrative` (Profitability) | Narrative + margin gauge |
| Risk Items | Netting alerts + trend alerts (existing) | Warning cards |
| Period Comparison | `fact_executive_summary.carry_forward_note` | Comparison callout |
| Download | Reports (existing) | Board Deck + Flash PDF buttons |

### 7.3 Impact on Existing Pages

**No changes to existing pages.** The Executive Summary is an additional view. Dashboard, P&L, Chat, Review, Approval, Reports, Admin — all remain as-is.

---

## 8. Report Integration

Reports become **consumers of the narrative pyramid**, not generators of content.

| Report | Audience | Layers Used |
|--------|----------|-------------|
| **XLSX** | Analyst | Layer 3 (leaf detail) in variance tabs, Layer 4 (parent) in summary tab |
| **PDF Executive Flash** | CFO | Layer 6 (exec summary) + Layer 5 (sections) + top 5 from Layer 4 |
| **PPTX Board Deck** | Board | Layer 7 (board) + Layer 6 (exec) + KPI visuals |
| **DOCX Board Narrative** | Board | Layer 7 + Layer 5 (sections) + risks + recommendations |

---

## 9. Feedback Loop

```
Approved Narrative
    ↓
Embedded → Vector Store (knowledge_commentary_history)
    ↓
RAG Retriever (70% semantic + 15% account + 15% magnitude)
    ↓
Future Period Generation → similar approved narratives as few-shot examples
    ↓
Better AI drafts → less analyst editing → faster close cycle
```

### Edit Intent Capture

When analyst edits, capture:
- **What changed:** text diff (existing)
- **Why they changed it:** dropdown — factual correction / added context / simplified / removed hallucination / style preference (new)
- **This enables:** RAG system learns error patterns, not just final text

---

## 10. Implementation Phases

| Phase | Scope | When | Key Deliverables |
|-------|-------|------|-----------------|
| **2A** | Foundation | Week 13-14 | Deterministic IDs, narrative persistence, version history table, FY-scoped review |
| **2B** | Layered Generation | Week 15-17 | 5A leaf-first, 5B parent-from-children, numerical guardrails, confidence scoring |
| **2C** | Section + Executive | Week 17-19 | 5C sections, 5D exec summary, materiality filtering, cross-BU themes, comparison-base tone |
| **2D** | Executive Summary Page | Week 19-20 | New frontend view, persona-based landing, risk items, downloads |
| **2E** | QTD/YTD + Carry-Forward | Week 20-21 | 5E-F temporal layering, prior period context |
| **2F** | Workflow Enhancement | Week 21-22 | Analyst locking, edit intent, escalation, on-demand regen |
| **2G** | Report Integration | Week 22-23 | Reports pull from pyramid |
| **2H** | Seasonality + FX | Week 23-24 | Seasonal profiles, dual-currency framing |

---

## 11. Guardrails Summary

| Guardrail | Layer | Implementation |
|-----------|-------|---------------|
| Numerical accuracy | All | Post-generation regex validation vs source data |
| Confidence scoring | Leaf + Parent | Based on decomposition quality + residual |
| Comparison-base tone | All | Prompt variants per base type |
| Summary materiality | Section + Exec | Top N filter + rollup language |
| Hallucination detection | All | Reject + template fallback + audit log |
| Temporal coherence | Carry-forward | Use corrected version if prior was amended |
| Unexplained variance | Leaf | Auto-escalate when residual > 40% |
| Concurrent editing | Review | Soft lock + optimistic versioning |
| Audit immutability | Version history | Append-only table, no UPDATE/DELETE |
| Approved persistence | Engine re-run | Skip overwrite when status = APPROVED |
