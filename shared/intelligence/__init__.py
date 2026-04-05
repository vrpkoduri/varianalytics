"""Intelligence dimensions for variance narrative enrichment.

Four Quick Intelligence dimensions (Phase 3F):
1. Materiality Context — "0.3% of revenue but 8% of EBITDA"
2. Risk Classification — "FX-driven: uncontrollable"
3. Cumulative Projection — "Full-year impact: $3.2M"
4. Variance Persistence — "Decaying at 0.5pp/month"
"""

from shared.intelligence.materiality import compute_materiality_context
from shared.intelligence.persistence import compute_persistence
from shared.intelligence.projection import compute_cumulative_projection
from shared.intelligence.risk import classify_risk

__all__ = [
    "compute_materiality_context",
    "classify_risk",
    "compute_cumulative_projection",
    "compute_persistence",
]
