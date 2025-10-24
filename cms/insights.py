from __future__ import annotations
import os
from typing import Optional, Dict

import duckdb
import pandas as pd

from .constants import DEFAULT_WAREHOUSE_DIR


def domain_trends_for_hospital(ccn: str, warehouse_dir: Optional[str] = None) -> pd.DataFrame:
    """Compute simple domain trends (recent slope) for a hospital.

    Returns dataframe with columns: domain, measure_count, slope_sign, slope_value
    where slope_sign in {improving, worsening, flat} using last 4 periods per domain.
    """
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(
            """
            WITH recent AS (
              SELECT ccn, domain, period_end, value
              FROM hospital_metrics
              WHERE ccn = ? AND value IS NOT NULL AND domain IS NOT NULL
            ),
            ranked AS (
              SELECT *, ROW_NUMBER() OVER (PARTITION BY domain ORDER BY period_end DESC) rn
              FROM recent
            )
            SELECT domain, period_end, value
            FROM ranked
            WHERE rn <= 4
            ORDER BY domain, period_end
            """,
            [ccn],
        ).df()
        if df.empty:
            return pd.DataFrame(columns=["domain", "measure_count", "slope_sign", "slope_value"])
        out_rows = []
        for domain, grp in df.groupby("domain"):
            grp = grp.sort_values("period_end")
            x = (pd.to_datetime(grp["period_end"]).view("int64") / 1e9).values
            y = grp["value"].astype(float).values
            if len(x) < 2:
                slope = 0.0
            else:
                # simple least squares: slope = cov(x,y)/var(x)
                x_mean = x.mean()
                y_mean = y.mean()
                denom = ((x - x_mean) ** 2).sum()
                slope = 0.0 if denom == 0 else float(((x - x_mean) * (y - y_mean)).sum() / denom)
            if abs(slope) < 1e-9:
                sign = "flat"
            else:
                sign = "improving" if slope > 0 else "worsening"
            out_rows.append({
                "domain": domain,
                "measure_count": int(len(grp)),
                "slope_sign": sign,
                "slope_value": slope,
            })
        return pd.DataFrame(out_rows)
    finally:
        con.close()


def _narrative_from_trends(trends_df: pd.DataFrame) -> Optional[str]:
    if trends_df is None or trends_df.empty:
        return None
    improving = [d for d, s in zip(trends_df["domain"], trends_df["slope_sign"]) if s == "improving"]
    worsening = [d for d, s in zip(trends_df["domain"], trends_df["slope_sign"]) if s == "worsening"]
    parts = []
    if improving:
        parts.append("improving in " + ", ".join(improving))
    if worsening:
        parts.append("worsening in " + ", ".join(worsening))
    if not parts:
        return "performance appears flat across domains"
    return "; ".join(parts)


def summarize_hospital(ccn: str, warehouse_dir: Optional[str] = None) -> Dict[str, object]:
    """Build a compact summary including latest official star and latest prediction."""
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        latest_star = con.execute(
            """
            SELECT ccn, star_rating, period_end, release, facility_name, state
            FROM hospital_star
            WHERE ccn = ? AND star_rating IS NOT NULL
            ORDER BY release DESC, period_end DESC
            LIMIT 1
            """,
            [ccn],
        ).df()
        latest_pred = con.execute(
            """
            SELECT * FROM star_predictions
            WHERE ccn = ?
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            [ccn],
        ).df()
        trends = domain_trends_for_hospital(ccn, warehouse_dir)
        return {
            "ccn": ccn,
            "official_star": None if latest_star.empty else float(latest_star["star_rating"].iloc[0]),
            "official_release": None if latest_star.empty else str(latest_star["release"].iloc[0]),
            "prediction": None if latest_pred.empty else latest_pred.to_dict(orient="records")[0],
            "trends": trends.to_dict(orient="records"),
            "narrative": _narrative_from_trends(trends),
        }
    finally:
        con.close()
