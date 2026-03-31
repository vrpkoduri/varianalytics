"""Synthesis endpoints — trigger and monitor narrative synthesis.

Prefix: /synthesis

Synthesis runs OUTSIDE the main engine pipeline. It is triggered
when an analyst approves a variance, aggregating approved child
commentaries bottom-up into parent summary narratives.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


# ---------------------------------------------------------------------------
# POST /synthesis/trigger/{variance_id}
# ---------------------------------------------------------------------------

@router.post("/trigger/{variance_id}")
async def trigger_synthesis(variance_id: str, request: Request) -> dict[str, Any]:
    """Trigger bottom-up narrative synthesis for an approved variance.

    Preconditions:
    - The variance must have review_status = APPROVED in fact_review_status.
    - All child variances in the hierarchy should be ANALYST_REVIEWED
      or APPROVED for complete synthesis.

    The synthesis process:
    1. Collect approved child commentaries from fact_review_status.
    2. Aggregate via LLM into parent midlevel/summary narratives.
    3. Update fact_variance_material with synthesized narratives.
    4. Log to audit_log.
    """
    ds = getattr(request.app.state, "data_service", None)
    llm_client = getattr(request.app.state, "llm_client", None)
    rag_retriever = getattr(request.app.state, "rag_retriever", None)

    # Get child commentaries from data service
    from shared.data.loader import DataLoader

    loader = DataLoader("data/output")
    dim_account = loader.load_table("dim_account")
    vm = loader.load_table("fact_variance_material")

    # Resolve account from variance_id if needed
    target_account = variance_id
    parent_row = dim_account[dim_account["account_id"] == variance_id]
    if parent_row.empty:
        # variance_id is not an account — try to find the account from the variance
        var_row = vm[vm["variance_id"] == variance_id]
        if var_row.empty:
            return {
                "variance_id": variance_id,
                "status": "error",
                "message": "Variance not found",
            }
        target_account = str(var_row.iloc[0].get("account_id", variance_id))
        parent_row = dim_account[dim_account["account_id"] == target_account]

    children = dim_account[dim_account["parent_id"] == target_account]
    child_ids = children["account_id"].tolist()

    # Get commentaries for child variances
    child_variances = vm[vm["account_id"].isin(child_ids)]
    child_commentaries = []
    for _, row in child_variances.iterrows():
        child_commentaries.append(
            {
                "variance_id": row.get("variance_id", ""),
                "account_id": row.get("account_id", ""),
                "narrative_detail": row.get("narrative_detail", ""),
                "narrative_midlevel": row.get("narrative_midlevel", ""),
            }
        )

    if not child_commentaries:
        return {
            "variance_id": variance_id,
            "status": "no_children",
            "message": "No child variances found",
        }

    # Run synthesis
    from services.computation.synthesis.narrative_synthesis import synthesize_narratives

    result = await synthesize_narratives(
        variance_id=variance_id,
        child_commentaries=child_commentaries,
        llm_client=llm_client,
        rag_retriever=rag_retriever,
    )

    return {
        "variance_id": variance_id,
        "status": result.status,
        "child_count": result.child_count,
        "narratives": result.narratives_synthesized,
        "error": result.error,
    }


# ---------------------------------------------------------------------------
# GET /synthesis/status/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/status/{variance_id}")
async def get_synthesis_status(variance_id: str) -> dict[str, Any]:
    """Check the synthesis status for a given variance.

    Returns current synthesis state: pending, in_progress, completed,
    or failed, along with timestamps and any error details.
    """
    # TODO: query synthesis job status from persistent store
    return {
        "variance_id": variance_id,
        "synthesis_status": "not_started",
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
