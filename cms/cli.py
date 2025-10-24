from __future__ import annotations
import os
from typing import List, Optional

import pandas as pd
import typer
from rich import print

from .extract import extract_from_zips
from .transform import transform_all
from .load import save_parquet, load_duckdb
from .validate import write_report
from .constants import DEFAULT_WAREHOUSE_DIR, DEFAULT_REPORTS_DIR
from .model import predict_next_star_for_ccn, persist_prediction, evaluate_predictions_for_release
from .insights import domain_trends_for_hospital, summarize_hospital

app = typer.Typer(help="CMS Hospital ETL runner")


@app.command()
def run(
    zip_list: List[str] = typer.Argument(..., help="Paths to ZIP files"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse output dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports output dir"),
):
    """Run full ETL: extract -> transform -> load -> validate."""
    print("[bold]Extracting[/bold] from ZIPs...")
    extracted = extract_from_zips(zip_list)
    if not extracted:
        print("[red]No target CSVs found in provided ZIPs[/red]")
        raise typer.Exit(code=1)

    # Prepare for transform
    tuples = [(e.dataset_key, e.release, e.frame) for e in extracted]
    releases = [e.release for e in extracted]

    print("[bold]Transforming[/bold] to standard schema...")
    tr = transform_all(tuples)

    print("[bold]Loading[/bold] to Parquet and DuckDB...")
    save_paths = save_parquet(tr.metrics, tr.star, tr.metrics_catalog, warehouse_dir)
    db_path = load_duckdb(tr.metrics, tr.star, tr.metrics_catalog, warehouse_dir)

    print("[bold]Validating[/bold] and generating report...")
    report_path = write_report(tr.metrics, tr.star, releases, reports_dir)

    print("[green]Done.[/green]")
    print({"parquet": save_paths, "duckdb": db_path, "report": report_path})


@app.command()
def query(
    ccn: str = typer.Argument(..., help="Hospital CCN (6 digits)"),
    start: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)"),
    domain: Optional[str] = typer.Option(None, help="Domain filter"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
):
    import duckdb
    db_path = os.path.join(warehouse_dir, "hospital.duckdb")
    if not os.path.exists(db_path):
        print(f"[red]DuckDB not found at {db_path}. Run etl first.[/red]")
        raise typer.Exit(code=1)

    con = duckdb.connect(db_path, read_only=True)
    try:
        sql = "SELECT * FROM hospital_metrics WHERE ccn = ?"
        params = [ccn]
        if start:
            sql += " AND period_end >= ?"; params.append(start)
        if end:
            sql += " AND period_end <= ?"; params.append(end)
        if domain:
            sql += " AND domain = ?"; params.append(domain)
        sql += " ORDER BY period_end DESC LIMIT 100"
        df = con.execute(sql, params).df()
        print(df.head(20))
    finally:
        con.close()


@app.command()
def sample(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR),
    out: Optional[str] = typer.Option(None, help="Output parquet path"),
):
    from .sample_extractor import build_star_training_sample
    path = build_star_training_sample(warehouse_dir, out)
    print({"sample": path})


@app.command()
def predict(
    ccn: str = typer.Argument(..., help="Hospital CCN (6 digits)"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
    steps_ahead: int = typer.Option(1, help="Months ahead to predict", min=1, max=6),
    save: bool = typer.Option(True, help="Persist prediction to DuckDB"),
):
    """Generate next-release star prediction with uncertainty and optional persistence."""
    pred = predict_next_star_for_ccn(ccn, warehouse_dir, steps_ahead=steps_ahead)
    if pred is None:
        print({"error": "No historical star data for CCN"})
        raise typer.Exit(code=1)
    if save:
        persist_prediction(pred, warehouse_dir)
    out = {
        "ccn": pred.ccn,
        "target_release": pred.target_release,
        "model": pred.model_name,
        "type": pred.prediction_type,
        "pred_star": round(pred.pred_star, 3),
        "conf": [pred.conf_lo, pred.conf_hi],
        "probs": pred.probs,
    }
    print(out)


@app.command()
def evaluate(
    target_release: str = typer.Argument(..., help="Release label YYYY_MM to evaluate"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
):
    """Compare saved predictions for a release vs official star when available."""
    df = evaluate_predictions_for_release(target_release, warehouse_dir)
    print({
        "evaluated": int(len(df)),
        "mae": None if df.empty else float(df["abs_error"].dropna().mean()),
        "coverage_68": None if df.empty else float(df["within_band"].mean()),
    })


@app.command()
def insights(
    ccn: str = typer.Argument(..., help="Hospital CCN (6 digits)"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
):
    """Show latest official star (if any), latest prediction, and domain trends."""
    summary = summarize_hospital(ccn, warehouse_dir)
    print(summary)


if __name__ == "__main__":
    app()
