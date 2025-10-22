# CMS Hospital Quality ETL

This repository contains a data pipeline to extract, standardize, and load CMS Provider Data Catalog (hospital topic) datasets from archived ZIP snapshots into a queryable warehouse (Parquet + DuckDB), generate validation reports, and prepare a sample dataset for AI modeling.

## Quickstart

1) Place/archive ZIP files (2018–present snapshots and latest release) and note their paths.

2) Install Python packages (inside your environment):

```bash
pip install -r cms_pipeline/requirements.txt
```

3) Run ETL (single command):

```bash
python -m cms_pipeline.cli run /path/to/zip1.zip /path/to/zip2.zip
```

Outputs:
- Parquet and DuckDB database in `warehouse/`
- Validation report in `reports/validation_report.md`

## Query Examples

```bash
python -m cms_pipeline.cli query 390048 --start 2023-01-01 --end 2024-12-31 --domain Mortality
```

## Sample Extraction (Star rating target)

```bash
python -m cms_pipeline.cli sample
```

Produces `warehouse/sample_star_training.parquet`.

## Schemas

- `hospital_metrics`: long-form timeseries with keys `(ccn, measure_id, period_end, release)` and columns: `ccn, measure_id, measure_name, domain, unit, direction, period_start, period_end, release, value, value_lo, value_hi, denominator, compare_to_national, reason, facility_name, state, city, zip`.
- `hospital_star`: keys `(ccn, period_end, release)` with `star_rating` and facility/period metadata.
- `metrics_catalog`: unique measure dictionary with `(measure_id, measure_name, domain, unit, direction)`.

## Notes

- The extractor matches target CSVs in ZIPs by filename patterns and infers `release` from the ZIP filename (e.g., `2025_08`).
- Missing/footnote reasons are standardized; unmapped entries default to `OTHER`.
- Use Parquet files directly or query DuckDB for interactive analysis.
