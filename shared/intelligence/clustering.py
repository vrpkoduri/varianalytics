"""Theme Clustering — groups related variances by DBSCAN.

Uses dimensional + magnitude features to cluster variances into
coherent themes (e.g., "APAC Revenue Weakness").

Falls back to simple dimension-based grouping if sklearn unavailable.

Example output:
    {"theme": "APAC Revenue Weakness", "variance_count": 12, "total_amount": -2.1M}
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# DBSCAN parameters
_EPS = 0.5
_MIN_SAMPLES = 3


def compute_theme_clusters(
    material_variances: pd.DataFrame,
    period_id: str,
) -> list[dict[str, Any]]:
    """Cluster variances into themes.

    Args:
        material_variances: All material variances for the period.
        period_id: Current period for filtering.

    Returns:
        List of cluster dicts with theme, count, total_amount, members.
    """
    if material_variances.empty:
        return []

    # Filter to current period + MTD + BUDGET
    mask = material_variances["period_id"] == period_id
    if "view_id" in material_variances.columns:
        mask &= material_variances["view_id"] == "MTD"
    if "base_id" in material_variances.columns:
        mask &= material_variances["base_id"] == "BUDGET"

    df = material_variances[mask].copy()
    if len(df) < _MIN_SAMPLES:
        return []

    # Try DBSCAN first, fall back to simple grouping
    try:
        return _dbscan_clustering(df)
    except Exception:
        logger.debug("DBSCAN unavailable or failed — using simple grouping")
        return _simple_grouping(df)


def _dbscan_clustering(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DBSCAN-based clustering on feature vectors."""
    try:
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return _simple_grouping(df)

    # Build feature matrix
    features = _build_features(df)
    if features is None or len(features) < _MIN_SAMPLES:
        return _simple_grouping(df)

    # Scale features
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    # Cluster
    dbscan = DBSCAN(eps=_EPS, min_samples=_MIN_SAMPLES)
    labels = dbscan.fit_predict(X)

    df = df.copy()
    df["cluster_label"] = labels

    # Build cluster results (exclude noise = -1)
    clusters = []
    for label in sorted(set(labels)):
        if label == -1:
            continue
        cluster_df = df[df["cluster_label"] == label]
        cluster = _build_cluster_dict(label, cluster_df)
        clusters.append(cluster)

    return clusters


def _simple_grouping(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Simple fallback: group by pl_category + dominant geo."""
    clusters = []
    cluster_id = 0

    for pl_cat in df["pl_category"].dropna().unique():
        cat_df = df[df["pl_category"] == pl_cat]
        if len(cat_df) < 2:
            continue

        # Sub-group by geo if available
        if "geo_node_id" in cat_df.columns:
            for geo in cat_df["geo_node_id"].dropna().unique():
                geo_df = cat_df[cat_df["geo_node_id"] == geo]
                if len(geo_df) >= 2:
                    cluster = _build_cluster_dict(cluster_id, geo_df)
                    cluster["theme"] = f"{geo} {pl_cat}"
                    clusters.append(cluster)
                    cluster_id += 1
        else:
            cluster = _build_cluster_dict(cluster_id, cat_df)
            cluster["theme"] = str(pl_cat)
            clusters.append(cluster)
            cluster_id += 1

    return clusters


def _build_features(df: pd.DataFrame) -> np.ndarray | None:
    """Build numerical feature matrix for clustering."""
    feature_cols = []

    # Normalized variance amount
    if "variance_amount" in df.columns:
        va = df["variance_amount"].fillna(0).values
        max_abs = np.abs(va).max()
        if max_abs > 0:
            feature_cols.append(va / max_abs)

    # Variance percentage
    if "variance_pct" in df.columns:
        vp = df["variance_pct"].fillna(0).values
        feature_cols.append(vp)

    # Encoded pl_category
    if "pl_category" in df.columns:
        cats = df["pl_category"].fillna("Other")
        cat_codes = cats.astype("category").cat.codes.values.astype(float)
        max_code = cat_codes.max() if cat_codes.max() > 0 else 1
        feature_cols.append(cat_codes / max_code)

    # Encoded geo
    if "geo_node_id" in df.columns:
        geos = df["geo_node_id"].fillna("Other")
        geo_codes = geos.astype("category").cat.codes.values.astype(float)
        max_geo = geo_codes.max() if geo_codes.max() > 0 else 1
        feature_cols.append(geo_codes / max_geo)

    # Encoded BU
    if "bu_id" in df.columns:
        bus = df["bu_id"].fillna("Other")
        bu_codes = bus.astype("category").cat.codes.values.astype(float)
        max_bu = bu_codes.max() if bu_codes.max() > 0 else 1
        feature_cols.append(bu_codes / max_bu)

    if not feature_cols:
        return None

    return np.column_stack(feature_cols)


def _build_cluster_dict(cluster_id: int, cluster_df: pd.DataFrame) -> dict[str, Any]:
    """Build a cluster result dict from a subset DataFrame."""
    total_amount = float(cluster_df["variance_amount"].sum())
    members = cluster_df["variance_id"].tolist() if "variance_id" in cluster_df.columns else []

    # Find common dimensions
    common = {}
    for col in ["pl_category", "geo_node_id", "bu_id", "segment_node_id"]:
        if col in cluster_df.columns:
            mode = cluster_df[col].mode()
            if not mode.empty:
                common[col.replace("_node_id", "").replace("_id", "")] = str(mode.iloc[0])

    # Auto-generate theme name
    direction = "Weakness" if total_amount < 0 else "Strength"
    theme_parts = []
    if "geo" in common:
        theme_parts.append(common["geo"])
    if "pl_category" in common:
        theme_parts.append(common["pl_category"])
    theme_parts.append(direction)
    theme = " ".join(theme_parts) if theme_parts else f"Cluster {cluster_id}"

    return {
        "cluster_id": cluster_id,
        "theme": theme,
        "variance_count": len(cluster_df),
        "total_amount": round(total_amount, 2),
        "members": members[:20],  # Limit to 20 IDs
        "common_dimensions": common,
    }
