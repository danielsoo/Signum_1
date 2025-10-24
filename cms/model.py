from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Dict, Optional

import duckdb
import numpy as np
import pandas as pd

from .constants import DEFAULT_WAREHOUSE_DIR
from .utils import parse_release_label, add_months_to_release


@dataclass(frozen=True)
class PredictionResult:
    ccn: str
    period_end: Optional[pd.Timestamp]
    target_release: str
    model_name: str
    prediction_type: str
    pred_star: float
    conf_lo: float
    conf_hi: float
    probs: Dict[int, float]


def _observed_star_series(con: duckdb.DuckDBPyConnection, ccn: str) -> pd.DataFrame:
    df = con.execute(
        """
        SELECT period_end, release, star_rating
        FROM hospital_star
        WHERE ccn = ? AND star_rating IS NOT NULL
        ORDER BY period_end
        """,
        [ccn],
    ).df()
    if not df.empty:
        df["period_end"] = pd.to_datetime(df["period_end"])
    return df


def _fit_transition_matrix(stars: pd.Series, alpha: float = 1.0) -> np.ndarray:
    """Estimate 5x5 transition probabilities with Laplace smoothing alpha.
    states are 1..5; we map to indices 0..4.
    """
    counts = np.ones((5, 5)) * alpha  # Laplace smoothing
    values = stars.dropna().astype(int).tolist()
    for a, b in zip(values[:-1], values[1:]):
        i = max(1, min(5, int(a))) - 1
        j = max(1, min(5, int(b))) - 1
        counts[i, j] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    P = counts / np.where(row_sums == 0, 1, row_sums)
    return P


def _roll_forward_probs(P: np.ndarray, initial_probs: np.ndarray, steps: int = 1) -> np.ndarray:
    v = initial_probs.copy()
    for _ in range(max(1, steps)):
        v = v @ P
    return v


def _conf_int_from_probs(probs: np.ndarray, level: float = 0.68) -> tuple[float, float]:
    # simple central interval from cumulative probs over stars 1..5
    stars = np.arange(1, 6)
    cdf = np.cumsum(probs)
    lo_idx = np.searchsorted(cdf, (1 - level) / 2)
    hi_idx = np.searchsorted(cdf, 1 - (1 - level) / 2)
    return float(stars[lo_idx]), float(stars[min(hi_idx, 4)])


def predict_next_star_for_ccn(
    ccn: str,
    warehouse_dir: Optional[str] = None,
    recency_weight: float = 0.9,
    steps_ahead: int = 1,
) -> Optional[PredictionResult]:
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        obs = _observed_star_series(con, ccn)
        if obs.empty:
            return None
        # determine next target_release as +1 month from latest release
        latest_rel = str(obs["release"].dropna().iloc[-1])
        target_release = add_months_to_release(latest_rel, months=steps_ahead) or latest_rel
        # training series with optional recency weighting (not used in simple MLE; could be expanded)
        P = _fit_transition_matrix(obs["star_rating"], alpha=1.0)
        last_star = int(round(float(obs["star_rating"].dropna().iloc[-1])))
        last_star = max(1, min(5, last_star))
        init = np.zeros(5)
        init[last_star - 1] = 1.0
        probs = _roll_forward_probs(P, init, steps=steps_ahead)
        pred = float(np.sum(probs * np.arange(1, 6)))
        lo, hi = _conf_int_from_probs(probs, level=0.68)
        period_end = pd.to_datetime(obs["period_end"].dropna().iloc[-1]) if not obs["period_end"].dropna().empty else None
        return PredictionResult(
            ccn=ccn,
            period_end=period_end,
            target_release=target_release,
            model_name="markov_transition_v1",
            prediction_type="direct_star",
            pred_star=pred,
            conf_lo=lo,
            conf_hi=hi,
            probs={i + 1: float(probs[i]) for i in range(5)},
        )
    finally:
        con.close()


def persist_prediction(pred: PredictionResult, warehouse_dir: Optional[str] = None) -> None:
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path)
    try:
        df = pd.DataFrame(
            [{
                "ccn": pred.ccn,
                "period_end": pred.period_end,
                "target_release": pred.target_release,
                "model_name": pred.model_name,
                "prediction_type": pred.prediction_type,
                "pred_star": pred.pred_star,
                "conf_lo": pred.conf_lo,
                "conf_hi": pred.conf_hi,
                "prob_star_1": pred.probs.get(1, 0.0),
                "prob_star_2": pred.probs.get(2, 0.0),
                "prob_star_3": pred.probs.get(3, 0.0),
                "prob_star_4": pred.probs.get(4, 0.0),
                "prob_star_5": pred.probs.get(5, 0.0),
                "generated_at": pd.Timestamp.utcnow(),
            }]
        )
        con.register("df_pred", df)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS star_predictions AS SELECT * FROM df_pred WHERE 1=0;
            """
        )
        con.execute("INSERT INTO star_predictions SELECT * FROM df_pred;")
    finally:
        con.close()


def evaluate_predictions_for_release(
    target_release: str,
    warehouse_dir: Optional[str] = None,
) -> pd.DataFrame:
    """Compare predictions for target_release to actual star when available.
    Writes rows into star_evaluations and returns the evaluation dataframe.
    """
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path)
    try:
        df = con.execute(
            """
            WITH latest_pred AS (
              SELECT *, ROW_NUMBER() OVER (PARTITION BY ccn, target_release, prediction_type ORDER BY generated_at DESC) rn
              FROM star_predictions
              WHERE target_release = ?
            ),
            p AS (
              SELECT * FROM latest_pred WHERE rn = 1
            ),
            a AS (
              SELECT ccn, star_rating AS actual_star, period_end, release
              FROM hospital_star
              WHERE release = ?
            )
            SELECT p.ccn, a.period_end, p.target_release, p.model_name, p.prediction_type,
                   p.pred_star, a.actual_star,
                   ABS(p.pred_star - a.actual_star) AS abs_error,
                   CASE WHEN a.actual_star BETWEEN p.conf_lo AND p.conf_hi THEN 1 ELSE 0 END AS within_band
            FROM p LEFT JOIN a USING(ccn)
            """,
            [target_release, target_release],
        ).df()

        if not df.empty:
            df["evaluated_at"] = pd.Timestamp.utcnow()
            con.register("df_eval", df)
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS star_evaluations AS SELECT * FROM df_eval WHERE 1=0;
                """
            )
            con.execute("INSERT INTO star_evaluations SELECT * FROM df_eval;")
        return df
    finally:
        con.close()
