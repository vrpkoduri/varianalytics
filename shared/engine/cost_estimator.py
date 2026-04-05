"""Cost estimation for Process B (Intelligence & Narratives).

Provides upfront cost/time estimates before committing to an AI Agent run.
Based on empirical data from production runs on the synthetic dataset.

Pricing assumptions (Claude Sonnet):
    - Input:  ~$3 per million tokens
    - Output: ~$15 per million tokens
    - Average prompt: ~2,000 input tokens, ~500 output tokens
"""

from __future__ import annotations

from typing import Any, Optional


# Empirical constants from production runs
_AVG_INPUT_TOKENS_PER_CALL = 2_000
_AVG_OUTPUT_TOKENS_PER_CALL = 500
_INPUT_COST_PER_1M = 3.00   # USD per million input tokens
_OUTPUT_COST_PER_1M = 15.00  # USD per million output tokens
_AVG_SECONDS_PER_LLM_CALL = 3.5  # Average latency per call
_CONCURRENCY = 10  # Parallel LLM calls (from pass5 Semaphore)


def estimate_process_b_cost(
    material_count: int,
    mode: str = "llm",
    stages: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Estimate LLM cost and time for a Process B run.

    Args:
        material_count: Number of material variances (from Process A).
        mode: 'llm' or 'template'.
        stages: Which narrative stages to run. Default ['all'].
            Options: 'leaves', 'parents', 'sections', 'executive', 'all'.

    Returns:
        Dict with estimated_calls, estimated_cost_usd,
        estimated_time_minutes, and breakdown.
    """
    if stages is None:
        stages = ["all"]

    if mode == "template":
        return {
            "estimated_calls": 0,
            "estimated_cost_usd": 0.0,
            "estimated_time_minutes": material_count / 1000 * 0.5,  # ~30s per 1K rows
            "mode": "template",
            "breakdown": {
                "leaves": 0,
                "parents": 0,
                "sections": 0,
                "executive": 0,
                "correlation_hypotheses": 0,
            },
        }

    if material_count == 0:
        return {
            "estimated_calls": 0,
            "estimated_cost_usd": 0.0,
            "estimated_time_minutes": 0.0,
            "mode": "llm",
            "breakdown": {
                "leaves": 0, "parents": 0, "sections": 0,
                "executive": 0, "correlation_hypotheses": 0,
            },
        }

    # Estimate call counts by stage
    # Empirical ratios from synthetic dataset:
    #   ~60% leaf variances, ~40% parent/rollup variances
    #   5 P&L sections, 1 executive summary
    #   Top 20 correlation pairs → 20 hypothesis calls
    leaf_count = int(material_count * 0.6)
    parent_count = int(material_count * 0.4)
    section_count = 5
    exec_count = 1
    hypothesis_count = min(20, material_count // 10)  # Top 20 or 10% of material

    breakdown = {
        "leaves": leaf_count if _stage_enabled("leaves", stages) else 0,
        "parents": parent_count if _stage_enabled("parents", stages) else 0,
        "sections": section_count if _stage_enabled("sections", stages) else 0,
        "executive": exec_count if _stage_enabled("executive", stages) else 0,
        "correlation_hypotheses": hypothesis_count,
    }

    total_calls = sum(breakdown.values())

    # Cost calculation
    total_input_tokens = total_calls * _AVG_INPUT_TOKENS_PER_CALL
    total_output_tokens = total_calls * _AVG_OUTPUT_TOKENS_PER_CALL
    cost_usd = (
        (total_input_tokens / 1_000_000) * _INPUT_COST_PER_1M
        + (total_output_tokens / 1_000_000) * _OUTPUT_COST_PER_1M
    )

    # Time calculation (parallel with concurrency limit)
    wall_seconds = (total_calls / _CONCURRENCY) * _AVG_SECONDS_PER_LLM_CALL
    wall_minutes = wall_seconds / 60

    return {
        "estimated_calls": total_calls,
        "estimated_cost_usd": round(cost_usd, 2),
        "estimated_time_minutes": round(wall_minutes, 1),
        "mode": "llm",
        "breakdown": breakdown,
        "token_estimate": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
    }


def _stage_enabled(stage: str, stages: list[str]) -> bool:
    """Check if a stage is enabled in the requested stage list."""
    return "all" in stages or stage in stages


def format_cost_summary(estimate: dict[str, Any]) -> str:
    """Format a cost estimate as a human-readable summary string.

    Args:
        estimate: Output from estimate_process_b_cost().

    Returns:
        Multi-line summary string.
    """
    lines = [
        f"Process B Cost Estimate ({estimate['mode']} mode)",
        f"  AI Agent calls: {estimate['estimated_calls']:,}",
        f"  Estimated cost: ${estimate['estimated_cost_usd']:.2f}",
        f"  Estimated time: {estimate['estimated_time_minutes']:.1f} minutes",
    ]

    if estimate.get("breakdown"):
        lines.append("  Breakdown:")
        for stage, count in estimate["breakdown"].items():
            if count > 0:
                lines.append(f"    {stage}: {count:,} calls")

    return "\n".join(lines)


def estimate_cascade_cost(
    chain: list[dict[str, Any]],
    mode: str = "template",
) -> dict[str, Any]:
    """Estimate cost for a specific cascade regeneration chain.

    Args:
        chain: Cascade chain from get_cascade_chain_typed().
        mode: 'llm' or 'template'.

    Returns:
        Dict with estimated_calls, estimated_cost_usd,
        estimated_time_seconds.
    """
    if not chain or mode == "template":
        return {
            "estimated_calls": 0,
            "estimated_cost_usd": 0.0,
            "estimated_time_seconds": len(chain) * 2,  # ~2s per template step
            "mode": mode,
            "steps": len(chain),
        }

    # LLM: one call per parent variance, one per section, one for exec
    parent_count = sum(1 for c in chain if c.get("type") == "parent_variance")
    section_count = sum(1 for c in chain if c.get("type") == "section")
    exec_count = sum(1 for c in chain if c.get("type") == "executive")

    total_calls = parent_count + section_count + exec_count
    total_input = total_calls * _AVG_INPUT_TOKENS_PER_CALL
    total_output = total_calls * _AVG_OUTPUT_TOKENS_PER_CALL
    cost = (
        (total_input / 1_000_000) * _INPUT_COST_PER_1M
        + (total_output / 1_000_000) * _OUTPUT_COST_PER_1M
    )
    time_seconds = total_calls * _AVG_SECONDS_PER_LLM_CALL

    return {
        "estimated_calls": total_calls,
        "estimated_cost_usd": round(cost, 4),
        "estimated_time_seconds": round(time_seconds, 1),
        "mode": "llm",
        "steps": len(chain),
        "breakdown": {
            "parents": parent_count,
            "sections": section_count,
            "executive": exec_count,
        },
    }
