import duckdb, os

warehouse_dir = "/Users/younsoopark/Documents/Privacy/Internship/PIT-UN/signum/Signum_1/warehouse"
db_path = os.path.join(warehouse_dir, "hospital.duckdb")
ccn = "390001"  # 예: '390001'

con = duckdb.connect(db_path, read_only=True)

print("공식 별점:")
print(con.execute("""
    SELECT star_rating, release, reason
    FROM hospital_star
    WHERE ccn = ? AND star_rating IS NOT NULL
    ORDER BY release DESC
    LIMIT 5
""", [ccn]).df())

print("\nAI 예측 별점:")
print(con.execute("""
    SELECT predicted_star, confidence, release
    FROM star_predictions
    WHERE ccn = ?
    ORDER BY release DESC
    LIMIT 5
""", [ccn]).df())

print("\nEstimated 계산용 메트릭 존재 여부:")
print(con.execute("""
    SELECT COUNT(*) AS metric_count
    FROM hospital_metrics
    WHERE ccn = ? AND value IS NOT NULL
""", [ccn]).df())

con.close()