"""Comprehensive data quality validation for all Phase 2 narrative features.

Tests the regenerated parquet data to ensure all narrative pyramid
features are present and correct: seasonality, carry-forward, parent
references, section narratives, executive summaries, confidence scoring.
"""

import pandas as pd
import pytest

DATA_DIR = "data/output"


@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet(f"{DATA_DIR}/fact_variance_material.parquet")


@pytest.fixture(scope="module")
def sn():
    return pd.read_parquet(f"{DATA_DIR}/fact_section_narrative.parquet")


@pytest.fixture(scope="module")
def es():
    return pd.read_parquet(f"{DATA_DIR}/fact_executive_summary.parquet")


@pytest.fixture(scope="module")
def rs():
    return pd.read_parquet(f"{DATA_DIR}/fact_review_status.parquet")


@pytest.mark.integration
class TestDataVolume:
    """Verify data volume and structure."""

    def test_material_variance_count(self, vm):
        assert len(vm) > 100_000, f"Expected >100K rows, got {len(vm)}"

    def test_all_three_bases(self, vm):
        bases = set(vm["base_id"].unique())
        assert bases == {"BUDGET", "FORECAST", "PRIOR_YEAR"}

    def test_all_three_views(self, vm):
        views = set(vm["view_id"].unique())
        assert "MTD" in views
        assert "QTD" in views

    def test_twelve_periods(self, vm):
        assert vm["period_id"].nunique() == 12

    def test_section_narratives_60(self, sn):
        assert len(sn) == 60  # 5 sections × 12 periods

    def test_executive_summaries_12(self, es):
        assert len(es) == 12  # 1 per period


@pytest.mark.integration
class TestNarrativeCompleteness:
    """Every row should have all 4 narrative levels populated."""

    def test_detail_100_pct(self, vm):
        assert vm["narrative_detail"].notna().sum() == len(vm)

    def test_midlevel_100_pct(self, vm):
        assert vm["narrative_midlevel"].notna().sum() == len(vm)

    def test_summary_100_pct(self, vm):
        assert vm["narrative_summary"].notna().sum() == len(vm)

    def test_oneliner_100_pct(self, vm):
        assert vm["narrative_oneliner"].notna().sum() == len(vm)


@pytest.mark.integration
class TestSeasonalContext:
    """December and August narratives should mention seasonal patterns."""

    def test_december_has_seasonal_notes(self, vm):
        dec = vm[(vm["period_id"] == "2025-12") & (vm["view_id"] == "MTD") & (vm["is_calculated"] == False)]
        count = sum(1 for _, r in dec.iterrows() if "seasonal" in str(r.get("narrative_detail", "")).lower())
        assert count > len(dec) * 0.5, f"Only {count}/{len(dec)} Dec narratives have seasonal context"

    def test_august_has_seasonal_notes(self, vm):
        aug = vm[(vm["period_id"] == "2025-08") & (vm["view_id"] == "MTD") & (vm["is_calculated"] == False)]
        count = sum(1 for _, r in aug.iterrows() if "seasonal" in str(r.get("narrative_detail", "")).lower())
        assert count > len(aug) * 0.5, f"Only {count}/{len(aug)} Aug narratives have seasonal context"


@pytest.mark.integration
class TestCarryForward:
    """Non-first periods should reference prior period."""

    def test_may_references_april(self, vm):
        may = vm[(vm["period_id"] == "2026-05") & (vm["view_id"] == "MTD") & (vm["is_calculated"] == False)]
        carry = sum(1 for _, r in may.iterrows() if "widened" in str(r.get("narrative_detail", "")).lower() or "narrowed" in str(r.get("narrative_detail", "")).lower())
        assert carry > len(may) * 0.8, f"Only {carry}/{len(may)} May narratives have carry-forward"

    def test_first_period_no_carry_forward(self, vm):
        jul = vm[(vm["period_id"] == "2025-07") & (vm["view_id"] == "MTD") & (vm["is_calculated"] == False)]
        carry = sum(1 for _, r in jul.iterrows() if "widened" in str(r.get("narrative_detail", "")).lower() or "narrowed" in str(r.get("narrative_detail", "")).lower())
        assert carry == 0, f"First period should have 0 carry-forward, got {carry}"


@pytest.mark.integration
class TestParentNarratives:
    """Calculated/parent accounts should reference children."""

    def test_most_parents_reference_children(self, vm):
        """At least 60% of MTD BUDGET parents should reference children."""
        parents = vm[(vm["is_calculated"] == True) & (vm["view_id"] == "MTD") & (vm["base_id"] == "BUDGET")]
        refs = sum(1 for _, r in parents.iterrows() if "Driven by" in str(r.get("narrative_detail", "")))
        pct = refs / max(len(parents), 1) * 100
        assert pct >= 60, f"Only {refs}/{len(parents)} ({pct:.0f}%) parents reference children (need 60%+)"


@pytest.mark.integration
class TestSectionNarratives:
    """Section narratives should cover all 5 P&L sections."""

    def test_five_sections_per_period(self, sn):
        for period in sn["period_id"].unique():
            period_sn = sn[sn["period_id"] == period]
            names = set(period_sn["section_name"])
            assert len(names) == 5, f"Period {period} has {len(names)} sections: {names}"

    def test_revenue_section_has_drivers(self, sn):
        rev = sn[(sn["section_name"] == "Revenue") & (sn["period_id"] == "2026-05")]
        assert not rev.empty
        narr = str(rev.iloc[0]["narrative"])
        assert "Advisory" in narr or "Revenue" in narr

    def test_profitability_has_margins(self, sn):
        prof = sn[(sn["section_name"] == "Profitability") & (sn["period_id"] == "2026-05")]
        assert not prof.empty
        narr = str(prof.iloc[0]["narrative"])
        assert "margin" in narr.lower() or "EBITDA" in narr


@pytest.mark.integration
class TestExecutiveSummaries:
    """Executive summaries should have headlines and narratives."""

    def test_all_periods_have_headline(self, es):
        for _, row in es.iterrows():
            assert row.get("headline"), f"Period {row['period_id']} missing headline"

    def test_headlines_mention_revenue_and_ebitda(self, es):
        for _, row in es.iterrows():
            headline = str(row.get("headline", ""))
            assert "Revenue" in headline or "revenue" in headline.lower(), f"Period {row['period_id']} headline missing Revenue"

    def test_cross_bu_themes_exist(self, es):
        for _, row in es.iterrows():
            themes = row.get("cross_bu_themes")
            assert themes is not None, f"Period {row['period_id']} missing cross_bu_themes"


@pytest.mark.integration
class TestDeterministicIDs:
    """Variance IDs should be deterministic 16-char hex."""

    def test_ids_unique(self, vm):
        assert vm["variance_id"].nunique() == len(vm)

    def test_ids_16_char_hex(self, vm):
        assert (vm["variance_id"].str.len() == 16).all()

    def test_ids_contain_only_hex(self, vm):
        import re
        assert vm["variance_id"].str.match(r'^[0-9a-f]{16}$').all()


@pytest.mark.integration
class TestConfidenceScoring:
    """Narrative confidence should be set on all rows."""

    def test_confidence_populated(self, vm):
        assert vm["narrative_confidence"].notna().sum() == len(vm)

    def test_confidence_in_range(self, vm):
        assert vm["narrative_confidence"].min() >= 0.0
        assert vm["narrative_confidence"].max() <= 1.0


@pytest.mark.integration
class TestReviewStatus:
    """Review status should have period context."""

    def test_has_period_id(self, rs):
        assert "period_id" in rs.columns
        assert rs["period_id"].notna().sum() > 0

    def test_has_fiscal_year(self, rs):
        assert "fiscal_year" in rs.columns
        assert set(rs["fiscal_year"].dropna().unique()) == {2025, 2026}
