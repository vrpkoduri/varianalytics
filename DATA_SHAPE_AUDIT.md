# Data Shape Audit: varianalytics API ↔ Frontend Mismatches

## Executive Summary
The app is showing mock data because API responses don't match frontend component expectations. Below is an exhaustive audit of each endpoint with exact field mismatches.

---

## DASHBOARD PAGE

### 1. Summary Cards (KPI Cards)

**Backend API Response** (`GET /dashboard/summary`)
Returns:
```python
{
  "cards": [
    {
      "metric_name": "Total Revenue",
      "account_id": "acct_revenue",
      "actual": 1234.56,
      "comparator": 1234.56,
      "variance_amount": 100.00,
      "variance_pct": 5.2,
      "is_favorable": True,
      "is_material": True
    }
  ],
  "period_id": "2026-06",
  "view_id": "MTD",
  "base_id": "BUDGET"
}
```

**Frontend Component Expects** (`KPICard` + `KPIGrid`)
```typescript
{
  id: string
  label: string
  value: number
  prefix: string        // "$"
  suffix: string        // "K"
  delta: number         // percentage, not dollar amount
  favorable: boolean
  comparator: number
  comparatorLabel: string  // e.g. "vs $1,803K"
  sparkData: number[]
}
```

**Frontend Hook** (`useDashboard.ts`)
- Receives API response
- Falls back to mock: `{ cards: MOCK_KPI_CARDS }`
- Does NO mapping/transformation

**MISMATCHES IDENTIFIED:**

| Backend Field | Frontend Expects | Issue |
|---|---|---|
| `metric_name` | `label` | Field name mismatch |
| `account_id` | (not used) | Extra field, unused |
| `actual` | `value` | Field name mismatch |
| `comparator` | `comparator` | ✓ Match |
| `variance_amount` | (not used) | Extra field, unused |
| `variance_pct` | `delta` | Field name mismatch |
| `is_favorable` | `favorable` | Field name mismatch (is_ prefix) |
| `is_material` | (not used) | Extra field, unused |
| (missing) | `id` | Backend doesn't provide ID |
| (missing) | `prefix` | Backend doesn't provide prefix |
| (missing) | `suffix` | Backend doesn't provide suffix |
| (missing) | `comparatorLabel` | Backend doesn't provide formatted string |
| (missing) | `sparkData` | Backend doesn't provide spark data |

---

### 2. Waterfall Chart

**Backend API Response** (`GET /dashboard/waterfall`)
```python
{
  "steps": [
    {
      "name": "Budget",
      "value": 488.00,
      "cumulative": 488.00,
      "is_total": True,
      "is_positive": True
    }
  ],
  "period_id": "2026-06",
  "base_id": "BUDGET"
}
```

**Frontend Component Expects** (`WaterfallChart`)
```typescript
{
  name: string
  value: number
  cumulative: number
  type: 'total' | 'positive' | 'negative'
}
```

**MISMATCHES IDENTIFIED:**

| Backend Field | Frontend Expects | Issue |
|---|---|---|
| `name` | `name` | ✓ Match |
| `value` | `value` | ✓ Match |
| `cumulative` | `cumulative` | ✓ Match |
| `is_total` | `type: 'total'` | Type mismatch: boolean → enum value |
| `is_positive` | `type: 'positive'\|'negative'` | Type mismatch: boolean → enum value |

---

### 3. Trends (TrendChart)

**Backend API Response** (`GET /dashboard/trends`)
```python
{
  "data": [
    {
      "period_id": "2026-01",
      "actual": 1234.56,
      "comparator": 1234.56,
      "variance_amount": 100.00,
      "variance_pct": 5.2
    }
  ],
  "account_id": "acct_gross_revenue",
  "periods": 12
}
```

**Frontend Component Expects** (`TrendChart`)
```typescript
{
  month: string      // e.g. "Jan"
  actual: number
  budget: number     // not "comparator"
}
```

**MISMATCHES IDENTIFIED:**

| Backend Field | Frontend Expects | Issue |
|---|---|---|
| `period_id` | `month` | Field name mismatch; format issue (YYYY-MM vs 3-letter month) |
| `actual` | `actual` | ✓ Match |
| `comparator` | `budget` | Field name mismatch |
| `variance_amount` | (not used) | Extra field, unused |
| `variance_pct` | (not used) | Extra field, unused |

---

### 4. Heatmap

**Backend API Response** (`GET /dashboard/heatmap`)
```python
{
  "rows": ["APAC", "EMEA", "NAM", ...],
  "columns": ["Marsh", "Mercer", "Guy Carpenter", ...],
  "cells": [
    [
      {"value": 2500.00, "pct": 3.2, "is_material": True},
      {"value": -1200.00, "pct": -1.4, "is_material": False},
      ...
    ],
    [...]
  ]
}
```

**Frontend Component Expects** (`Heatmap`)
```typescript
{
  columns: string[]
  rows: {
    bu: string
    cells: number[]  // just the percentage values!
  }[]
}
```

**MISMATCHES IDENTIFIED:**

| Backend | Frontend | Issue |
|---|---|---|
| `rows` (geo names) | `rows.bu` (BU names) | Wrong dimension! Backend provides geos, frontend expects BUs |
| `columns` (BU names) | `columns` (should be geo names) | Swapped dimensions |
| `cells[i][j].pct` | `cells[j]` | Backend nests in objects, frontend expects flat array of numbers |
| `cells[i][j].value` | (not used) | Extra field |
| `cells[i][j].is_material` | (not used) | Extra field, unused |

**CRITICAL ISSUE:** Heatmap dimensions are reversed between backend and frontend!

---

### 5. Variance Table (uses get_variance_list)

**Backend API Response** (`GET /variances/` or from dashboard summary)

From `get_variance_list()` in `service.py`:
```python
{
  "items": [
    {
      "variance_id": "var_123",
      "account_id": "acct_advisory",
      "account_name": "Advisory Fees",
      "bu_id": "bu_marsh",
      "period_id": "2026-06",
      "actual_amount": 18200.00,
      "comparator_amount": 16800.00,
      "variance_amount": 1400.00,
      "variance_pct": 8.33,
      "is_material": True,
      "is_netted": False,
      "is_trending": False,
      "pl_category": "Revenue",
      "narrative_oneliner": "Advisory growth from..."
    }
  ],
  "total_count": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Frontend Component Expects** (`VarianceTable`)
```typescript
{
  id: string
  account: string
  bu: string
  geo: string           // NOT PROVIDED BY BACKEND!
  variance: number      // dollars
  variancePct: number
  favorable: boolean    // NOT PROVIDED BY BACKEND!
  sparkData: number[]   // NOT PROVIDED BY BACKEND!
  type: 'material' | 'netted' | 'trending'
  status: 'approved' | 'reviewed' | 'draft'  // NOT PROVIDED BY BACKEND!
  edgeBadge?: 'edited' | 'New' | 'No budget' | 'synth'
  narrative: string
}
```

**MISMATCHES IDENTIFIED:**

| Backend Field | Frontend Expects | Issue |
|---|---|---|
| `variance_id` | `id` | Field name mismatch |
| `account_name` | `account` | Field name mismatch |
| `bu_id` | `bu` | Field name mismatch (but missing value) |
| `actual_amount` | (not used) | Extra field |
| `comparator_amount` | (not used) | Extra field |
| `variance_amount` | `variance` | Field name mismatch |
| `variance_pct` | `variancePct` | Field name mismatch |
| `is_material` | `type: 'material'` | Type mismatch: boolean → enum |
| `is_netted` | `type: 'netted'` | Type mismatch: boolean → enum |
| `is_trending` | `type: 'trending'` | Type mismatch: boolean → enum |
| `narrative_oneliner` | `narrative` | Field name mismatch |
| (missing) | `geo` | **CRITICAL: Backend doesn't provide geography** |
| (missing) | `favorable` | Backend doesn't provide favorability |
| (missing) | `sparkData` | Backend doesn't provide trend data |
| (missing) | `status` | Backend doesn't provide approval status |
| (missing) | `edgeBadge` | Backend doesn't provide edge badge |

---

## P&L PAGE

### P&L Statement

**Backend API Response** (`GET /pl/statement`)
```python
{
  "rows": [
    {
      "account_id": "acct_revenue",
      "account_name": "Revenue",
      "depth": 0,
      "is_calculated": False,
      "is_leaf": True,
      "actual": 52400.00,
      "comparator": 49800.00,
      "variance_amount": 2600.00,
      "variance_pct": 5.2,
      "is_material": True,
      "pl_category": "Revenue",
      "children": [...]
    }
  ],
  "period_id": "2026-06",
  "bu_id": None,
  "view_id": "MTD",
  "base_id": "BUDGET"
}
```

**Frontend Component Expects** (`PLGrid`)
```typescript
{
  id: string
  name: string
  depth: number
  isContainer?: boolean     // NOT PROVIDED BY BACKEND!
  children?: string[]       // Backend provides nested objects
  isLeaf?: boolean
  parentId?: string         // NOT PROVIDED BY BACKEND!
  isCalculated?: boolean
  isMajor?: boolean         // NOT PROVIDED BY BACKEND!
  actual: number
  budget: number            // not "comparator"
  signConvention: 'normal' | 'inverse'  // NOT PROVIDED BY BACKEND!
  status?: 'approved' | 'reviewed' | 'draft'
  type?: 'material' | 'trending' | 'netted'
  varianceId?: string
}
```

**MISMATCHES IDENTIFIED:**

| Backend Field | Frontend Expects | Issue |
|---|---|---|
| `account_id` | `id` | Field name mismatch |
| `account_name` | `name` | Field name mismatch |
| `depth` | `depth` | ✓ Match |
| `is_calculated` | `isCalculated` | Field name mismatch (is_ → camelCase) |
| `is_leaf` | `isLeaf` | Field name mismatch (is_ → camelCase) |
| `actual` | `actual` | ✓ Match |
| `comparator` | `budget` | Field name mismatch |
| `variance_amount` | (not used) | Extra field |
| `variance_pct` | (not used) | Extra field |
| `is_material` | `type: 'material'` | Type mismatch + field name |
| `pl_category` | (not used) | Extra field |
| `children` (list) | `children` (strings) | Structure mismatch: objects vs IDs |
| (missing) | `isContainer` | Backend doesn't mark containers |
| (missing) | `parentId` | Backend doesn't provide parent reference |
| (missing) | `isMajor` | Backend doesn't mark major lines |
| (missing) | `signConvention` | **CRITICAL: Backend doesn't provide sign convention** |
| (missing) | `status` | Backend doesn't provide workflow status |
| (missing) | `type` | Backend doesn't provide variance type |
| (missing) | `varianceId` | Backend doesn't provide variance ID |

---

## VARIANCE DETAIL

**Backend API Response** (`GET /variances/{variance_id}`)
```python
{
  "variance_id": "var_123",
  "period_id": "2026-06",
  "bu_id": "bu_marsh",
  "account_id": "acct_advisory",
  "account_name": "Advisory Fees",
  "geo_node_id": "geo_apac",
  "segment_node_id": "seg_xyz",
  "lob_node_id": "lob_xyz",
  "costcenter_node_id": "cc_xyz",
  "view_id": "MTD",
  "base_id": "BUDGET",
  "actual_amount": 18200.00,
  "comparator_amount": 16800.00,
  "variance_amount": 1400.00,
  "variance_pct": 8.33,
  "is_material": True,
  "is_netted": False,
  "is_trending": False,
  "pl_category": "Revenue",
  "variance_sign": "normal",
  "narratives": {
    "detail": "...",
    "midlevel": "...",
    "summary": "...",
    "oneliner": "...",
    "board": "..."
  },
  "narrative_source": "ai_generated",
  "decomposition": {
    "method": "volume_price_mix",
    "components": [...],
    "total_explained": 95.5,
    "residual": 4.5
  },
  "correlations": [
    {
      "correlation_id": "corr_123",
      "other_variance_id": "var_456",
      "correlation_score": 0.85,
      "dimension_overlap": ["bu", "geo"],
      "directional_match": True,
      "hypothesis": "...",
      "confidence": 0.92
    }
  ]
}
```

**Frontend Hook** (`useChat.ts` SSE events, `VarianceTable.tsx` modal)
Maps to `VarianceDetail`:
```typescript
{
  id: string
  account: string
  bu: string
  geo: string              // NOT PROVIDED BY BACKEND (only node_id)
  variance: number
  variancePct: number
  favorable: boolean       // NOT PROVIDED BY BACKEND
  type: 'material' | 'netted' | 'trending'
  status: 'approved' | 'reviewed' | 'draft'  // NOT PROVIDED!
  sparkData: number[]      // NOT PROVIDED!
  decomposition: Array<{ label: string; value: number; pct: number }>
  correlations: Array<{ ... }>  // Structure mismatch
  hypotheses: Array<{ text: string; confidence: 'High' | 'Medium' | 'Low'; feedback: -1 | 0 | 1 }>
  narratives: { detail: string; midlevel: string; summary: string; board: string }
  isEdited: boolean        // NOT PROVIDED!
  isSynthesized: boolean   // NOT PROVIDED!
  isNew: boolean           // NOT PROVIDED!
  noBudget: boolean        // NOT PROVIDED!
  noPriorYear: boolean     // NOT PROVIDED!
  edgeBadge?: string       // NOT PROVIDED!
  narrative: string        // Not in backend narratives object
}
```

**CRITICAL MISMATCHES:**

| Backend | Frontend | Issue |
|---|---|---|
| `geo_node_id` | `geo` (name) | Backend provides ID, frontend needs display name |
| `variance_amount` | `variance` | Field name mismatch |
| `variance_pct` | `variancePct` | Field name mismatch |
| `is_material`, `is_netted`, `is_trending` | `type` enum | Boolean fields → single enum field |
| `decomposition.components` | `decomposition[].label/value/pct` | Structure mismatch |
| `narratives` object | `narrative` string | Backend provides structured object, frontend expects single string |
| `correlations` | `correlations` | Fields in backend don't match expected structure |
| (missing) | `favorable` | Backend doesn't provide favorability |
| (missing) | `status` | Backend doesn't provide workflow status |
| (missing) | `sparkData` | Backend doesn't provide trend data |
| (missing) | `hypotheses` | Backend doesn't have formal hypothesis structure |
| (missing) | `isEdited`, `isSynthesized`, `isNew`, `noBudget`, `noPriorYear` | Backend doesn't track edge badges |

---

## REVIEW QUEUE

### Backend Response (`GET /review/queue`)
```python
{
  "items": [
    {
      "variance_id": "var_123",
      "account_name": "Advisory Fees",
      "period_label": "Jun 2026",
      "variance_amount": 1400.00,
      "variance_pct": 8.33,
      "current_status": "AI_DRAFT",
      "narrative_preview": "Advisory fees exceeded...",
      "sla_hours_remaining": 24.5
    }
  ],
  "total": 20,
  "page": 1,
  "page_size": 50
}
```

### Frontend Hook Expects (`useReviewQueue.ts`)
```typescript
{
  id: string               // NOT PROVIDED (only variance_id)
  account: string          // Field name mismatch
  bu: string               // NOT PROVIDED!
  geo: string              // NOT PROVIDED!
  variance: number         // Field name mismatch
  variancePct: number      // Field name mismatch
  favorable: boolean       // NOT PROVIDED!
  type: 'material' | 'netted' | 'trending'  // NOT PROVIDED!
  status: 'approved' | 'reviewed' | 'draft'  // Status name mismatch
  sla: number              // Field name mismatch (sla_hours_remaining)
  sparkData: number[]      // NOT PROVIDED!
  edgeBadge?: string
  isEdited: boolean        // NOT PROVIDED!
  isSynthesized: boolean
  synthCount?: number
  narratives: { detail: string; ... }  // NOT PROVIDED! Only preview
  decomposition: Array<{ label: string; value: number; pct: number }>  // NOT PROVIDED!
  hypotheses: Array<{ text: string; ... }>  // NOT PROVIDED!
  varianceId?: string      // Matches variance_id
}
```

**MISMATCHES IDENTIFIED:**

| Backend | Frontend | Issue |
|---|---|---|
| `variance_id` | `id` + `varianceId` | Multiple ID fields; naming inconsistency |
| `account_name` | `account` | Field name mismatch |
| `variance_amount` | `variance` | Field name mismatch |
| `variance_pct` | `variancePct` | Field name mismatch |
| `current_status` | `status` | Status value mismatch: "AI_DRAFT" vs "draft" |
| `sla_hours_remaining` | `sla` | Field name mismatch; type mismatch (float vs int) |
| `narrative_preview` | `narratives.detail` | Backend provides preview string, frontend needs full narratives object |
| (missing) | `bu`, `geo` | **CRITICAL: Backend doesn't provide business unit or geography** |
| (missing) | `favorable` | Backend doesn't provide favorability |
| (missing) | `type` | Backend doesn't provide variance type |
| (missing) | `sparkData` | Backend doesn't provide trend data |
| (missing) | `isEdited`, `isSynthesized` | Backend doesn't track edit status |
| (missing) | `decomposition`, `hypotheses` | Backend doesn't provide decomposition or hypotheses |

---

## APPROVAL QUEUE

### Backend Response (`GET /approval/queue`)
```python
{
  "items": [
    {
      "variance_id": "var_123",
      "account_name": "Advisory Fees",
      "period_label": "Jun 2026",
      "variance_amount": 1400.00,
      "variance_pct": 8.33,
      "analyst_name": "Sarah Chen",
      "reviewed_narrative": "Advisory fees exceeded..."
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 50
}
```

### Frontend Hook Expects (`useApprovalQueue.ts`)
```typescript
{
  id: string               // NOT PROVIDED (only variance_id)
  account: string          // Field name mismatch
  bu: string               // NOT PROVIDED!
  geo: string              // NOT PROVIDED!
  variance: number         // Field name mismatch
  variancePct: number      // Field name mismatch
  favorable: boolean       // NOT PROVIDED!
  status: 'reviewed' | 'approved'
  assignedAnalyst: string  // ✓ Matches analyst_name
  isEdited: boolean        // NOT PROVIDED!
  varianceId?: string      // ✓ Matches variance_id
}
```

**MISMATCHES IDENTIFIED:**

| Backend | Frontend | Issue |
|---|---|---|
| `variance_id` | `id` + `varianceId` | Inconsistent ID field naming |
| `account_name` | `account` | Field name mismatch |
| `variance_amount` | `variance` | Field name mismatch |
| `variance_pct` | `variancePct` | Field name mismatch |
| `analyst_name` | `assignedAnalyst` | Field name mismatch |
| `reviewed_narrative` | (not used) | Extra field |
| (missing) | `bu`, `geo` | **CRITICAL: Backend doesn't provide BU or geography** |
| (missing) | `favorable` | Backend doesn't provide favorability |
| (missing) | `status` | Backend returns status but type values might not match |
| (missing) | `isEdited` | Backend doesn't track edit status |

---

## CHAT & SSE STREAMING

### Backend SSE Event Payloads (`services/gateway/streaming/events.py`)

**Token Event:**
```python
{ "text": "partial text" }
```

**Data Table Event:**
```python
{
  "title": "...",
  "columns": ["col1", "col2"],
  "rows": [[val1, val2], ...],
  "footer": "..."
}
```

**Mini Chart Event:**
```python
{
  "chart_type": "bar" | "line" | "waterfall",
  "title": "...",
  "data": [{"key": val, ...}, ...]
}
```

**Suggestion Event:**
```python
{ "suggestions": ["q1", "q2", ...] }
```

**Confidence Event:**
```python
{
  "score": 0.92,
  "label": "high" | "medium" | "low"
}
```

**Netting Alert Event:**
```python
{
  "node_id": "...",
  "node_name": "...",
  "net_variance": 1234.56,
  "gross_variance": 5678.90,
  "netting_ratio": 35.5,
  "message": "..."
}
```

**Review Status Event:**
```python
{
  "variance_id": "...",
  "status": "...",
  "message": "..."
}
```

### Frontend SSE Hook (`useSSE.ts`)

**Expected Event Structure:**
```typescript
{
  type: 'token' | 'data_table' | 'mini_chart' | 'suggestion' | 'confidence' | 'netting_alert' | 'review_status' | 'done' | 'error',
  payload: any
}
```

**CRITICAL ISSUE:** Backend sends properly typed Pydantic models. Frontend's `useSSE` hook expects generic SSE events with `type` and `payload` fields. The hook is generic and should work IF the backend correctly serializes and streams the events.

**Potential Issues:**
1. Backend wrapper (`SSEEvent.to_sse()`) should properly serialize each event type
2. Frontend's `addEventListener` for typed events (token, data_table, etc.) should work
3. However, if backend is NOT using the `SSEEvent` wrapper correctly, frontend receives malformed events

---

## SUMMARY TABLE

### Critical Missing Fields (Backend doesn't provide, Frontend needs)

| Field | Used In | Impact |
|---|---|---|
| `id` | KPI Cards, Variances, Review, Approval | No unique identifier for UI operations |
| `geo` / geography | Variance Table, Heatmap, Review, Approval | Cannot display geographic context |
| `favorable` | Variances, Review | Cannot determine color coding |
| `sparkData` | KPI Cards, Variance Table, Review | Cannot show trend sparklines |
| `status` (workflow) | Variance Table, P&L | Cannot show approval workflow status |
| `type` (material/trending/netted) | Variance Table | Cannot show variance classification |
| `signConvention` | P&L Statement | Cannot compute favorable direction |
| `prefix`, `suffix` | KPI Cards | Cannot format display values |
| `comparatorLabel` | KPI Cards | Cannot show formatted comparison |
| `month` format | Trend Chart | Cannot render period labels correctly |
| `isContainer`, `parentId`, `isMajor` | P&L | Cannot render hierarchy correctly |
| `hypotheses` structured | Variance Detail, Review | Cannot display decomposition hypotheses |

### Field Name Mismatches (Mapping Required)

| Backend Field | Frontend Field | Count |
|---|---|---|
| `metric_name` → `label` | KPI Cards | 1 |
| `account_id` / `account_name` → `account` | Multiple | 5 |
| `bu_id` → `bu` | Multiple | 5 |
| `variance_amount` → `variance` | Variance Table, Review, Approval | 3 |
| `variance_pct` → `variancePct` | Variance Table, Review, Approval | 3 |
| `is_*` → `camelCase` | P&L (`isCalculated`, `isLeaf`) | 2 |
| `comparator` → `budget` | KPI Cards, Trends, P&L | 3 |
| `actual_amount` → `actual` | Various | Multiple |
| `sla_hours_remaining` → `sla` | Review Queue | 1 |
| `analyst_name` → `assignedAnalyst` | Approval Queue | 1 |
| `current_status` → `status` | Review Queue | 1 |
| `narrative_oneliner` / `narrative_preview` → `narrative` | Variance Table, Review | 2 |

### Type/Structure Mismatches

| Issue | Location | Severity |
|---|---|---|
| Boolean flags → single enum field (`is_material` + `is_netted` + `is_trending` → `type`) | Variance Table, P&L | HIGH |
| Dimension swap (geos ↔ BUs in heatmap) | Heatmap | CRITICAL |
| Nested objects vs flat arrays (`cells[i][j].pct` vs `cells[j]`) | Heatmap | HIGH |
| Nested objects vs strings (`children: [{...}]` vs `children: ["id1", "id2"]`) | P&L | MEDIUM |
| Narrative structure (object keys vs single string) | Variance Detail | MEDIUM |
| Status values ("AI_DRAFT" vs "draft") | Review Queue | MEDIUM |

---

## RECOMMENDATIONS

### Quick Wins (Field Renaming Only)
1. Rename backend fields to match frontend expectations (metric_name → label, etc.)
2. Add missing ID generation/mapping in API responses
3. Format month labels in trends API (YYYY-MM → 3-letter month)

### Medium Complexity (Type Mapping)
1. Create boolean flags → type enum mapping in hook
2. Convert is_material/is_netted/is_trending → single "type" field
3. Add status field from review store to variance responses
4. Convert sla_hours_remaining to integer sla field

### High Complexity (Data Augmentation)
1. **Add geography data** to variance responses (join with dim_hierarchy)
2. **Add favorability calculation** (use variance_sign from account metadata)
3. **Add sparkData generation** (fetch from trend data for each variance)
4. **Add edge badges** (track synthesis status, edits, new flags)
5. **Add hypotheses structure** (extract from decomposition components)
6. **Fix heatmap dimensions** (swap rows/columns to match frontend expectations)
7. **Add sign convention** to P&L rows (use account metadata)
8. **Add container/parent metadata** to P&L (track hierarchy structure)

### Architectural Fix
1. Implement comprehensive data shape contracts (Pydantic models) that exactly match frontend TypeScript interfaces
2. Add API integration tests that validate response shapes against frontend expectations
3. Create data transformation layer in hooks to normalize API responses before use

