"""Configuration endpoints.

Expose and update materiality thresholds and LLM model-routing configuration.
Changes are persisted to YAML config files and pushed to the computation engine.
"""

from typing import Any, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/config", tags=["config"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ThresholdConfig(BaseModel):
    """Materiality threshold configuration."""

    absolute_amount: float = Field(50_000, description="Absolute $ threshold")
    percentage: float = Field(0.05, description="Percentage threshold (5%)")
    netting_tolerance: float = Field(
        0.10, description="Netting offset tolerance (10%)"
    )
    trend_consecutive_months: int = Field(
        3, description="Months for trend detection"
    )


class ModelRoutingEntry(BaseModel):
    """Single LLM model routing rule."""

    task: str = Field(..., description="Task name, e.g. 'narrative_generation'")
    model: str = Field(..., description="LiteLLM model identifier")
    max_tokens: int = 2048
    temperature: float = 0.3


class ModelRoutingConfig(BaseModel):
    """Full model routing configuration."""

    routes: list[ModelRoutingEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/thresholds",
    response_model=ThresholdConfig,
    summary="Get current threshold configuration",
)
async def get_thresholds() -> ThresholdConfig:
    """Return the active materiality threshold settings."""
    # TODO: read from shared/config/thresholds.yaml
    return ThresholdConfig()


@router.put(
    "/thresholds",
    response_model=ThresholdConfig,
    summary="Update threshold configuration",
)
async def update_thresholds(body: ThresholdConfig) -> ThresholdConfig:
    """Update materiality thresholds. Triggers engine re-computation flag."""
    # TODO: persist to YAML, notify computation service
    return body


@router.get(
    "/model-routing",
    response_model=ModelRoutingConfig,
    summary="Get LLM model routing config",
)
async def get_model_routing() -> ModelRoutingConfig:
    """Return the current LLM model routing table."""
    # TODO: read from shared/config/model_routing.yaml
    return ModelRoutingConfig(
        routes=[
            ModelRoutingEntry(
                task="narrative_generation",
                model="azure/gpt-4o",
                max_tokens=2048,
                temperature=0.3,
            ),
            ModelRoutingEntry(
                task="intent_classification",
                model="azure/gpt-4o-mini",
                max_tokens=256,
                temperature=0.0,
            ),
        ]
    )
