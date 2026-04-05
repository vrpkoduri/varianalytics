"""Intelligence dimensions for variance narrative enrichment.

Phase 3F — Quick Intelligence (4 dimensions):
1. Materiality Context — "0.3% of revenue but 8% of EBITDA"
2. Risk Classification — "FX-driven: uncontrollable"
3. Cumulative Projection — "Full-year impact: $3.2M"
4. Variance Persistence — "Decaying at 0.5pp/month"

Phase 3G — Core Intelligence (6 dimensions):
5. Cross-Dimensional Pivot — "85% in EMEA geography"
6. Peer Comparison — "Systemic — 4/5 BUs same direction"
7. Causal Chains — "Linked to Headcount (r=0.87)"
8. Multi-Year Patterns — "Same Q2 pattern in 2024 and 2025"
9. Leading/Lagging — "Comp moves 2 months before Revenue"
10. Theme Clustering — "APAC Revenue Weakness (12 variances)"
"""

# Phase 3F
from shared.intelligence.materiality import compute_materiality_context
from shared.intelligence.persistence import compute_persistence
from shared.intelligence.projection import compute_cumulative_projection
from shared.intelligence.risk import classify_risk

# Phase 3G
from shared.intelligence.causal_chains import compute_causal_chain
from shared.intelligence.clustering import compute_theme_clusters
from shared.intelligence.leading_lagging import compute_leading_lagging
from shared.intelligence.multi_year import compute_multi_year_pattern
from shared.intelligence.peer_comparison import compute_peer_comparison
from shared.intelligence.pivot import compute_dimensional_pivot

__all__ = [
    # Phase 3F
    "compute_materiality_context",
    "classify_risk",
    "compute_cumulative_projection",
    "compute_persistence",
    # Phase 3G
    "compute_dimensional_pivot",
    "compute_peer_comparison",
    "compute_causal_chain",
    "compute_multi_year_pattern",
    "compute_leading_lagging",
    "compute_theme_clusters",
]
