# BID — Business Investigation Department

A KPI intelligence-to-action engine that transforms fragmented business data into deterministic KPI intelligence, ranked explanations, grounded evidence, persona-specific narratives, and actionable business recommendations.

This README summarises the prototype, explains how the system produces deterministic numeric truth and where language models are used, and links the implementation to the core pipeline with short, copy-pasteable code examples from the repository.

---

## Executive overview

BID answers the business question behind KPI changes. When a KPI moves (for example, "Revenue dropped 12%"), BID deterministically computes what changed, ranks contributing drivers, retrieves supporting business evidence, quantifies confidence, and produces persona-specific narratives and ownerable recommendations.

BID's core principle: LLMs are never the source of quantitative truth. All numeric claims are derived from deterministic processing (SQL, pandas, statistical tests, forecasting, contribution analysis and rule-based confidence). LLMs are used only for language synthesis, persona-aware phrasing and contextual action drafting.

---

## Pipeline: from data to decision

Data Sources
  ↓
Data Reconciliation
  ↓
KPI Semantic Layer
  ↓
Anomaly Detection
  ↓
Root Cause & Contribution Analysis
  ↓
Confidence / Abstention Logic
  ↓
Evidence Retrieval (RAG)
  ↓
Persona Context
  ↓
Narrative + Recommendations (LLM as language layer)
  ↓
Feedback & Ranking

Each stage is implemented in the codebase. Key modules:
- Data and ingestion: `main.py`, `database.py`, `custom_kpi.py`
- Detection: `anomaly_detector.py`, `prophet_detector.py`
- Root cause & confidence: `root_cause.py`
- Evidence retrieval: `text_retrieval.py`
- Narrative / LLM: `llm_narrative.py`, `prompts.py`
- Recommendations & ranking: `action_engine.py`, `recommendation_engine_v5.py`
- Reporting: `report_pdf.py`

---

## Selected implementation snippets (copy-paste)

The snippets below show how key parts of the pipeline are organised in the repository. Full files live in the repo root.

```python name=anomaly_detector.py url=https://github.com/Giridhar692005/BusinessIntelligence.AI---BID/blob/main/anomaly_detector.py
# rolling z-score detector (simplified extract)
def detect_anomalies_zscore(df: pd.DataFrame, column: str, window: int = 14, threshold: float = 2.5) -> pd.DataFrame:
    shifted = df[column].shift(1)  # exclude current day from its own baseline
    rolling_mean = shifted.rolling(window=window, min_periods=5).mean()
    rolling_std = shifted.rolling(window=window, min_periods=5).std()
    z_score = (df[column] - rolling_mean) / rolling_std
    is_anomaly = z_score.abs() > threshold
    result = pd.DataFrame({"date": df["date"], "value": df[column], "rolling_mean": rolling_mean, "rolling_std": rolling_std, "z_score": z_score, "is_anomaly": is_anomaly})
    result["rolling_mean"] = result["rolling_mean"].fillna(0)
    result["rolling_std"] = result["rolling_std"].fillna(0)
    result["z_score"] = result["z_score"].fillna(0)
    result["is_anomaly"] = result["is_anomaly"].fillna(False)
    return result
```

```python name=root_cause.py url=https://github.com/Giridhar692005/BusinessIntelligence.AI---BID/blob/main/root_cause.py
# full_root_cause_report: deterministic driver analysis and confidence
def full_root_cause_report(df: pd.DataFrame, anomaly_date: str, kpi_columns: list = None, window: int = 14, threshold: float = 2.5, extra_drivers: list = None) -> dict:
    # discovers available KPIs, selects target_kpi, computes drivers via analyze_drivers,
    # merges extra_drivers (e.g. product contribution), runs multi-kpi overlap, and computes confidence
    # returns {"anomaly_date":..., "drivers":..., "multi_kpi_overlap":..., "confidence":...}
```

```python name=llm_narrative.py url=https://github.com/Giridhar692005/BusinessIntelligence.AI---BID/blob/main/llm_narrative.py
# generate_narrative: controlled LLM synthesis for persona
def generate_narrative(report: dict, persona_key: str, api_key: str = None, evidence: dict = None) -> dict:
    # builds a system prompt from prompts.py, attaches user prompt with deterministic report and evidence,
    # calls the configured Groq model and returns {"persona":..., "narrative":..., "abstained":..., "telemetry":...}
```

```python name=main.py url=https://github.com/Giridhar692005/BusinessIntelligence.AI---BID/blob/main/main.py
# key endpoints (examples):
# POST /calculate-kpis  -> aggregate raw orders + marketing into Kpis table
# POST /detect-all      -> run anomaly detection across default KPI columns
# POST /root-cause      -> run deterministic root cause, product drivers and ranking
# POST /narrative       -> produce persona-specific narrative (LLM used for language)
# POST /report          -> render PDF from supplied analysis JSON (no LLM call during render)
```

These examples show the separation of roles: numeric analysis runs in deterministic modules; LLM is called only after the analysis to produce human-friendly narratives and candidate action wording.

---

## KPI semantic contract (in practice)

BID uses a lightweight KPI metadata contract to keep meaning consistent across the pipeline. Example fields:
- id, name, description, formula
- unit, higher_is_better
- drivers, downstream relationships
- threshold / materiality (material_pct, zscore)
- data_source (primary, additional_calculation_inputs)
- lineage and access policy (allowed_personas)

The contract is represented in the prototype as configuration in `business_config.py` and emitted by `custom_kpi.py` when a derived KPI is created.

---

## How to run the prototype (quick)

Prerequisites: Python 3.10+, optional PostgreSQL for persistence, optional GROQ_API_KEY for LLM narratives.

```bash
git clone https://github.com/Giridhar692005/BusinessIntelligence.AI---BID.git
cd BusinessIntelligence.AI---BID
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# set .env with GROQ_API_KEY and DB connection if needed
uvicorn main:app --reload --port 8000
# optionally run frontend
cd samplefrontend && npm install && npm run dev
```

Open http://127.0.0.1:8000/docs for interactive endpoints.

---

## Demo flow (recommended)

1. Upload synthetic data files present in `synthetic data/` via the UI or the `/upload-*` endpoints.
2. (Optional, requires DB) POST `/calculate-kpis` to populate the Kpis table.
3. POST `/detect-all` with Kpis.csv to identify anomalies across KPIs.
4. POST `/root-cause` for a chosen anomaly date to get deterministic driver analysis, multi-kpi overlap and confidence.
5. POST `/narrative?persona=marketing_manager` to get a persona-specific explanation (LLM used for wording; numbers come from root_cause).
6. POST `/report` with analysis JSON to render a PDF (report is a renderer only).

A demo script is included under `demo/demo_flow.sh` to exercise the above steps against a running server.

---

## Live API examples (curl)

Below are minimal, copy-pasteable curl commands that judges can run against a locally running server (http://127.0.0.1:8000). They use the sample files in `synthetic data/`.

Prerequisite: start the backend:

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

1) Upload marketing CSV

```bash
curl -s -X POST "http://127.0.0.1:8000/upload-marketing" -F "file=@'synthetic data/daily_marketing.csv'" | jq
```

2) Upload reviews (RAG corpus)

```bash
curl -s -X POST "http://127.0.0.1:8000/upload-reviews" -F "file=@'synthetic data/synthetic_reviews.csv'" | jq
```

3) Optional: calculate KPIs into Postgres (requires DB configured)

```bash
curl -s -X POST "http://127.0.0.1:8000/calculate-kpis" | jq
```

4) Detect anomalies across default KPIs using the Kpis.csv file

```bash
curl -s -X POST "http://127.0.0.1:8000/detect-all?window=14&threshold=2.5" -F "file=@'synthetic data/Kpis.csv'" | jq '.revenue | {anomaly_count, data: .data[:3]}'
```

5) Run deterministic root-cause for a chosen date (replace DATE if needed)

```bash
DATE=$(awk -F, 'NR==2{print $1}' "synthetic data/Kpis.csv")
curl -s -X POST "http://127.0.0.1:8000/root-cause?date=${DATE}&window=14&threshold=2.5" -F "file=@'synthetic data/Kpis.csv'" | jq '{date: .date, root_cause: .root_cause, decision_engine: .decision_engine}'
```

6) Generate a persona-specific narrative (marketing_manager) — requires GROQ_API_KEY set in env

```bash
curl -s -X POST "http://127.0.0.1:8000/narrative?date=${DATE}&window=14&threshold=2.5&persona=marketing_manager&use_reviews=true" -F "file=@'synthetic data/Kpis.csv'" | jq '{narratives: .narratives, telemetry: .telemetry}'
```

7) Render a PDF from previously obtained analysis JSON (example saves demo_report.pdf)

```bash
ANALYSIS_JSON='{}' # replace with actual JSON or pipeline output
curl -s -X POST "http://127.0.0.1:8000/report?kpi=revenue&date=${DATE}&window=14&threshold=2.5" -F "file=@'synthetic data/Kpis.csv'" -F "analysis_json=${ANALYSIS_JSON}" --output demo_report.pdf
```

Notes on the examples:
- Replace DATE and ANALYSIS_JSON with values obtained from earlier endpoints when needed.
- `jq` is used to pretty-print JSON responses; install it for easier reading.
- Narrative calls require an LLM API key (GROQ_API_KEY) configured in the environment.

---

## Prototype scope (intentional boundaries)

Prototype scope (purposefully bounded for a reproducible demo):
- Representative CSV data ingestion for portability
- Deterministic KPI calculations, anomaly detection, root-cause and confidence
- Evidence retrieval from a finite review corpus
- Persona-aware narrative synthesis via a hosted LLM (telemetry collected)
- Feedback storage and ranking demonstration

These boundaries are deliberate: the architecture is designed to expand toward warehouse connectors, richer entitlements and async workers for heavy forecasting.

---

## Where to inspect code (quick map)

- `main.py` — API surface and orchestration
- `anomaly_detector.py` — z-score detector, multi-kpi runner
- `prophet_detector.py` — optional Prophet ensemble
- `root_cause.py` — driver analysis and confidence logic
- `custom_kpi.py` — merging extra CSVs and computing derived KPIs
- `text_retrieval.py` — evidence loading and retrieval logic
- `llm_narrative.py` & `prompts.py` — controlled LLM prompts and generation
- `action_engine.py`, `recommendation_engine_v5.py` — action catalog and ranking
- `report_pdf.py` — PDF rendering from analysis JSON
- `database.py` — Postgres connection and helpers
- `samplefrontend/` — React workspace (app.jsx, components/*)
- `synthetic data/` — sample datasets used in demos

---

If you want more code snippets or a short tutorial that walks through the code while running the demo, tell me which module or endpoint to annotate and I will add a focused example and minimal tests.
