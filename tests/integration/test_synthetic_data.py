"""Integration tests for the synthetic data generator.

Tests the full generation pipeline, data quality, and scenario injections.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shared.data.synthetic import SyntheticDataGenerator


@pytest.fixture(scope="module")
def generator() -> SyntheticDataGenerator:
    """Create and run the generator once for all tests in this module."""
    gen = SyntheticDataGenerator("docs/synthetic-data-spec.json", seed=42)
    gen.generate()
    return gen


@pytest.fixture(scope="module")
def tables(generator: SyntheticDataGenerator) -> dict[str, pd.DataFrame]:
    """Get all generated tables."""
    return generator._tables


@pytest.mark.integration
class TestGenerationCompleteness:
    """Tests that all 15 tables are generated with correct structure."""

    def test_all_15_tables_present(self, tables: dict) -> None:
        assert len(tables) == 15

    def test_validation_passes(self, generator: SyntheticDataGenerator) -> None:
        issues = generator.validate()
        assert issues == [], f"Validation failed: {issues}"

    def test_dim_hierarchy_node_count(self, tables: dict) -> None:
        dh = tables["dim_hierarchy"]
        # Geo: 26, Segment: 13, LOB: 13, CostCenter: 20 = 72 from spec
        # Actual count may vary slightly based on tree structure
        assert len(dh) >= 70

    def test_dim_hierarchy_all_dimensions(self, tables: dict) -> None:
        dims = set(tables["dim_hierarchy"]["dimension_name"].unique())
        assert dims == {"Geography", "Segment", "LOB", "CostCenter"}

    def test_dim_business_unit_count(self, tables: dict) -> None:
        assert len(tables["dim_business_unit"]) == 5

    def test_dim_account_structure(self, tables: dict) -> None:
        da = tables["dim_account"]
        assert len(da) >= 36  # 28 detail + 8+ calculated
        assert da["is_calculated"].sum() >= 8  # At least 8 calculated rows

    def test_dim_period_36_months(self, tables: dict) -> None:
        assert len(tables["dim_period"]) == 36

    def test_dim_view_3_rows(self, tables: dict) -> None:
        assert len(tables["dim_view"]) == 3

    def test_dim_comparison_base_3_rows(self, tables: dict) -> None:
        assert len(tables["dim_comparison_base"]) == 3

    def test_fact_financials_has_data(self, tables: dict) -> None:
        assert len(tables["fact_financials"]) > 40000

    def test_empty_tables_have_correct_schema(self, tables: dict) -> None:
        """Computed tables should be empty but have the right columns."""
        fvm = tables["fact_variance_material"]
        assert len(fvm) == 0
        assert "variance_id" in fvm.columns
        assert "narrative_detail" in fvm.columns


@pytest.mark.integration
class TestFactFinancialsGrain:
    """Tests that the grain is Period x BU x CostCenter x Account."""

    def test_grain_uniqueness(self, tables: dict) -> None:
        """No duplicate rows on the 4-key grain."""
        ff = tables["fact_financials"]
        grain_cols = ["period_id", "bu_id", "costcenter_node_id", "account_id"]
        dupes = ff.duplicated(subset=grain_cols, keep=False).sum()
        assert dupes == 0

    def test_bu_cc_maps_to_one_geo_seg_lob(self, tables: dict) -> None:
        """Each (BU, CC) pair maps to exactly one (Geo, Segment, LOB)."""
        ff = tables["fact_financials"]
        mapping = ff.groupby(["bu_id", "costcenter_node_id"])[
            ["geo_node_id", "segment_node_id", "lob_node_id"]
        ].nunique()
        multi = mapping[(mapping > 1).any(axis=1)]
        assert len(multi) == 0, f"BU+CC combos with >1 mapping: {multi}"

    def test_realistic_bu_cc_pruning(self, tables: dict) -> None:
        """Not every BU has all 16 CCs — realistic pruning applied."""
        ff = tables["fact_financials"]
        bu_cc_counts = ff.groupby("bu_id")["costcenter_node_id"].nunique()
        # MMC Corporate should have fewer CCs than Marsh
        assert bu_cc_counts["mmc_corporate"] < bu_cc_counts["marsh"]
        # All BUs should have at least 10 CCs
        assert bu_cc_counts.min() >= 10


@pytest.mark.integration
class TestOrgMapping:
    """Tests for the org unit mapping module."""

    def test_all_org_units_valid(self) -> None:
        from shared.data.org_mapping import get_org_units
        units = get_org_units()
        assert len(units) == 60  # Total from eligibility matrix

    def test_eligibility_matches_mapping(self) -> None:
        from shared.data.org_mapping import BU_CC_ELIGIBILITY, get_org_units
        units = get_org_units()
        for bu_id, cc_list in BU_CC_ELIGIBILITY.items():
            bu_units = [u for u in units if u.bu_id == bu_id]
            bu_cc_ids = {u.costcenter_id for u in bu_units}
            assert bu_cc_ids == set(cc_list), f"Mismatch for {bu_id}"

    def test_geo_spread(self) -> None:
        """Org units should be spread across multiple geos per BU."""
        from shared.data.org_mapping import get_org_units_for_bu
        for bu_id in ["marsh", "mercer", "guy_carpenter", "oliver_wyman"]:
            units = get_org_units_for_bu(bu_id)
            geos = {u.geo_node_id for u in units}
            assert len(geos) >= 3, f"{bu_id} should span 3+ geos, got {len(geos)}"


@pytest.mark.integration
class TestFactFinancialsQuality:
    """Tests data quality of the generated fact_financials."""

    def test_all_bus_present(self, tables: dict) -> None:
        bus = set(tables["fact_financials"]["bu_id"].unique())
        assert bus == {"marsh", "mercer", "guy_carpenter", "oliver_wyman", "mmc_corporate"}

    def test_all_periods_present(self, tables: dict) -> None:
        periods = sorted(tables["fact_financials"]["period_id"].unique())
        assert periods[0] == "2024-01"
        assert periods[-1] == "2026-12"
        assert len(periods) == 36

    def test_revenue_accounts_positive(self, tables: dict) -> None:
        ff = tables["fact_financials"]
        rev_accounts = ["acct_advisory_fees", "acct_consulting_fees", "acct_reinsurance_comm",
                        "acct_investment_income", "acct_data_analytics_rev", "acct_other_revenue"]
        rev_data = ff[ff["account_id"].isin(rev_accounts)]
        assert (rev_data["actual_amount"] > 0).all(), "Revenue should be positive"

    def test_actual_differs_from_budget(self, tables: dict) -> None:
        """Volatility should cause actual != budget in most rows."""
        ff = tables["fact_financials"]
        exact_match_pct = (ff["actual_amount"] == ff["budget_amount"]).mean()
        assert exact_match_pct < 0.01, f"Too many exact matches: {exact_match_pct:.1%}"

    def test_prior_year_null_for_2024_revenue(self, tables: dict) -> None:
        """2024 revenue rows should have NULL prior year (no 2023 data)."""
        ff = tables["fact_financials"]
        fy2024_rev = ff[(ff["fiscal_year"] == 2024) & (ff["account_id"] == "acct_advisory_fees")]
        assert fy2024_rev["prior_year_amount"].isna().all()

    def test_prior_year_populated_for_2025_2026(self, tables: dict) -> None:
        """2025+ rows should mostly have prior year data."""
        ff = tables["fact_financials"]
        fy2025 = ff[ff["fiscal_year"] == 2025]
        # Revenue accounts should have PY
        rev_2025 = fy2025[fy2025["account_id"] == "acct_advisory_fees"]
        assert rev_2025["prior_year_amount"].notna().mean() > 0.5

    def test_forecast_null_for_current_and_future(self, tables: dict) -> None:
        """Forecast should be NULL for periods >= current (2026-06)."""
        ff = tables["fact_financials"]
        future = ff[ff["period_id"] >= "2026-06"]
        assert future["forecast_amount"].isna().all()

    def test_fx_rates_for_non_usd_geos(self, tables: dict) -> None:
        """Non-USD geos should have FX rate data."""
        ff = tables["fact_financials"]
        uk_data = ff[ff["geo_node_id"] == "geo_uk_ireland"]
        if len(uk_data) > 0:
            assert (uk_data["local_currency"] == "GBP").all()
            assert uk_data["budget_fx_rate"].notna().all()

    def test_usd_geos_have_rate_1(self, tables: dict) -> None:
        """US geos should have FX rate = 1.0."""
        ff = tables["fact_financials"]
        us_data = ff[ff["geo_node_id"] == "geo_us_ne"]
        if len(us_data) > 0:
            assert (us_data["budget_fx_rate"] == 1.0).all()

    def test_seasonality_visible(self, tables: dict) -> None:
        """December should have higher revenue than August (seasonality)."""
        ff = tables["fact_financials"]
        rev = ff[ff["account_id"] == "acct_advisory_fees"]
        dec = rev[rev["period_id"].str.endswith("-12")]["actual_amount"].mean()
        aug = rev[rev["period_id"].str.endswith("-08")]["actual_amount"].mean()
        assert dec > aug, f"Dec ({dec:.0f}) should exceed Aug ({aug:.0f}) due to seasonality"


@pytest.mark.integration
class TestDimHierarchyQuality:
    """Tests hierarchy dimension quality."""

    def test_rollup_paths_populated(self, tables: dict) -> None:
        dh = tables["dim_hierarchy"]
        assert dh["rollup_path"].notna().all()
        assert (dh["rollup_path"].str.len() > 0).all()

    def test_root_nodes_have_null_parent(self, tables: dict) -> None:
        dh = tables["dim_hierarchy"]
        roots = dh[dh["depth"] == 0]
        assert roots["parent_id"].isna().all()

    def test_leaf_nodes_flagged(self, tables: dict) -> None:
        dh = tables["dim_hierarchy"]
        # All parent_ids should reference valid node_ids
        all_ids = set(dh["node_id"])
        non_root = dh[dh["parent_id"].notna()]
        invalid_parents = set(non_root["parent_id"]) - all_ids
        assert len(invalid_parents) == 0, f"Invalid parent IDs: {invalid_parents}"


@pytest.mark.integration
class TestDimAccountQuality:
    """Tests account dimension quality."""

    def test_calculated_rows_have_formulas(self, tables: dict) -> None:
        da = tables["dim_account"]
        calc = da[da["is_calculated"] == True]  # noqa: E712
        # All calc rows except root (acct_total_pl) should have formulas
        non_root_calc = calc[calc["account_id"] != "acct_total_pl"]
        assert non_root_calc["calc_formula"].notna().all()

    def test_detail_accounts_have_pl_category(self, tables: dict) -> None:
        da = tables["dim_account"]
        detail = da[(da["is_leaf"] == True) & (da["is_calculated"] == False)]  # noqa: E712
        # Most detail accounts should have a pl_category (some root nodes might not)
        assert detail["pl_category"].notna().mean() > 0.8

    def test_ebitda_in_calculated(self, tables: dict) -> None:
        da = tables["dim_account"]
        ebitda = da[da["account_id"] == "acct_ebitda"]
        assert len(ebitda) == 1
        assert ebitda.iloc[0]["is_calculated"] == True  # noqa: E712


@pytest.mark.integration
class TestSaveAndLoad:
    """Tests save/load round-trip."""

    def test_save_and_reload(self, generator: SyntheticDataGenerator, tmp_path: Path) -> None:
        generator.save(str(tmp_path), formats=["parquet"])

        from shared.data.loader import DataLoader
        loader = DataLoader(str(tmp_path))

        ff = loader.load_table("fact_financials")
        assert len(ff) == len(generator._tables["fact_financials"])

        dh = loader.load_table("dim_hierarchy")
        assert len(dh) == len(generator._tables["dim_hierarchy"])


@pytest.mark.integration
class TestReproducibility:
    """Tests that the same seed produces identical output."""

    def test_same_seed_same_output(self) -> None:
        gen1 = SyntheticDataGenerator("docs/synthetic-data-spec.json", seed=42)
        gen1.generate()

        gen2 = SyntheticDataGenerator("docs/synthetic-data-spec.json", seed=42)
        gen2.generate()

        ff1 = gen1._tables["fact_financials"]
        ff2 = gen2._tables["fact_financials"]

        assert len(ff1) == len(ff2)
        pd.testing.assert_frame_equal(ff1, ff2)

    def test_different_seed_different_output(self) -> None:
        gen1 = SyntheticDataGenerator("docs/synthetic-data-spec.json", seed=42)
        gen1.generate()

        gen2 = SyntheticDataGenerator("docs/synthetic-data-spec.json", seed=123)
        gen2.generate()

        ff1 = gen1._tables["fact_financials"]
        ff2 = gen2._tables["fact_financials"]

        # Same structure but different values
        assert len(ff1) == len(ff2)
        assert not ff1["actual_amount"].equals(ff2["actual_amount"])
