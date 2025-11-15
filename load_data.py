#!/usr/bin/env python3
"""
Load hospital data directly from CSV files (not ZIP)
"""
import pandas as pd
from provider.hospital.constants import DEFAULT_WAREHOUSE_DIR
from provider.hospital.load import save_parquet, load_duckdb
from provider.hospital.transform import transform_all
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "provider"))

print("🏥 Loading Hospital Data from CSV Files\n")

# Import modules

# Data directory
data_dir = project_root / "hospitals_current_data"
warehouse_dir = project_root / "provider" / "hospital" / "warehouse"
warehouse_dir.mkdir(parents=True, exist_ok=True)

if not data_dir.exists():
    print(f"❌ Error: Directory not found: {data_dir}")
    print("Make sure hospitals_current_data/ is in the project root")
    sys.exit(1)

print(f"📁 Data directory: {data_dir}")
print(f"📁 Warehouse directory: {warehouse_dir}")

# Define file mappings
file_map = {
    "complications_deaths": "Complications_and_Deaths-Hospital.csv",
    "readmissions_deaths": "Unplanned_Hospital_Visits-Hospital.csv",  # Updated
    "hcahps": "HCAHPS-Hospital.csv",
    "timely_effective": "Timely_and_Effective_Care-Hospital.csv",
    "overall_star": "Hospital_General_Information.csv",
}

print("\n📊 Loading CSV files...")
raw_data = {}
for key, filename in file_map.items():
    filepath = data_dir / filename
    if filepath.exists():
        print(f"  ✅ Loading {filename}...")
        try:
            raw_data[key] = pd.read_csv(
                filepath, encoding='utf-8-sig', low_memory=False)
            print(f"     Rows: {len(raw_data[key]):,}")
        except Exception as e:
            print(f"  ⚠️  Error loading {filename}: {e}")
    else:
        print(f"  ⚠️  File not found: {filename}")

if not raw_data:
    print("\n❌ No data loaded. Exiting.")
    sys.exit(1)

print(f"\n✅ Loaded {len(raw_data)} datasets")

# Transform data
print("\n🔄 Transforming data...")
try:
    # Convert to format expected by transform_all: List[Tuple[dataset_key, release, df]]
    from datetime import datetime
    release = datetime.now().strftime("%Y_%m")  # e.g., "2024_11"

    extracted = [(key, release, df) for key, df in raw_data.items()]

    transformed = transform_all(extracted)
    print(f"  ✅ Metrics rows: {len(transformed.metrics):,}")
    print(f"  ✅ Star rows: {len(transformed.star):,}")
    print(f"  ✅ Catalog rows: {len(transformed.metrics_catalog):,}")
except Exception as e:
    print(f"  ❌ Transform error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Save to Parquet
print("\n💾 Saving to Parquet files...")
try:
    save_parquet(transformed.metrics, transformed.star,
                 transformed.metrics_catalog, str(warehouse_dir))
    print("  ✅ Parquet files saved")
except Exception as e:
    print(f"  ❌ Save error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Load into DuckDB
print("\n🦆 Loading into DuckDB...")
try:
    load_duckdb(transformed.metrics, transformed.star,
                transformed.metrics_catalog, str(warehouse_dir))
    print("  ✅ DuckDB database created")
except Exception as e:
    print(f"  ❌ DuckDB error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify the data
print("\n✅ VERIFICATION")
print("=" * 60)
try:
    import duckdb
    db_path = warehouse_dir / "hospital.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)

    # Check hospitals
    result = con.execute(
        "SELECT COUNT(DISTINCT ccn) as count FROM hospital_star").fetchone()
    print(f"📊 Total hospitals: {result[0]:,}")

    # Check by state
    result = con.execute(
        "SELECT state, COUNT(*) as count FROM hospital_star GROUP BY state ORDER BY count DESC LIMIT 5").fetchall()
    print(f"\n🏥 Top 5 states by hospital count:")
    for state, count in result:
        print(f"   {state}: {count:,}")

    # Check NY hospitals
    result = con.execute(
        "SELECT COUNT(*) as count FROM hospital_star WHERE state = 'NY'").fetchone()
    print(f"\n🗽 New York hospitals: {result[0]:,}")

    # Sample NY hospitals
    result = con.execute(
        "SELECT facility_name, city, star_rating FROM hospital_star WHERE state = 'NY' LIMIT 3").fetchall()
    print(f"\n📋 Sample NY hospitals:")
    for name, city, rating in result:
        print(f"   • {name} ({city}) - Rating: {rating}")

    con.close()

except Exception as e:
    print(f"❌ Verification error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🎉 SUCCESS! Hospital data loaded successfully!")
print("=" * 60)
print("\nNext steps:")
print("1. Restart your API server to pick up the new data")
print("2. Test: curl 'http://localhost:8000/api/v1/hospitals/search?city=New%20York&state=NY'")
print("3. Generate predictions: python -m provider.hospital.cli predict")
print("\nDatabase location:", warehouse_dir / "hospital.duckdb")
