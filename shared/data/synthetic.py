"""Synthetic data generator — Sprint 0, Deliverable #1.

Generates 36 months of P&L data across 5 ragged-hierarchy dimensions.
Outputs all 15 tables as Parquet and CSV.

Usage:
    generator = SyntheticDataGenerator("docs/synthetic-data-spec.json")
    generator.generate()
    generator.save("data/output")
    issues = generator.validate()
"""

from __future__ import annotations

import json
import logging
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from shared.hierarchy.tree import build_tree_from_dict, flatten_tree, get_leaf_nodes

logger = logging.getLogger(__name__)

# Account ID -> cost profile key mapping
_COST_ACCOUNT_MAP: dict[str, str] = {
    "acct_direct_comp": "direct_comp",
    "acct_subcontractor": "subcontractor",
    "acct_direct_tech": "direct_tech",
    "acct_other_direct": "other_direct",
    "acct_comp_benefits": "comp_benefits",
    "acct_tech_infra": "tech_infra",
    "acct_prof_services": "prof_services",
    "acct_occupancy": "occupancy",
    "acct_travel": "travel",
    "acct_marketing": "marketing",
    "acct_da": "da",
    "acct_insurance": "insurance",
    "acct_training": "training",
    "acct_other_opex": "other_opex",
}

# Revenue account ID -> revenue profile key mapping
_REVENUE_ACCOUNT_MAP: dict[str, str] = {
    "acct_advisory_fees": "advisory_fees",
    "acct_consulting_fees": "consulting_fees",
    "acct_reinsurance_comm": "reinsurance_comm",
    "acct_investment_income": "investment_income",
    "acct_data_analytics_rev": "data_analytics_rev",
    "acct_other_revenue": "other_revenue",
}

# Non-operating accounts with fixed base amounts (in $K)
_NON_OP_BASES: dict[str, float] = {
    "acct_interest_exp": -5000.0,
    "acct_interest_inc": 3000.0,
    "acct_other_nonop": 500.0,
}

# Tax rate for income tax expense
_TAX_RATE = 0.25


class SyntheticDataGenerator:
    """Generates all 15 tables from the synthetic data spec.

    Generation order (dependency-aware):
    1. Dimension tables (no dependencies)
    2. Base fact table (depends on dims)
    3. Computed tables (empty schemas — engine fills)
    4. Workflow/knowledge/audit (empty schemas)
    """

    def __init__(self, spec_path: str, seed: int = 42) -> None:
        """Initialize generator with spec file path.

        Args:
            spec_path: Path to synthetic-data-spec.json
            seed: Random seed for reproducibility
        """
        self.spec_path = Path(spec_path)
        self.seed = seed
        self._spec: dict[str, Any] = {}
        self._tables: dict[str, pd.DataFrame] = {}
        self._rng = np.random.default_rng(seed)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def load_spec(self) -> None:
        """Load and validate the synthetic data spec."""
        with open(self.spec_path) as f:
            self._spec = json.load(f)
        logger.info("Loaded spec from %s", self.spec_path)

    def generate(self) -> dict[str, pd.DataFrame]:
        """Generate all 15 tables. Returns dict of table_name -> DataFrame."""
        if not self._spec:
            self.load_spec()

        logger.info("=== Generating synthetic data (seed=%d) ===", self.seed)

        # Phase A: Dimension tables
        self._tables["dim_hierarchy"] = self._build_dim_hierarchy()
        self._tables["dim_business_unit"] = self._build_dim_business_unit()
        self._tables["dim_account"] = self._build_dim_account()
        self._tables["dim_period"] = self._build_dim_period()
        self._tables["dim_view"] = self._build_dim_view()
        self._tables["dim_comparison_base"] = self._build_dim_comparison_base()
        logger.info("Phase A complete: 6 dimension tables")

        # Phase B: Base fact table
        self._tables["fact_financials"] = self._generate_fact_financials()
        logger.info(
            "Phase B complete: fact_financials (%d rows)",
            len(self._tables["fact_financials"]),
        )

        # Phase C: Empty schema tables (engine fills these)
        self._tables["fact_variance_material"] = self._empty_fact_variance_material()
        self._tables["fact_decomposition"] = self._empty_fact_decomposition()
        self._tables["fact_netting_flags"] = self._empty_fact_netting_flags()
        self._tables["fact_trend_flags"] = self._empty_fact_trend_flags()
        self._tables["fact_correlations"] = self._empty_fact_correlations()
        self._tables["fact_review_status"] = self._empty_fact_review_status()
        self._tables["knowledge_commentary_history"] = self._empty_knowledge_commentary()
        self._tables["audit_log"] = self._empty_audit_log()
        logger.info("Phase C complete: 8 empty schema tables")

        logger.info("=== All 15 tables generated ===")
        return self._tables

    def save(self, output_dir: str, formats: list[str] | None = None) -> None:
        """Save all tables to disk as Parquet and CSV.

        Args:
            output_dir: Target directory.
            formats: List of formats ('parquet', 'csv'). Default: both.
        """
        if not self._tables:
            raise RuntimeError("No tables generated. Call generate() first.")

        formats = formats or ["parquet", "csv"]
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        for table_name, df in self._tables.items():
            for fmt in formats:
                file_path = out_path / f"{table_name}.{fmt}"
                if fmt == "parquet":
                    df.to_parquet(file_path, index=False)
                elif fmt == "csv":
                    df.to_csv(file_path, index=False)
                logger.info("Saved %s (%d rows) -> %s", table_name, len(df), file_path)

    def validate(self) -> list[str]:
        """Post-generation validation. Returns list of issues (empty = valid)."""
        issues: list[str] = []

        if not self._tables:
            return ["No tables generated"]

        # Check all 15 tables exist
        expected_tables = {
            "dim_hierarchy", "dim_business_unit", "dim_account", "dim_period",
            "dim_view", "dim_comparison_base", "fact_financials",
            "fact_variance_material", "fact_decomposition", "fact_netting_flags",
            "fact_trend_flags", "fact_correlations", "fact_review_status",
            "knowledge_commentary_history", "audit_log",
        }
        missing = expected_tables - set(self._tables.keys())
        if missing:
            issues.append(f"Missing tables: {missing}")

        # Validate dimension tables are non-empty
        for dim_name in ["dim_hierarchy", "dim_business_unit", "dim_account", "dim_period"]:
            if dim_name in self._tables and len(self._tables[dim_name]) == 0:
                issues.append(f"{dim_name} is empty")

        # Validate fact_financials
        ff = self._tables.get("fact_financials")
        if ff is not None and len(ff) > 0:
            # No nulls in required columns
            required_cols = [
                "period_id", "bu_id", "account_id", "geo_node_id",
                "fiscal_year", "actual_amount", "budget_amount",
            ]
            for col in required_cols:
                if col in ff.columns and ff[col].isna().any():
                    issues.append(f"fact_financials has nulls in required column: {col}")

            # Check period range
            periods = ff["period_id"].unique()
            if "2024-01" not in periods:
                issues.append("fact_financials missing start period 2024-01")
            if "2026-12" not in periods:
                issues.append("fact_financials missing end period 2026-12")

            # Check all 5 BUs present
            bus = set(ff["bu_id"].unique())
            expected_bus = {"marsh", "mercer", "guy_carpenter", "oliver_wyman", "mmc_corporate"}
            if bus != expected_bus:
                issues.append(f"BU mismatch: got {bus}, expected {expected_bus}")

            # Check actual amounts are positive for revenue, non-zero spread
            rev_rows = ff[ff["account_id"].isin(_REVENUE_ACCOUNT_MAP.keys())]
            if len(rev_rows) > 0 and (rev_rows["actual_amount"] < 0).any():
                issues.append("Revenue accounts have negative actual amounts")

            # Check budget != actual (i.e., there IS variance)
            if len(ff) > 0:
                exact_match_pct = (ff["actual_amount"] == ff["budget_amount"]).mean()
                if exact_match_pct > 0.5:
                    issues.append(
                        f"Too many exact actual=budget matches ({exact_match_pct:.1%}), "
                        "check volatility"
                    )

        # Validate dim_hierarchy node counts
        dh = self._tables.get("dim_hierarchy")
        if dh is not None:
            for dim_name in ["Geography", "Segment", "LOB", "CostCenter"]:
                dim_rows = dh[dh["dimension_name"] == dim_name]
                if len(dim_rows) == 0:
                    issues.append(f"dim_hierarchy missing dimension: {dim_name}")

        # Validate dim_account has calculated rows
        da = self._tables.get("dim_account")
        if da is not None:
            calc_rows = da[da["is_calculated"] == True]  # noqa: E712
            if len(calc_rows) == 0:
                issues.append("dim_account has no calculated rows")

        return issues

    # -------------------------------------------------------------------------
    # Phase A: Dimension Tables
    # -------------------------------------------------------------------------

    def _build_dim_hierarchy(self) -> pd.DataFrame:
        """Build dim_hierarchy from all 4 hierarchy trees in the spec.

        Flattens Geo (26 nodes), Segment (13), LOB (13), CostCenter (20)
        into a single parent-child table with materialized rollup paths.
        """
        rows: list[dict[str, Any]] = []
        dimension_keys = [
            ("geography_hierarchy", "Geography"),
            ("segment_hierarchy", "Segment"),
            ("lob_hierarchy", "LOB"),
            ("costcenter_hierarchy", "CostCenter"),
        ]

        for spec_key, dim_name in dimension_keys:
            tree_data = self._spec[spec_key]["tree"]
            root = build_tree_from_dict(tree_data)
            flat_nodes = flatten_tree(root)

            for i, node in enumerate(flat_nodes):
                rows.append({
                    "node_id": node.node_id,
                    "node_name": node.node_name,
                    "dimension_name": dim_name,
                    "parent_id": node.parent_id,
                    "depth": node.depth,
                    "is_leaf": node.is_leaf,
                    "rollup_path": node.rollup_path,
                    "sort_order": i,
                })

        df = pd.DataFrame(rows)
        logger.info("dim_hierarchy: %d nodes across 4 dimensions", len(df))
        return df

    def _build_dim_business_unit(self) -> pd.DataFrame:
        """Build dim_business_unit — 5 BUs from spec."""
        return pd.DataFrame(self._spec["business_units"])

    def _build_dim_account(self) -> pd.DataFrame:
        """Build dim_account — 36 account nodes with calculated row metadata.

        Includes calc_formula, calc_dependencies, variance_sign, pl_category.
        """
        tree_data = self._spec["account_hierarchy"]["tree"]
        root = build_tree_from_dict(tree_data)
        flat_nodes = flatten_tree(root)

        rows: list[dict[str, Any]] = []
        for i, node in enumerate(flat_nodes):
            meta = node.metadata
            # Determine calc_dependencies from formula
            calc_deps = None
            formula = meta.get("calc_formula")
            if formula:
                calc_deps = self._parse_calc_dependencies(formula)

            rows.append({
                "account_id": node.node_id,
                "account_name": node.node_name,
                "parent_id": node.parent_id,
                "depth": node.depth,
                "is_leaf": node.is_leaf,
                "is_calculated": meta.get("is_calculated", False),
                "calc_formula": formula,
                "calc_dependencies": json.dumps(calc_deps) if calc_deps else None,
                "pl_category": meta.get("pl_category"),
                "variance_sign": meta.get("variance_sign"),
                "rollup_path": node.rollup_path,
                "sort_order": i,
            })

        df = pd.DataFrame(rows)
        logger.info("dim_account: %d nodes (%d calculated)", len(df), df["is_calculated"].sum())
        return df

    def _build_dim_period(self) -> pd.DataFrame:
        """Build dim_period — 36 months from 2024-01 to 2026-12."""
        period_range = self._spec["metadata"]["period_range"]
        current_period = period_range["current_period"]  # "2026-06"
        rows: list[dict[str, Any]] = []

        for year in range(2024, 2027):
            for month in range(1, 13):
                period_id = f"{year}-{month:02d}"
                _, last_day = monthrange(year, month)
                quarter = (month - 1) // 3 + 1
                # Periods before current are closed
                is_current = period_id == current_period
                is_closed = period_id < current_period

                rows.append({
                    "period_id": period_id,
                    "fiscal_year": year,
                    "fiscal_quarter": quarter,
                    "fiscal_month": month,
                    "period_start": date(year, month, 1).isoformat(),
                    "period_end": date(year, month, last_day).isoformat(),
                    "is_closed": is_closed,
                    "is_current": is_current,
                })

        return pd.DataFrame(rows)

    def _build_dim_view(self) -> pd.DataFrame:
        """Build dim_view — 3 rows: MTD, QTD, YTD."""
        return pd.DataFrame([
            {"view_id": "MTD", "view_name": "Month-to-Date", "view_type": "MTD"},
            {"view_id": "QTD", "view_name": "Quarter-to-Date", "view_type": "QTD"},
            {"view_id": "YTD", "view_name": "Year-to-Date", "view_type": "YTD"},
        ])

    def _build_dim_comparison_base(self) -> pd.DataFrame:
        """Build dim_comparison_base — 3 rows: Budget, Forecast, Prior Year."""
        return pd.DataFrame([
            {"base_id": "BUDGET", "base_name": "Budget", "base_type": "BUDGET"},
            {"base_id": "FORECAST", "base_name": "Forecast", "base_type": "FORECAST"},
            {"base_id": "PRIOR_YEAR", "base_name": "Prior Year", "base_type": "PRIOR_YEAR"},
        ])

    # -------------------------------------------------------------------------
    # Phase B: fact_financials
    # -------------------------------------------------------------------------

    def _generate_fact_financials(self) -> pd.DataFrame:
        """Generate fact_financials — MTD atomic grain.

        Grain: Period × BU × CostCenter × Account
        Each (BU, CostCenter) maps to exactly one (Geo, Segment, LOB) via org_mapping.

        For each org unit per period:
        - Revenue: BU profile × geo weight × CC share × seasonality × growth × noise
        - Costs: Revenue-proportional × cost ratio × noise
        - Non-Op: Fixed base × CC share × noise
        - Tax: Effective rate × pre-tax income
        """
        from shared.data.org_mapping import get_org_units, get_org_units_for_bu

        rules = self._spec["data_generation_rules"]
        periods = self._get_period_list()
        org_units = get_org_units()

        # Pre-compute CC count per BU for revenue share
        bu_cc_counts: dict[str, int] = {}
        for unit in org_units:
            bu_cc_counts[unit.bu_id] = bu_cc_counts.get(unit.bu_id, 0) + 1

        # Revenue and cost account IDs
        revenue_accounts = list(_REVENUE_ACCOUNT_MAP.keys())
        cost_accounts = list(_COST_ACCOUNT_MAP.keys())
        nonop_accounts = list(_NON_OP_BASES.keys())
        tax_account = "acct_tax"

        all_rows: list[dict[str, Any]] = []

        for period_id in periods:
            year = int(period_id[:4])
            month = int(period_id[5:7])
            growth = rules["growth_rates"][str(year)]
            rev_season = rules["seasonality"]["revenue"][month - 1]
            cost_season = rules["seasonality"]["costs"][month - 1]

            for unit in org_units:
                bu_id = unit.bu_id
                cc_id = unit.costcenter_id
                geo_id = unit.geo_node_id
                seg_id = unit.segment_node_id
                lob_id = unit.lob_node_id

                rev_profile = rules["revenue_profiles"][bu_id]
                geo_dist = rules["geographic_distribution"][bu_id]

                # Geo weight for this org unit's geography
                geo_weight = self._get_geo_weight(geo_id, geo_dist)
                if geo_weight == 0:
                    geo_weight = 0.01  # Minimum weight for mapped org units

                # CC share: distribute geo's revenue across CCs in same BU+geo
                # Count how many CCs in this BU share the same geo
                same_geo_ccs = sum(
                    1 for u in org_units
                    if u.bu_id == bu_id and u.geo_node_id == geo_id
                )
                cc_share = 1.0 / same_geo_ccs if same_geo_ccs > 0 else 1.0

                # FX rate info
                currency, budget_fx, actual_fx = self._get_fx_rates(
                    geo_id, period_id, rules
                )

                # --- Revenue accounts ---
                total_revenue = 0.0
                for acct_id in revenue_accounts:
                    profile_key = _REVENUE_ACCOUNT_MAP[acct_id]
                    base = rev_profile[profile_key]
                    if base == 0:
                        continue

                    actual = self._compute_actual(
                        base, geo_weight * cc_share, rev_season, growth,
                        rules["volatility_params"]["revenue_volatility"],
                    )
                    budget = self._compute_budget(
                        base, geo_weight * cc_share, rev_season, growth,
                        rules["volatility_params"]["budget_accuracy"],
                    )

                    # Apply scenario injections
                    actual = self._apply_scenarios(
                        actual, bu_id, geo_id, acct_id, period_id
                    )

                    forecast = self._compute_forecast(
                        actual, period_id,
                        rules["volatility_params"]["forecast_accuracy"],
                    )
                    prior_year = self._compute_prior_year(
                        base, geo_weight * cc_share, rev_season, growth, year
                    )

                    local_actual = actual / actual_fx if actual_fx else None

                    total_revenue += actual
                    all_rows.append(self._make_row(
                        period_id, bu_id, acct_id, geo_id, seg_id, lob_id, cc_id,
                        year, actual, budget, forecast, prior_year,
                        local_actual, currency, budget_fx, actual_fx,
                    ))

                # --- Cost accounts (proportional to this CC's revenue) ---
                for acct_id in cost_accounts:
                    profile_key = _COST_ACCOUNT_MAP[acct_id]
                    cost_ratio = rules["cost_profiles"][profile_key]
                    base_cost = total_revenue * cost_ratio

                    volatility = (
                        rules["volatility_params"]["cogs_volatility"]
                        if acct_id.startswith("acct_direct") or acct_id == "acct_subcontractor"
                        else rules["volatility_params"]["opex_volatility"]
                    )
                    actual = base_cost * (1 + self._rng.normal(0, volatility))
                    actual = self._apply_scenarios(actual, bu_id, geo_id, acct_id, period_id)

                    budget = base_cost * (
                        1 + self._rng.normal(0, 1 - rules["volatility_params"]["budget_accuracy"])
                    )
                    forecast = self._compute_forecast(
                        actual, period_id,
                        rules["volatility_params"]["forecast_accuracy"],
                    )

                    # Costs stored as positive (sign convention at variance calc)
                    actual = abs(actual) * cost_season / rev_season
                    budget = abs(budget) * cost_season / rev_season

                    prior_year_cost = abs(base_cost) / growth
                    local_actual = actual / actual_fx if actual_fx else None

                    all_rows.append(self._make_row(
                        period_id, bu_id, acct_id, geo_id, seg_id, lob_id, cc_id,
                        year, actual, budget, forecast, prior_year_cost,
                        local_actual, currency, budget_fx, actual_fx,
                    ))

                # --- Non-operating accounts ---
                for acct_id in nonop_accounts:
                    base = _NON_OP_BASES[acct_id] * geo_weight * cc_share
                    actual = base * growth * (1 + self._rng.normal(0, 0.05))
                    budget = base * growth * (1 + self._rng.normal(0, 0.02))
                    forecast = self._compute_forecast(actual, period_id, 0.98)
                    prior_year = base * rules["growth_rates"].get(str(year - 1), 1.0)

                    if acct_id == "acct_interest_exp":
                        actual = abs(actual)
                        budget = abs(budget)
                        prior_year = abs(prior_year) if prior_year else None

                    all_rows.append(self._make_row(
                        period_id, bu_id, acct_id, geo_id, seg_id, lob_id, cc_id,
                        year, actual, budget, forecast, prior_year,
                        None, currency, budget_fx, actual_fx,
                    ))

                # --- Tax account ---
                estimated_pti = total_revenue * 0.15
                tax_actual = abs(estimated_pti * _TAX_RATE * (1 + self._rng.normal(0, 0.03)))
                tax_budget = abs(estimated_pti * _TAX_RATE * (1 + self._rng.normal(0, 0.01)))

                all_rows.append(self._make_row(
                    period_id, bu_id, tax_account, geo_id, seg_id, lob_id, cc_id,
                    year, tax_actual, tax_budget, None, None,
                    None, currency, budget_fx, actual_fx,
                ))

        df = pd.DataFrame(all_rows)
        logger.info("fact_financials: %d rows generated", len(df))
        return df

    # -------------------------------------------------------------------------
    # Phase C: Empty Schema Tables
    # -------------------------------------------------------------------------

    def _empty_fact_variance_material(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "variance_id", "period_id", "bu_id", "account_id", "geo_node_id",
            "segment_node_id", "lob_node_id", "costcenter_node_id",
            "view_id", "base_id", "actual_amount", "comparator_amount",
            "variance_amount", "variance_pct", "is_material", "is_netted",
            "is_trending", "narrative_detail", "narrative_midlevel",
            "narrative_summary", "narrative_oneliner", "narrative_board",
            "narrative_source", "synthesis_child_ids", "engine_run_id", "created_at",
        ])

    def _empty_fact_decomposition(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "variance_id", "method", "components", "total_explained",
            "residual", "created_at",
        ])

    def _empty_fact_netting_flags(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "netting_id", "parent_node_id", "parent_dimension", "check_type",
            "net_variance", "gross_variance", "netting_ratio", "child_details",
            "period_id", "created_at",
        ])

    def _empty_fact_trend_flags(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "trend_id", "account_id", "dimension_key", "rule_type",
            "consecutive_periods", "cumulative_amount", "direction",
            "period_details", "created_at",
        ])

    def _empty_fact_correlations(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "correlation_id", "variance_id_a", "variance_id_b",
            "correlation_score", "dimension_overlap", "directional_match",
            "hypothesis", "confidence", "created_at",
        ])

    def _empty_fact_review_status(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "review_id", "variance_id", "status", "assigned_analyst",
            "reviewer", "approver", "original_narrative", "edited_narrative",
            "edit_diff", "hypothesis_feedback", "review_notes",
            "created_at", "reviewed_at", "approved_at",
        ])

    def _empty_knowledge_commentary(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "commentary_id", "variance_id", "account_id", "period_id", "bu_id",
            "narrative_text", "narrative_level", "embedding_vector",
            "variance_amount", "variance_pct", "context_metadata",
            "created_at", "approved_by",
        ])

    def _empty_audit_log(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "audit_id", "event_type", "user_id", "service", "action",
            "details", "ip_address", "timestamp",
        ])

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_period_list(self) -> list[str]:
        """Get list of all 36 period IDs."""
        periods = []
        for year in range(2024, 2027):
            for month in range(1, 13):
                periods.append(f"{year}-{month:02d}")
        return periods

    def _get_leaf_ids(self, hierarchy_key: str) -> list[str]:
        """Get leaf node IDs from a hierarchy spec key."""
        tree_data = self._spec[hierarchy_key]["tree"]
        root = build_tree_from_dict(tree_data)
        return [n.node_id for n in get_leaf_nodes(root)]

    def _get_geo_weight(self, geo_id: str, geo_dist: dict[str, float]) -> float:
        """Get geographic distribution weight for a leaf geo node.

        Sub-regions (e.g., geo_us_ne) inherit from parent (geo_us) split evenly.
        """
        # Direct match
        if geo_id in geo_dist:
            return geo_dist[geo_id]

        # US sub-regions: split geo_us weight across 4 regions
        us_regions = {"geo_us_ne", "geo_us_se", "geo_us_mw", "geo_us_w"}
        if geo_id in us_regions and "geo_us" in geo_dist:
            return geo_dist["geo_us"] / len(us_regions)

        # LATAM sub-regions
        latam_regions = {"geo_brazil", "geo_mexico", "geo_colombia"}
        if geo_id in latam_regions and "geo_latam" in geo_dist:
            return geo_dist["geo_latam"] / len(latam_regions)

        # Continental Europe sub-regions
        europe_regions = {"geo_germany", "geo_france", "geo_netherlands", "geo_spain"}
        if geo_id in europe_regions and "geo_cont_europe" in geo_dist:
            return geo_dist["geo_cont_europe"] / len(europe_regions)

        # Middle East & Africa sub-regions
        mea_regions = {"geo_uae", "geo_south_africa"}
        if geo_id in mea_regions and "geo_mea" in geo_dist:
            return geo_dist["geo_mea"] / len(mea_regions)

        # APAC sub-regions
        apac_map = {
            "geo_anz": 0.30, "geo_japan": 0.25, "geo_india": 0.20,
            "geo_singapore": 0.125, "geo_hong_kong": 0.125,
        }
        if geo_id in apac_map and "geo_apac" in geo_dist:
            return geo_dist["geo_apac"] * apac_map[geo_id]

        return 0.0

    def _get_fx_rates(
        self, geo_id: str, period_id: str, rules: dict
    ) -> tuple[str | None, float | None, float | None]:
        """Get currency code and FX rates for a geography.

        Returns (currency_code, budget_rate, actual_rate).
        USD geos return (USD, 1.0, 1.0).
        """
        geo_currency_map = rules["fx_rates"]["geo_currency_map"]
        currencies = rules["fx_rates"]["currencies"]

        currency = geo_currency_map.get(geo_id, "USD")
        if currency == "USD":
            return "USD", 1.0, 1.0

        if currency not in currencies:
            return currency, 1.0, 1.0

        fx_info = currencies[currency]
        budget_rate = fx_info["budget_rate"]
        # Actual rate varies from budget based on volatility
        actual_rate = budget_rate * (1 + self._rng.normal(0, fx_info["volatility"]))

        return currency, budget_rate, actual_rate

    def _compute_actual(
        self, base: float, geo_weight: float, seasonality: float,
        growth: float, volatility: float
    ) -> float:
        """Compute actual amount with noise."""
        noise = 1 + self._rng.normal(0, volatility)
        return base * geo_weight * seasonality * growth * noise

    def _compute_budget(
        self, base: float, geo_weight: float, seasonality: float,
        growth: float, accuracy: float
    ) -> float:
        """Compute budget amount (tighter noise than actual)."""
        noise = 1 + self._rng.normal(0, 1 - accuracy)
        return base * geo_weight * seasonality * growth * noise

    def _compute_forecast(
        self, actual: float, period_id: str, accuracy: float
    ) -> float | None:
        """Compute forecast. Only available for closed periods before current."""
        current = self._spec["metadata"]["period_range"]["current_period"]
        if period_id >= current:
            return None  # No forecast for future/current periods
        noise = 1 + self._rng.normal(0, 1 - accuracy)
        return actual * noise

    def _compute_prior_year(
        self, base: float, geo_weight: float, seasonality: float,
        current_growth: float, current_year: int
    ) -> float | None:
        """Compute prior year amount. None if year < 2025 (no 2023 data)."""
        if current_year <= 2024:
            return None
        prior_growth = self._spec["data_generation_rules"]["growth_rates"].get(
            str(current_year - 1), 1.0
        )
        noise = 1 + self._rng.normal(0, 0.02)
        return base * geo_weight * seasonality * prior_growth * noise

    def _apply_scenarios(
        self, amount: float, bu_id: str, geo_id: str, acct_id: str, period_id: str
    ) -> float:
        """Apply scenario injections from spec."""
        scenarios = self._spec["data_generation_rules"]["scenario_injections"]["scenarios"]

        for scenario in scenarios:
            adjustments = scenario.get("adjustments", [])
            for adj in adjustments:
                # Check period match
                adj_period = adj.get("period", scenario.get("period"))
                if adj_period and adj_period != period_id:
                    continue

                # Check BU match (if specified)
                if "bu" in adj and adj["bu"] != bu_id:
                    continue

                # Check geo match (if specified)
                if "geo" in adj and adj["geo"] != geo_id:
                    continue

                # Check account match
                if "account" in adj and adj["account"] != acct_id:
                    continue

                # Apply multiplier
                amount *= adj.get("multiplier", 1.0)

            # Handle tech trend scenario (cumulative multipliers)
            if "cumulative_multipliers" in scenario:
                if scenario.get("account") == acct_id:
                    periods = scenario.get("periods", [])
                    multipliers = scenario["cumulative_multipliers"]
                    if period_id in periods:
                        idx = periods.index(period_id)
                        amount *= multipliers[idx]

        return amount

    def _make_row(
        self,
        period_id: str, bu_id: str, account_id: str,
        geo_id: str, seg_id: str, lob_id: str, cc_id: str,
        fiscal_year: int,
        actual: float, budget: float,
        forecast: float | None, prior_year: float | None,
        local_amount: float | None, currency: str | None,
        budget_fx: float | None, actual_fx: float | None,
    ) -> dict[str, Any]:
        """Create a single fact_financials row dict."""
        return {
            "period_id": period_id,
            "bu_id": bu_id,
            "account_id": account_id,
            "geo_node_id": geo_id,
            "segment_node_id": seg_id,
            "lob_node_id": lob_id,
            "costcenter_node_id": cc_id,
            "fiscal_year": fiscal_year,
            "actual_amount": round(actual, 2),
            "budget_amount": round(budget, 2),
            "forecast_amount": round(forecast, 2) if forecast is not None else None,
            "prior_year_amount": round(prior_year, 2) if prior_year is not None else None,
            "actual_local_amount": round(local_amount, 2) if local_amount is not None else None,
            "local_currency": currency,
            "budget_fx_rate": budget_fx,
            "actual_fx_rate": actual_fx,
        }

    @staticmethod
    def _parse_calc_dependencies(formula: str) -> list[str]:
        """Extract account IDs referenced in a calc formula.

        Handles formulas like 'acct_gross_revenue - acct_total_cor' and
        'SUM(acct_revenue.children)'.
        """
        import re
        return re.findall(r"acct_\w+", formula)
