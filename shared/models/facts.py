"""Pydantic schemas for fact tables."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.models.enums import (
    ComparisonBase,
    DecompositionMethod,
    NarrativeLevel,
    NarrativeSource,
    NettingCheckType,
    ReviewStatus,
    TrendRuleType,
    ViewType,
)


class FactFinancials(BaseModel):
    """Base fact table — MTD atomic grain.

    Stores actual, budget, forecast, and prior year amounts at the leaf level.
    Partitioned by fiscal_year, Z-ordered on (period_id, bu_id, account_id).
    """

    period_id: str = Field(..., description="YYYY-MM")
    bu_id: str
    account_id: str = Field(..., description="Leaf accounts only, not calculated")
    geo_node_id: str
    segment_node_id: str
    lob_node_id: str
    costcenter_node_id: str
    fiscal_year: int

    actual_amount: float = Field(0.0, description="Actual MTD amount (USD)")
    budget_amount: float = Field(0.0, description="Budget MTD amount (USD)")
    forecast_amount: Optional[float] = Field(None, description="Forecast MTD (NULL if no forecast)")
    prior_year_amount: Optional[float] = Field(None, description="Prior year actual MTD")

    actual_local_amount: Optional[float] = Field(None, description="Actual in local currency")
    local_currency: Optional[str] = Field(None, description="ISO currency code")
    budget_fx_rate: Optional[float] = Field(None, description="Budget FX rate to USD")
    actual_fx_rate: Optional[float] = Field(None, description="Actual FX rate to USD")


class FactVarianceMaterial(BaseModel):
    """Materialized variance fact — persisted only for above-threshold variances.

    5 narrative levels + synthesis tracking. Z-ordered on (period_id, bu_id, view_id, base_id).
    """

    variance_id: str = Field(..., description="Unique variance identifier")
    period_id: str
    bu_id: str
    account_id: str
    geo_node_id: str
    segment_node_id: str
    lob_node_id: str
    costcenter_node_id: str
    view_id: ViewType
    base_id: ComparisonBase

    actual_amount: float
    comparator_amount: float
    variance_amount: float
    variance_pct: Optional[float] = Field(None, description="NULL if comparator=0")

    is_material: bool = Field(False)
    is_netted: bool = Field(False)
    is_trending: bool = Field(False)

    narrative_detail: Optional[str] = Field(None, description="Analyst level (3-5 sentences)")
    narrative_midlevel: Optional[str] = Field(None, description="BU Leader (2-3 sentences)")
    narrative_summary: Optional[str] = Field(None, description="CFO (1-2 sentences)")
    narrative_oneliner: Optional[str] = Field(None, description="Dashboard one-liner")
    narrative_board: Optional[str] = Field(None, description="Board level (on-demand)")
    narrative_source: Optional[NarrativeSource] = None

    synthesis_child_ids: Optional[list[str]] = Field(
        None, description="Child variance IDs used in synthesis"
    )

    engine_run_id: str = Field(..., description="Links to audit_log")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactDecomposition(BaseModel):
    """Variance decomposition results."""

    variance_id: str
    method: DecompositionMethod
    components: dict[str, Any] = Field(
        ..., description="Decomposition components as JSON, e.g. {'volume': 1200, 'price': -300}"
    )
    total_explained: float = Field(..., description="Sum of components")
    residual: float = Field(0.0, description="Unexplained portion")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactNettingFlags(BaseModel):
    """Netting detection flags for summary nodes below threshold."""

    netting_id: str
    parent_node_id: str
    parent_dimension: str
    check_type: NettingCheckType
    net_variance: float = Field(..., description="Net (small) variance at parent")
    gross_variance: float = Field(..., description="Sum of absolute child variances")
    netting_ratio: float = Field(..., description="gross / abs(net)")
    child_details: list[dict[str, Any]] = Field(
        ..., description="List of child variances that net out"
    )
    period_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactTrendFlags(BaseModel):
    """Trend detection flags."""

    trend_id: str
    account_id: str
    dimension_key: str = Field(..., description="Concatenated dimension context")
    rule_type: TrendRuleType
    consecutive_periods: int = Field(0, description="Number of consecutive periods in trend")
    cumulative_amount: float = Field(0.0, description="Cumulative variance over trend period")
    direction: str = Field(..., description="'increasing' or 'decreasing'")
    period_details: list[dict[str, Any]] = Field(
        ..., description="Period-by-period trend data"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactCorrelations(BaseModel):
    """Pairwise correlation and root cause hypotheses."""

    correlation_id: str
    variance_id_a: str
    variance_id_b: str
    correlation_score: float = Field(..., description="0.0 to 1.0 correlation strength")
    dimension_overlap: list[str] = Field(..., description="Shared dimension values")
    directional_match: bool = Field(..., description="Do they move in same/opposite direction?")
    hypothesis: Optional[str] = Field(None, description="LLM-generated root cause hypothesis")
    confidence: Optional[float] = Field(None, description="0.0 to 1.0 hypothesis confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactReviewStatus(BaseModel):
    """Review workflow tracking per variance."""

    review_id: str
    variance_id: str
    status: ReviewStatus = Field(default=ReviewStatus.AI_DRAFT)
    assigned_analyst: Optional[str] = None
    reviewer: Optional[str] = None
    approver: Optional[str] = None

    original_narrative: Optional[str] = Field(None, description="AI-generated narrative")
    edited_narrative: Optional[str] = Field(None, description="Analyst-edited narrative")
    edit_diff: Optional[str] = Field(None, description="Diff between original and edited")

    hypothesis_feedback: Optional[dict[str, Any]] = Field(
        None, description="Thumbs up/down per hypothesis"
    )
    review_notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None


class KnowledgeCommentaryHistory(BaseModel):
    """Approved commentaries for RAG retrieval."""

    commentary_id: str
    variance_id: str
    account_id: str
    period_id: str
    bu_id: str

    narrative_text: str = Field(..., description="Approved narrative text")
    narrative_level: NarrativeLevel
    embedding_vector: Optional[list[float]] = Field(
        None, description="Vector embedding for similarity search"
    )

    variance_amount: float
    variance_pct: Optional[float]
    context_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for RAG matching"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: str


class AuditLog(BaseModel):
    """Enterprise audit trail — every computation, LLM call, review action, data access."""

    audit_id: str
    event_type: str = Field(
        ..., description="engine_run, llm_call, review_action, data_access, etc."
    )
    user_id: Optional[str] = None
    service: str = Field(..., description="gateway, computation, or reports")
    action: str = Field(..., description="Specific action taken")
    details: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
