from __future__ import annotations
import os
from typing import Optional

import pandas as pd
from jinja2 import Template

from .constants import DEFAULT_REPORTS_DIR


TEMPLATE_MD = Template(
    """
# CMS Hospital Data Validation Report

- Release files processed: {{ releases_count }}
- Unique releases: {{ unique_releases }}

## Summary

- Total rows (metrics): {{ metrics_rows }}
- Unique hospitals (metrics): {{ metrics_ccn }}
- Unique measures: {{ metrics_measures }}
- Period range (metrics): {{ metrics_period_min }} — {{ metrics_period_max }}

- Total rows (star): {{ star_rows }}
- Unique hospitals (star): {{ star_ccn }}
- Period range (star): {{ star_period_min }} — {{ star_period_max }}

## Missing/Reason Distribution (Top 10)

### Metrics.reason

{% if metrics_reason %}
| reason | count |
|---|---:|
{% for k, v in metrics_reason %}| {{k}} | {{v}} |
{% endfor %}
{% else %}
No reasons found.
{% endif %}

### Star.reason

{% if star_reason %}
| reason | count |
|---|---:|
{% for k, v in star_reason %}| {{k}} | {{v}} |
{% endfor %}
{% else %}
No reasons found.
{% endif %}

## Duplicate Keys

- Metrics duplicates on (ccn, measure_id, period_end, release): {{ metrics_dupes }}
- Star duplicates on (ccn, period_end, release): {{ star_dupes }}

## Example Queries

- Example 1: CCN=390048, 2023-01-01—2024-12-31 Mortality metrics
- Example 2: Join metrics to star by (ccn, period_end, release)

"""
)


def _top_counts(series: pd.Series, n: int = 10):
    counts = series.dropna().astype(str).value_counts().head(n)
    return list(counts.items())


def _minmax(series: pd.Series):
    if series.dropna().empty:
        return None, None
    return series.min(), series.max()


def write_report(metrics: pd.DataFrame, star: pd.DataFrame, releases: list[str], reports_dir: Optional[str] = None) -> str:
    rd = reports_dir or DEFAULT_REPORTS_DIR
    os.makedirs(rd, exist_ok=True)

    metrics_rows = int(len(metrics)) if metrics is not None else 0
    metrics_ccn = int(metrics["ccn"].nunique()) if metrics_rows else 0
    metrics_measures = int(metrics["measure_id"].nunique()) if metrics_rows else 0
    m_pmin, m_pmax = (None, None)
    if metrics_rows and "period_end" in metrics.columns:
        m_pmin, m_pmax = _minmax(pd.to_datetime(metrics["period_end"]))

    star_rows = int(len(star)) if star is not None else 0
    star_ccn = int(star["ccn"].nunique()) if star_rows else 0
    s_pmin, s_pmax = (None, None)
    if star_rows and "period_end" in star.columns:
        s_pmin, s_pmax = _minmax(pd.to_datetime(star["period_end"]))

    metrics_reason = _top_counts(metrics["reason"]) if metrics_rows and "reason" in metrics.columns else []
    star_reason = _top_counts(star["reason"]) if star_rows and "reason" in star.columns else []

    metrics_dupes = 0
    if metrics_rows:
        metrics_dupes = int(
            metrics.groupby(["ccn", "measure_id", "period_end", "release"]).size().gt(1).sum()
        )
    star_dupes = 0
    if star_rows:
        star_dupes = int(
            star.groupby(["ccn", "period_end", "release"]).size().gt(1).sum()
        )

    unique_releases = sorted(set(releases))
    text = TEMPLATE_MD.render(
        releases_count=len(releases),
        unique_releases=unique_releases,
        metrics_rows=metrics_rows,
        metrics_ccn=metrics_ccn,
        metrics_measures=metrics_measures,
        metrics_period_min=m_pmin,
        metrics_period_max=m_pmax,
        star_rows=star_rows,
        star_ccn=star_ccn,
        star_period_min=s_pmin,
        star_period_max=s_pmax,
        metrics_reason=metrics_reason,
        star_reason=star_reason,
        metrics_dupes=metrics_dupes,
        star_dupes=star_dupes,
    )

    out_path = os.path.join(rd, "validation_report.md")
    with open(out_path, "w") as f:
        f.write(text)
    return out_path
