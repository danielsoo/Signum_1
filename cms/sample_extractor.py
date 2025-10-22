from __future__ import annotations
import os
from typing import Optional

import duckdb
import pandas as pd

from .constants import DEFAULT_WAREHOUSE_DIR


def build_star_training_sample(
    warehouse_dir: Optional[str] = None,
    out_path: Optional[str] = None,
    recent_releases: int = 3,
) -> str:
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        # Identify latest N releases
        releases_rows = con.execute(
            "SELECT DISTINCT release FROM hospital_star ORDER BY release DESC LIMIT ?",
            [recent_releases],
        ).fetchall()
        releases = [r[0] for r in releases_rows]
        if not releases:
            raise RuntimeError("No releases found in hospital_star")

        # Register releases as a temp table for IN clause
        releases_df = pd.DataFrame({"release": releases})
        con.register("releases_df", releases_df)

        # Simple feature set: average value by measure_id for recent releases
        df = con.execute(
            """
            WITH recent AS (
              SELECT * FROM hospital_metrics
              WHERE release IN (SELECT release FROM releases_df)
            ),
            agg AS (
              SELECT ccn, measure_id, AVG(value) AS value_mean
              FROM recent
              GROUP BY ccn, measure_id
            ),
            wide AS (
              SELECT ccn,
                     STRING_AGG(measure_id || '=' || CAST(ROUND(value_mean, 4) AS VARCHAR), ',') AS features
              FROM agg
              GROUP BY ccn
            )
            SELECT s.ccn, s.star_rating, s.period_end, s.release, w.features
            FROM hospital_star s
            LEFT JOIN wide w USING(ccn)
            WHERE s.release IN (SELECT release FROM releases_df)
            """
        ).df()

        out = out_path or os.path.join(wd, "sample_star_training.parquet")
        df.to_parquet(out, index=False)
        return out
    finally:
        con.close()
