#!/usr/bin/env bash
# demo/demo_flow.sh
# Minimal demo script that exercises the main API endpoints against a local server.
# Assumes uvicorn main:app is running on http://127.0.0.1:8000

set -euo pipefail
API=http://127.0.0.1:8000
DATA_DIR="synthetic data"
KPI_CSV="$DATA_DIR/Kpis.csv"
MARKETING_CSV="$DATA_DIR/daily_marketing.csv"
REVIEWS_CSV="$DATA_DIR/synthetic_reviews.csv"

echo "1) Upload marketing data"
curl -s -X POST "$API/upload-marketing" -F "file=@${MARKETING_CSV}" | jq

echo "\n2) Upload reviews"
curl -s -X POST "$API/upload-reviews" -F "file=@${REVIEWS_CSV}" | jq

echo "\n3) Calculate KPIs in Postgres (requires DB configured)"
curl -s -X POST "$API/calculate-kpis" | jq

echo "\n4) Detect anomalies across default KPIs using Kpis.csv"
curl -s -X POST "$API/detect-all?window=14&threshold=2.5" -F "file=@${KPI_CSV}" | jq '.revenue | {anomaly_count, data: .data[:3]}'

echo "\n5) Run root-cause for a sample date (replace DATE as needed)"
DATE=$(head -n 2 "${KPI_CSV}" | tail -n 1 | awk -F, '{print $1}')
if [ -z "$DATE" ]; then
  DATE="2023-01-15"
fi

echo "Using date: $DATE"
ROOT_CAUSE_JSON=$(curl -s -X POST "$API/root-cause?date=${DATE}&window=14&threshold=2.5" -F "file=@${KPI_CSV}")
echo "$ROOT_CAUSE_JSON" | jq '{anomaly_date: .date, primary_driver: .decision_engine.primary_driver, recommendations: .decision_engine.recommendations}'

echo "\n6) Generate narratives (marketing_manager)"
NARRATIVE_JSON=$(curl -s -X POST "$API/narrative?date=${DATE}&window=14&threshold=2.5&persona=marketing_manager&use_reviews=true" -F "file=@${KPI_CSV}")
echo "$NARRATIVE_JSON" | jq '{narratives: .narratives, telemetry: .telemetry}'

# Save analysis_json and produce PDF (requires report endpoint and file)
echo "\n7) Render PDF from analysis result (saved as demo_report.pdf)"
ANALYSIS_JSON=$(echo "$NARRATIVE_JSON")
curl -s -X POST "$API/report?kpi=revenue&date=${DATE}&window=14&threshold=2.5" -F "file=@${KPI_CSV}" -F "analysis_json=${ANALYSIS_JSON}" --output demo_report.pdf

echo "\nDemo finished — demo_report.pdf generated (if report endpoint succeeded)."

echo "Open demo_report.pdf to review the rendered analysis (no LLM call during PDF render)."
