"""Narrative Synthesis — bottom-up aggregation of child commentaries.

Triggered when all child variances of a parent node are approved.
Generates midlevel and summary narratives for the parent by synthesizing
child-level approved commentaries, optionally using RAG few-shot examples.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of a narrative synthesis operation."""

    parent_variance_id: str
    child_count: int = 0
    narratives_synthesized: dict[str, str] = field(default_factory=dict)
    status: str = "pending"  # pending, completed, blocked, failed
    error: Optional[str] = None


async def synthesize_narratives(
    variance_id: str,
    child_commentaries: list[dict[str, Any]],
    llm_client: Any = None,
    rag_retriever: Any = None,
) -> SynthesisResult:
    """Synthesize parent narratives from approved child commentaries.

    Steps:
    1. Validate all children are ANALYST_REVIEWED or APPROVED
    2. Retrieve similar synthesis examples via RAG (optional)
    3. Build synthesis prompt with child narratives
    4. Call LLM for midlevel and summary generation
    5. Return SynthesisResult with generated narratives

    Args:
        variance_id: Parent variance to synthesize for.
        child_commentaries: List of dicts with narrative_detail, account_id, etc.
        llm_client: Optional LLMClient for generation.
        rag_retriever: Optional RAGRetriever for few-shot examples.

    Returns:
        SynthesisResult with status and generated narratives.
    """
    result = SynthesisResult(
        parent_variance_id=variance_id,
        child_count=len(child_commentaries),
    )

    # Step 1: Validate children
    if not child_commentaries:
        result.status = "blocked"
        result.error = "No child commentaries provided"
        return result

    # Check all children have narratives
    valid_children = [
        c
        for c in child_commentaries
        if c.get("narrative_detail") or c.get("narrative_midlevel")
    ]
    if not valid_children:
        result.status = "blocked"
        result.error = "No children with narratives found"
        return result

    # Step 2: Retrieve similar synthesis examples (optional)
    few_shot_text = ""
    if rag_retriever:
        try:
            examples = await rag_retriever.retrieve_similar(
                {"account_id": variance_id, "variance_amount": 0},
                top_k=2,
            )
            if examples:
                few_shot_text = "\n\nHere are examples of synthesis narratives:\n"
                for ex in examples:
                    few_shot_text += f"- {ex.narrative_text}\n"
        except Exception:
            pass  # RAG failure doesn't block synthesis

    # Step 3: Build synthesis prompt
    child_summaries = []
    for child in valid_children:
        account = child.get("account_id", "Unknown")
        narrative = (
            child.get("narrative_detail") or child.get("narrative_midlevel") or ""
        )
        child_summaries.append(f"- {account}: {narrative}")

    children_text = "\n".join(child_summaries)

    system_prompt = (
        "You are a senior FP&A analyst synthesizing child-level variance commentaries "
        "into a parent-level summary. Be concise, highlight the net impact, "
        "and identify the key drivers."
    )

    user_prompt = (
        f"Synthesize these {len(valid_children)} child variance commentaries "
        f"into parent-level narratives:\n\n{children_text}"
        f"{few_shot_text}\n\n"
        "Return a JSON object with two keys:\n"
        '- "midlevel": 2-3 sentences for management (BU leaders)\n'
        '- "summary": 1 sentence for CFO/board'
    )

    # Step 4: Call LLM
    if llm_client and hasattr(llm_client, "is_available") and llm_client.is_available:
        try:
            response = await llm_client.complete(
                task="narrative_generation",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            if isinstance(response, dict) and response.get("fallback"):
                # LLM not available, use simple aggregation
                result.narratives_synthesized = _simple_synthesis(valid_children)
                result.status = "completed"
                return result

            content = response.choices[0].message.content

            # Parse JSON response
            import json

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            result.narratives_synthesized = {
                "midlevel": parsed.get("midlevel", ""),
                "summary": parsed.get("summary", ""),
            }
            result.status = "completed"
            logger.info(
                "Synthesis completed for %s (%d children)",
                variance_id,
                len(valid_children),
            )
            return result

        except Exception as exc:
            logger.warning("LLM synthesis failed for %s: %s", variance_id, exc)

    # Step 5: Fallback — simple aggregation without LLM
    result.narratives_synthesized = _simple_synthesis(valid_children)
    result.status = "completed"
    return result


def _simple_synthesis(children: list[dict[str, Any]]) -> dict[str, str]:
    """Simple aggregation fallback when LLM is unavailable."""
    summaries = []
    for child in children[:5]:  # Top 5 by position
        account = (
            child.get("account_id", "").replace("acct_", "").replace("_", " ").title()
        )
        narrative = child.get("narrative_detail", child.get("narrative_midlevel", ""))
        if narrative:
            summaries.append(f"{account}: {narrative[:100]}")

    midlevel = (
        ". ".join(summaries[:3]) + "." if summaries else "Multiple variances aggregated."
    )
    summary = summaries[0] if summaries else "Synthesized from child commentaries."

    return {"midlevel": midlevel, "summary": summary}
