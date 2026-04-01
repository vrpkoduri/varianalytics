"""Unit tests for config API persistence (YAML read/write).

Tests that GET /config/thresholds reads real values from thresholds.yaml,
PUT /config/thresholds writes to YAML and reads back correctly,
and GET /config/model-routing reads real model routing from YAML.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from services.gateway.api.config import (
    _read_thresholds_yaml,
    _read_model_routing_yaml,
    _write_thresholds_yaml,
    ThresholdConfig,
)

THRESHOLDS_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "config" / "thresholds.yaml"
MODEL_ROUTING_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "config" / "model_routing.yaml"


class TestReadThresholdsYAML:
    """Tests for reading thresholds from the real YAML file."""

    def test_reads_global_abs_threshold(self):
        config = _read_thresholds_yaml(THRESHOLDS_PATH)
        assert config.absolute_amount == 50000

    def test_reads_global_pct_threshold(self):
        config = _read_thresholds_yaml(THRESHOLDS_PATH)
        assert config.percentage == 3.0

    def test_reads_trend_consecutive(self):
        config = _read_thresholds_yaml(THRESHOLDS_PATH)
        assert config.trend_consecutive_months == 3

    def test_missing_file_returns_defaults(self, tmp_path):
        config = _read_thresholds_yaml(tmp_path / "nonexistent.yaml")
        assert config.absolute_amount == 50000  # default


class TestWriteThresholdsYAML:
    """Tests for writing thresholds to YAML and reading back."""

    def test_write_and_readback(self):
        """Write new values to a temp copy, then read them back."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tf:
            temp_path = Path(tf.name)

        try:
            # Copy original to temp
            shutil.copy(THRESHOLDS_PATH, temp_path)

            # Write new values
            new_config = ThresholdConfig(
                absolute_amount=75000,
                percentage=4.5,
                netting_tolerance=2.5,
                trend_consecutive_months=4,
            )
            _write_thresholds_yaml(new_config, temp_path)

            # Read back
            readback = _read_thresholds_yaml(temp_path)
            assert readback.absolute_amount == 75000
            assert readback.percentage == 4.5
            assert readback.trend_consecutive_months == 4
        finally:
            temp_path.unlink(missing_ok=True)

    def test_write_preserves_other_fields(self):
        """Writing thresholds should not destroy other YAML fields (domain overrides, etc.)."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tf:
            temp_path = Path(tf.name)

        try:
            shutil.copy(THRESHOLDS_PATH, temp_path)

            # Write
            _write_thresholds_yaml(ThresholdConfig(absolute_amount=99999), temp_path)

            # Read raw YAML to check other fields preserved
            with open(temp_path) as f:
                data = yaml.safe_load(f)

            assert "domain_overrides" in data, "domain_overrides section should be preserved"
            assert "close_week" in data, "close_week section should be preserved"
            assert "role_overrides" in data, "role_overrides section should be preserved"
        finally:
            temp_path.unlink(missing_ok=True)


class TestReadModelRoutingYAML:
    """Tests for reading model routing from the real YAML file."""

    def test_reads_routes(self):
        config = _read_model_routing_yaml(MODEL_ROUTING_PATH)
        assert len(config.routes) > 0, "Should have at least 1 model route"

    def test_routes_have_model_names(self):
        config = _read_model_routing_yaml(MODEL_ROUTING_PATH)
        for route in config.routes:
            assert route.model, f"Route {route.task} has empty model"
            assert route.task, "Route has empty task name"

    def test_narrative_generation_route_exists(self):
        config = _read_model_routing_yaml(MODEL_ROUTING_PATH)
        tasks = {r.task for r in config.routes}
        assert "narrative_generation" in tasks, f"Missing narrative_generation route. Found: {tasks}"

    def test_missing_file_returns_empty(self, tmp_path):
        config = _read_model_routing_yaml(tmp_path / "nonexistent.yaml")
        assert len(config.routes) == 0
