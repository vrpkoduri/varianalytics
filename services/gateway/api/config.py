"""Configuration endpoints.

Expose and update materiality thresholds and AI Agent model-routing configuration.
Reads from and writes to YAML config files. Changes are validated before persisting.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from shared.auth.middleware import UserContext, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

# Paths to config YAML files
_THRESHOLDS_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "config" / "thresholds.yaml"
_MODEL_ROUTING_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "config" / "model_routing.yaml"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ThresholdConfig(BaseModel):
    """Materiality threshold configuration."""

    absolute_amount: float = Field(50_000, description="Absolute $ threshold")
    percentage: float = Field(3.0, description="Percentage threshold")
    netting_tolerance: float = Field(
        0.10, description="Netting offset tolerance"
    )
    trend_consecutive_months: int = Field(
        3, description="Months for trend detection"
    )


class ModelRoutingEntry(BaseModel):
    """Single AI Agent model routing rule."""

    task: str = Field(..., description="Task name, e.g. 'narrative_generation'")
    model: str = Field(..., description="LiteLLM model identifier")
    max_tokens: int = 2048
    temperature: float = 0.3


class ModelRoutingConfig(BaseModel):
    """Full AI Agent model routing configuration."""

    provider: str = Field("anthropic", description="Active AI provider (anthropic, azure)")
    routes: list[ModelRoutingEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def _read_thresholds_yaml(path: Path = _THRESHOLDS_PATH) -> ThresholdConfig:
    """Read thresholds from YAML file."""
    if not path.exists():
        logger.warning("Thresholds YAML not found at %s, using defaults", path)
        return ThresholdConfig()

    with open(path) as f:
        data = yaml.safe_load(f)

    g = data.get("global", {})
    netting = data.get("netting", {})
    trend = data.get("trend", {})

    return ThresholdConfig(
        absolute_amount=g.get("abs_threshold", 50000),
        percentage=g.get("pct_threshold", 3.0),
        netting_tolerance=netting.get("netting_ratio_threshold", 0.10),
        trend_consecutive_months=trend.get("consecutive_periods", 3),
    )


def _write_thresholds_yaml(config: ThresholdConfig, path: Path = _THRESHOLDS_PATH) -> None:
    """Write thresholds to YAML file, preserving structure."""
    if not path.exists():
        raise FileNotFoundError(f"Thresholds YAML not found at {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Update only the fields we manage via the API
    data["global"]["abs_threshold"] = config.absolute_amount
    data["global"]["pct_threshold"] = config.percentage
    data.setdefault("netting", {})["netting_ratio_threshold"] = config.netting_tolerance
    data.setdefault("trend", {})["consecutive_periods"] = config.trend_consecutive_months

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info("Thresholds YAML updated: abs=%s, pct=%s", config.absolute_amount, config.percentage)


def _read_model_routing_yaml(path: Path = _MODEL_ROUTING_PATH) -> ModelRoutingConfig:
    """Read model routing from YAML file."""
    if not path.exists():
        logger.warning("Model routing YAML not found at %s, using defaults", path)
        return ModelRoutingConfig()

    with open(path) as f:
        data = yaml.safe_load(f)

    provider = data.get("default_provider", "anthropic")
    provider_config = data.get("providers", {}).get(provider, {})

    routes = []
    for task_name, task_config in provider_config.items():
        if isinstance(task_config, dict) and "model" in task_config:
            routes.append(ModelRoutingEntry(
                task=task_name,
                model=task_config["model"],
                max_tokens=task_config.get("max_tokens", 2048),
                temperature=task_config.get("temperature", 0.3),
            ))

    return ModelRoutingConfig(provider=provider, routes=routes)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/thresholds",
    response_model=ThresholdConfig,
    summary="Get current threshold configuration",
)
async def get_thresholds(
    user: UserContext = Depends(get_current_user),
) -> ThresholdConfig:
    """Return the active materiality threshold settings from thresholds.yaml."""
    return _read_thresholds_yaml()


@router.put(
    "/thresholds",
    response_model=ThresholdConfig,
    summary="Update threshold configuration",
)
async def update_thresholds(
    body: ThresholdConfig,
    user: UserContext = Depends(require_admin()),
) -> ThresholdConfig:
    """Update materiality thresholds. Persists to thresholds.yaml."""
    # Validation
    if body.absolute_amount < 0:
        raise HTTPException(status_code=422, detail="absolute_amount must be >= 0")
    if body.percentage < 0:
        raise HTTPException(status_code=422, detail="percentage must be >= 0")
    if body.trend_consecutive_months < 1:
        raise HTTPException(status_code=422, detail="trend_consecutive_months must be >= 1")

    try:
        _write_thresholds_yaml(body)
    except Exception as exc:
        logger.error("Failed to write thresholds YAML: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {exc}")

    return body


@router.get(
    "/model-routing",
    response_model=ModelRoutingConfig,
    summary="Get AI Agent model routing config",
)
async def get_model_routing(
    user: UserContext = Depends(get_current_user),
) -> ModelRoutingConfig:
    """Return the current AI Agent model routing table from model_routing.yaml."""
    return _read_model_routing_yaml()


@router.put(
    "/model-routing",
    response_model=ModelRoutingConfig,
    summary="Update AI Agent model routing config",
)
async def update_model_routing(
    body: ModelRoutingConfig,
    user: UserContext = Depends(require_admin()),
) -> ModelRoutingConfig:
    """Update AI Agent model routing. Persists provider + routes to model_routing.yaml."""
    try:
        _write_model_routing_yaml(body)
    except Exception as exc:
        logger.error("Failed to write model routing YAML: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {exc}")

    return body


def _write_model_routing_yaml(
    config: ModelRoutingConfig, path: Path = _MODEL_ROUTING_PATH
) -> None:
    """Write model routing config to YAML, preserving structure."""
    if not path.exists():
        raise FileNotFoundError(f"Model routing YAML not found at {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Update default provider
    data["default_provider"] = config.provider

    # Update routes for the active provider
    provider_config = data.setdefault("providers", {}).setdefault(config.provider, {})
    for route in config.routes:
        provider_config[route.task] = {
            "model": route.model,
            "max_tokens": route.max_tokens,
            "temperature": route.temperature,
        }

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(
        "Model routing YAML updated: provider=%s, routes=%d",
        config.provider, len(config.routes),
    )
