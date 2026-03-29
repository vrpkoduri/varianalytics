"""Organizational unit mapping: BU × CostCenter → (Geography, Segment, LOB).

Defines which cost centers are active per BU (eligibility matrix) and the
deterministic mapping of each (BU, CC) pair to its geography, segment, and
line of business.

This mapping is the structural backbone of fact_financials — the grain is
(Period × BU × CostCenter × Account), and Geo/Segment/LOB are denormalized
attributes of the org unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrgUnit:
    """A single organizational unit: one BU + CostCenter combination."""

    bu_id: str
    costcenter_id: str
    geo_node_id: str
    segment_node_id: str
    lob_node_id: str


# =============================================================================
# BU → Eligible Cost Centers
# =============================================================================
# Not every BU has every CC. This reflects real org structure.

BU_CC_ELIGIBILITY: dict[str, list[str]] = {
    "marsh": [
        # Client-facing
        "cc_new_biz", "cc_acct_mgmt", "cc_advisory_teams", "cc_placement",
        "cc_claims", "cc_client_success",
        # Corporate
        "cc_finance", "cc_hr", "cc_legal", "cc_marketing",
        # Technology
        "cc_infra_cloud", "cc_app_dev", "cc_data_eng",
        # Executive
        "cc_exec_office",
    ],
    "mercer": [
        # Client-facing (no placement/claims — consulting firm)
        "cc_new_biz", "cc_acct_mgmt", "cc_advisory_teams", "cc_client_success",
        # Corporate
        "cc_finance", "cc_hr", "cc_legal", "cc_marketing", "cc_strategy",
        # Technology
        "cc_infra_cloud", "cc_app_dev", "cc_data_eng",
        # Executive
        "cc_exec_office",
    ],
    "guy_carpenter": [
        # Client-facing (reinsurance broker — placement heavy)
        "cc_new_biz", "cc_acct_mgmt", "cc_advisory_teams", "cc_placement",
        "cc_client_success",
        # Corporate
        "cc_finance", "cc_hr", "cc_legal",
        # Technology
        "cc_infra_cloud", "cc_app_dev",
        # Executive
        "cc_exec_office",
    ],
    "oliver_wyman": [
        # Client-facing (pure consulting — no placement/claims)
        "cc_new_biz", "cc_acct_mgmt", "cc_advisory_teams", "cc_client_success",
        # Corporate
        "cc_finance", "cc_hr", "cc_legal", "cc_marketing", "cc_strategy",
        # Technology
        "cc_app_dev", "cc_data_eng",
        # Executive
        "cc_exec_office",
    ],
    "mmc_corporate": [
        # Corporate functions only — no client-facing ops
        "cc_finance", "cc_hr", "cc_legal", "cc_marketing", "cc_strategy",
        # Technology (shared services)
        "cc_infra_cloud", "cc_app_dev", "cc_data_eng", "cc_cybersecurity",
        # Executive
        "cc_exec_office",
    ],
}


# =============================================================================
# (BU, CC) → (Geo, Segment, LOB) Mapping
# =============================================================================
# Each org unit sits in a specific geography, serves a segment, and belongs
# to a line of business. Designed to spread across geos per BU's distribution
# weights and create interesting variance analysis scenarios.

_ORG_UNIT_MAP: dict[tuple[str, str], tuple[str, str, str]] = {
    # ---- MARSH (14 CCs) ----
    # Client-facing spread across key geographies
    ("marsh", "cc_new_biz"):        ("geo_us_ne", "seg_large_corp", "lob_pc"),
    ("marsh", "cc_acct_mgmt"):      ("geo_us_se", "seg_mid_market", "lob_pc"),
    ("marsh", "cc_advisory_teams"): ("geo_uk_ireland", "seg_large_corp", "lob_fin_prof"),
    ("marsh", "cc_placement"):      ("geo_us_w", "seg_specialty", "lob_pc"),
    ("marsh", "cc_claims"):         ("geo_us_mw", "seg_commercial", "lob_pc"),
    ("marsh", "cc_client_success"): ("geo_anz", "seg_mid_market", "lob_cyber"),
    # Corporate in US HQ
    ("marsh", "cc_finance"):        ("geo_us_ne", "seg_large_corp", "lob_risk_advisory"),
    ("marsh", "cc_hr"):             ("geo_us_ne", "seg_large_corp", "lob_risk_advisory"),
    ("marsh", "cc_legal"):          ("geo_us_ne", "seg_large_corp", "lob_risk_advisory"),
    ("marsh", "cc_marketing"):      ("geo_germany", "seg_commercial", "lob_risk_advisory"),
    # Technology spread globally
    ("marsh", "cc_infra_cloud"):    ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("marsh", "cc_app_dev"):        ("geo_singapore", "seg_large_corp", "lob_data_analytics"),
    ("marsh", "cc_data_eng"):       ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("marsh", "cc_exec_office"):    ("geo_us_ne", "seg_large_corp", "lob_risk_advisory"),

    # ---- MERCER (13 CCs) ----
    ("mercer", "cc_new_biz"):        ("geo_us_ne", "seg_large_corp", "lob_hr_workforce"),
    ("mercer", "cc_acct_mgmt"):      ("geo_uk_ireland", "seg_large_corp", "lob_hr_workforce"),
    ("mercer", "cc_advisory_teams"): ("geo_france", "seg_large_corp", "lob_invest_advisory"),
    ("mercer", "cc_client_success"): ("geo_canada", "seg_mid_market", "lob_hr_workforce"),
    ("mercer", "cc_finance"):        ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mercer", "cc_hr"):             ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mercer", "cc_legal"):          ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mercer", "cc_marketing"):      ("geo_uk_ireland", "seg_consumer", "lob_consulting"),
    ("mercer", "cc_strategy"):       ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mercer", "cc_infra_cloud"):    ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("mercer", "cc_app_dev"):        ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("mercer", "cc_data_eng"):       ("geo_singapore", "seg_large_corp", "lob_data_analytics"),
    ("mercer", "cc_exec_office"):    ("geo_us_ne", "seg_large_corp", "lob_consulting"),

    # ---- GUY CARPENTER (11 CCs) ----
    ("guy_carpenter", "cc_new_biz"):        ("geo_us_ne", "seg_specialty", "lob_treaty"),
    ("guy_carpenter", "cc_acct_mgmt"):      ("geo_uk_ireland", "seg_specialty", "lob_treaty"),
    ("guy_carpenter", "cc_advisory_teams"): ("geo_germany", "seg_specialty", "lob_facultative"),
    ("guy_carpenter", "cc_placement"):      ("geo_uk_ireland", "seg_specialty", "lob_treaty"),
    ("guy_carpenter", "cc_client_success"): ("geo_japan", "seg_specialty", "lob_reinsurance"),
    ("guy_carpenter", "cc_finance"):        ("geo_us_ne", "seg_specialty", "lob_reinsurance"),
    ("guy_carpenter", "cc_hr"):             ("geo_us_ne", "seg_specialty", "lob_reinsurance"),
    ("guy_carpenter", "cc_legal"):          ("geo_uk_ireland", "seg_specialty", "lob_reinsurance"),
    ("guy_carpenter", "cc_infra_cloud"):    ("geo_india", "seg_specialty", "lob_data_analytics"),
    ("guy_carpenter", "cc_app_dev"):        ("geo_india", "seg_specialty", "lob_data_analytics"),
    ("guy_carpenter", "cc_exec_office"):    ("geo_us_ne", "seg_specialty", "lob_reinsurance"),

    # ---- OLIVER WYMAN (13 CCs) ----
    ("oliver_wyman", "cc_new_biz"):        ("geo_us_ne", "seg_large_corp", "lob_mgmt_consulting"),
    ("oliver_wyman", "cc_acct_mgmt"):      ("geo_uk_ireland", "seg_large_corp", "lob_mgmt_consulting"),
    ("oliver_wyman", "cc_advisory_teams"): ("geo_france", "seg_large_corp", "lob_mgmt_consulting"),
    ("oliver_wyman", "cc_client_success"): ("geo_hong_kong", "seg_large_corp", "lob_mgmt_consulting"),
    ("oliver_wyman", "cc_finance"):        ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("oliver_wyman", "cc_hr"):             ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("oliver_wyman", "cc_legal"):          ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("oliver_wyman", "cc_marketing"):      ("geo_netherlands", "seg_mid_market", "lob_consulting"),
    ("oliver_wyman", "cc_strategy"):       ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("oliver_wyman", "cc_app_dev"):        ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("oliver_wyman", "cc_data_eng"):       ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("oliver_wyman", "cc_exec_office"):    ("geo_us_ne", "seg_large_corp", "lob_consulting"),

    # ---- MMC CORPORATE (10 CCs) ----
    ("mmc_corporate", "cc_finance"):     ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mmc_corporate", "cc_hr"):          ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mmc_corporate", "cc_legal"):       ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mmc_corporate", "cc_marketing"):   ("geo_us_mw", "seg_commercial", "lob_consulting"),
    ("mmc_corporate", "cc_strategy"):    ("geo_us_ne", "seg_large_corp", "lob_consulting"),
    ("mmc_corporate", "cc_infra_cloud"): ("geo_us_w", "seg_large_corp", "lob_data_analytics"),
    ("mmc_corporate", "cc_app_dev"):     ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("mmc_corporate", "cc_data_eng"):    ("geo_india", "seg_large_corp", "lob_data_analytics"),
    ("mmc_corporate", "cc_cybersecurity"):("geo_us_ne", "seg_large_corp", "lob_data_analytics"),
    ("mmc_corporate", "cc_exec_office"): ("geo_us_ne", "seg_large_corp", "lob_consulting"),
}


def get_org_units() -> list[OrgUnit]:
    """Return all valid (BU, CC) org units with their mapped dimensions.

    Returns:
        List of OrgUnit instances — one per active (BU, CC) combination.
    """
    units = []
    for (bu_id, cc_id), (geo_id, seg_id, lob_id) in _ORG_UNIT_MAP.items():
        units.append(OrgUnit(
            bu_id=bu_id,
            costcenter_id=cc_id,
            geo_node_id=geo_id,
            segment_node_id=seg_id,
            lob_node_id=lob_id,
        ))
    return units


def get_org_units_for_bu(bu_id: str) -> list[OrgUnit]:
    """Return org units for a specific BU."""
    return [u for u in get_org_units() if u.bu_id == bu_id]


def get_eligible_cc_ids(bu_id: str) -> list[str]:
    """Return eligible cost center IDs for a BU."""
    return BU_CC_ELIGIBILITY.get(bu_id, [])


def get_org_unit(bu_id: str, cc_id: str) -> OrgUnit | None:
    """Look up the org unit for a specific (BU, CC) pair."""
    key = (bu_id, cc_id)
    if key not in _ORG_UNIT_MAP:
        return None
    geo_id, seg_id, lob_id = _ORG_UNIT_MAP[key]
    return OrgUnit(
        bu_id=bu_id,
        costcenter_id=cc_id,
        geo_node_id=geo_id,
        segment_node_id=seg_id,
        lob_node_id=lob_id,
    )
