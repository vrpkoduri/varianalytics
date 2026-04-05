"""Intelligence dimensions for variance narrative enrichment.

15 dimensions across 3 phases:

Phase 3F — Quick Intelligence (4):
  1. Materiality Context
  2. Risk Classification
  3. Cumulative Projection
  4. Variance Persistence

Phase 3G — Core Intelligence (6):
  5. Cross-Dimensional Pivot
  6. Peer Comparison
  7. Causal Chains
  8. Multi-Year Patterns
  9. Leading/Lagging
  10. Theme Clustering

Phase 3H — Quality + Context (5):
  11. Narrative Coherence
  12. Anomaly Detection
  13. Budget Assumptions
  14. Market Context
  15. Quality Scoring (enhanced confidence)
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

# Phase 3H
from shared.intelligence.anomaly import compute_anomaly_score
from shared.intelligence.budget_assumptions import compute_budget_gap
from shared.intelligence.coherence import compute_narrative_coherence
from shared.intelligence.market_context import compute_market_context

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
    # Phase 3H
    "compute_anomaly_score",
    "compute_budget_gap",
    "compute_market_context",
    "compute_narrative_coherence",
]
