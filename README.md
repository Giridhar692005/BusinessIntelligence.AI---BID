# BusinessIntelligence.AI---BID

**BID - Business Investigation Department**

A hackathon prototype KPI intelligence-to-action engine built for the BusinessIntelligence.ai Round 2 problem statement.

This README has been updated to reflect the current implementation, demo priorities, known limitations, testing steps, and how the system satisfies the contest requirements. Implementation work was intentionally incremental — the core codebase was not modified by this documentation change.

---

## Quick summary

- Purpose: Detect and prioritise material KPI movements, explain drivers with deterministic analytics, surface persona-aware narratives, and recommend actionable steps while preserving evidence and confidence.
- This repo is a working prototype (FastAPI backend + React frontend) intended for demo and hackathon evaluation. The LLM is used for narrative synthesis; all quantitative claims come from deterministic code (SQL, pandas, statistics, forecasting, rule engines, ML ranking) and retrieval.

---

## Status snapshot (what works now)

Implemented and preserved (do NOT change):
- KPI anomaly detection (Z-score and Prophet hybrid)
- Deterministic root-cause analysis and multi-driver contribution scoring
- Evidence retrieval (RAG) for customer reviews/support
- Persona-aware narrative templates (LLM used only for language)
- Recommendation catalog + ML ranking (recommendation_engine_v5.py)
- Feedback capture and historical feedback influence on ranking
- PDF renderer that uses pre-computed analysis JSON (no extra LLM calls)
- Runtime telemetry (latency, LLM calls, token estimates, cost estimate)
- Custom KPI creation and cross-source calculation foundations (partial)

Partially implemented (demo-ready improvements remaining):
- Formal KPI semantic contract (lightweight central metadata) — scaffolding present, README now documents the contract
- Explicit 3–5 connected KPI demo wiring in the UI (KPI set exists; frontend should show connections)
- Low-confidence / abstention demo scenario (logic exists; README documents how to trigger and test deterministic abstention)
- Sparse-history demo scenario (architecture supports this; README documents test steps)
- Centralised entitlement enforcement (persona config exists; backend hooks added conceptually — see notes)
- Clear LLM vs non-LLM visibility in outputs (evidence & lineage present; README shows how to surface it)
- Final custom KPI output separation (calculation dataframe vs KPI dataframe) — foundation present, further refinement needed in code

Not in scope for this patch:
- Production-grade security, auto model retraining pipelines, enterprise-scale infra.

---

## KPI semantic contract (lightweight)

Every KPI in the system should expose the following metadata fields. This file documents the contract used by the demo and serves as the single source-of-truth for metadata. The existing custom KPI structures in code should be adapted to emit/consume the same contract.

Example (JSON-like):

{
  "id": "revenue",
  "name": "Revenue",
  "description": "Daily gross revenue from sales",
  "formula": "sum(unit_price * quantity)",
  "unit": "USD",
  "higher_is_better": true,
  "drivers": ["ad_spend", "website_visits", "orders"],
  "downstream": ["aov", "cac"],
  "threshold": {
    "material_pct": 5.0,
    "zscore": 2.5
  },
  "data_source": {
    "primary": "Kpis table (Postgres)",
    "additional_calculation_inputs": ["MarketingData.csv", "orders.csv"]
  },
  "lineage": [
    {"source": "RawData.orders.csv", "derived_field": "unit_price * quantity"},
    {"source": "MarketingData", "derived_field": "website_visits"}
  ],
  "access": {
    "allowed_personas": ["marketing_manager", "sales_ops_manager"]
  }
}

Notes:
- "formula" is optional for metrics imported directly; required for custom KPIs.
- "additional_calculation_inputs" are inputs used only for calculation and should not automatically become KPI columns in the final KPI dataframe.
- The codebase currently creates custom KPI series but may still include additional source columns in the final dataframe; that separation is a targeted follow-up task.

---

## How the system separates deterministic vs LLM steps

Design principle: quantitative truth always comes from deterministic code. LLMs only perform language synthesis and persona-aware phrasing. The analysis result includes explicit evidence describing which part of the output was produced deterministically and which was created by the LLM.

Where to inspect this in the code:
- Deterministic analytics / data: anomaly_detector.py, prophet_detector.py, root_cause.py, product_drivers.py, custom_kpi.py
- Ranking & recommendations: recommendation_engine_v5.py, action_engine.py
- Evidence retrieval: text_retrieval.py, synthetic_reviews.csv
- LLM narrative / synthesis: llm_narrative.py, prompts.py
- PDF rendering of supplied analysis: report_pdf.py

Output objects include fields for:
- source (source name/type/freshness)
- method (e.g., zscore, prophet, correlation)
- contribution (driver, pct change)
- confidence (score, label, should_abstain, reason)
- lineage (which source produced which metric)
- llm_generated (boolean) and llm_prompt (for traceability)

---

## Persona & entitlement (demo)

Personas supported in the prototype:
- marketing_manager
- sales_ops_manager

Centralised entitlement concept (example):

access_control = {
  "marketing_manager": {
    "allowed_kpis": ["revenue","conversion_rate","aov","visitors","revenue_per_visitor"],
    "allowed_sources": ["MarketingData","synthetic_reviews"],
    "allowed_features": ["narrative","evidence"]
  },
  "sales_ops_manager": {
    "allowed_kpis": ["revenue","orders","cac","aov"],
    "allowed_sources": ["RawData","ProductContribution"],
    "allowed_features": ["narrative","recommendations"]
  }
}

The backend should honor check_persona_access(persona, resource_type, resource_name) for sensitive endpoints (root-cause, evidence retrieval, actions). Frontend UI can hide unavailable KPIs but should rely on backend enforcement for security.

Where to look in code: business_config.py (persona definitions), main.py (use of persona headers in endpoints).

---

## Demo scenarios and how to trigger them (deterministic tests)

1) 3–5 connected KPI demo
- Use the provided synthetic datasets and/or upload CSVs that include: revenue, conversion_rate, aov, visitors, cac, revenue_per_visitor.
- Steps:
  - Calculate KPIs: POST /calculate-kpis
  - Detect anomalies: POST /detect-all?window=14&threshold=2.5 with the KPI CSV
  - Open RootCauseWindow in the frontend for the anomaly date to see connected KPI list and drivers

2) Multi-factor KPI movement
- Trigger: pick a day where multiple drivers change in the synthetic data (ad_spend and visitors). The root_cause pipeline will list primary and secondary drivers with deterministic pct changes and correlations.
- Inspect fields response.root_cause.drivers_ranked and response.root_cause.confidence.

3) Low-confidence / abstention demo
- Deterministic triggers for abstention include: too few valid drivers, contradictory evidence, or weak correlations.
- To test: upload a KPI CSV with very few historical rows (e.g., 7 days while window=14) or conflicting driver changes (one driver up strongly, another down with similar magnitude but low correlation).
- Expected behavior: root_cause.confidence.should_abstain == true and reason explains which evidence is insufficient.

4) Sparse-history demo
- Create a new KPI (custom) with only 10 historical days and run detection with a 30-day window.
- Expected: confidence score degrades, narrative says "sparse history," forecast/prophet may be disabled or flagged, and suggestions state what extra data is needed.

5) Persona-based access demo
- In a request include persona header (e.g., X-Persona: marketing_manager). Attempt to access a KPI restricted to sales_ops_manager; backend should deny or mark fields as unavailable.
- The README documents the entitlement contract but the current prototype may still allow broad access — check logs and business_config.py for the current rule set.

---

## Evidence & lineage visibility

- All results returned by the root-cause and narrative endpoints include an evidence block listing: source name, type, date range, row counts (when available), the deterministic method used, and whether an LLM synthesized the final text. Use the UI Evidence & Lineage panel to review the elements.
- PDF report includes the evidence block from the supplied analysis JSON and does not re-run calculations.

---

## Telemetry

The system collects and returns telemetry per analysis request and totals for the session. Telemetry items include:
- total_analysis_latency_ms
- llm_calls
- llm_models_used
- llm_prompt_tokens
- llm_completion_tokens
- llm_total_tokens
- llm_estimated_cost_usd

Telemetry is an ESTIMATE for LLM-related costs. It is NOT provider billing.

---

## How to run the demo (short)

1. Backend

```bash
git clone https://github.com/Giridhar692005/BusinessIntelligence.AI---BID.git
cd BusinessIntelligence.AI---BID
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# configure .env (DB and LLM keys where required)
uvicorn main:app --reload --port 8000
```

2. Frontend (optional)

```bash
cd samplefrontend
npm install
npm run dev
# app at http://127.0.0.1:5173
```

3. Recommended demo sequence
- Upload synthetic data (or use sample CSVs) via /upload-* endpoints
- POST /calculate-kpis
- POST /detect-all to find anomalies across KPIs
- POST /root-cause for a chosen anomaly date
- POST /narrative?persona=marketing_manager to produce persona-specific narrative (LLM used only to express deterministic analysis)
- Download PDF by POST /report with analysis_json returned by root-cause

---

## What I changed in README.md (this commit)

- Added a focused "KPI semantic contract" section to formalize metadata fields (STEP 1 priority).
- Added a "Status snapshot" summarising implemented and partially implemented items mapped to problem statement expectations.
- Documented deterministic vs LLM responsibilities and where to find them in code.
- Added explicit demo scenarios and deterministic triggers for low-confidence and sparse-history cases.
- Described persona/entitlement concept and how to demo role-based access.
- Clarified telemetry fields and how they appear in analysis responses.

This is a documentation-only change and does not modify code or runtime behavior.

---

## Remaining work (recommended next tasks)

Priority (short list):
1. Emit/consume the formal KPI semantic contract centrally in code (business_config.py / custom_kpi.py).
2. Finalize separation of calculation-only input columns vs KPI dataframe output in custom_kpi.py.
3. Add one explicit demo script and synthetic dataset showing a low-confidence abstention scenario.
4. Harden backend check_persona_access() enforcement for at least one sensitive endpoint.
5. Make the UI show deterministic vs LLM-produced fields explicitly in the Evidence & Lineage panel.

---

## Assumptions made while updating this README

- No code changes were made as part of this README update.
- Existing modules and endpoints behave as described in the original README and source files.
- The persona system is configuration-driven and the persona header pattern is respected by endpoints (see business_config.py and main.py).

---

## How to test the documentation changes

- The README update is not executable, but follow the demo steps in this file to exercise the implemented features.
- Use the synthetic data included in the repo (synthetic_reviews.csv and files under "synthetic data") to run demo flows.

---

## Future extension points

- Central metadata service or table for KPI contracts and access policies
- UI improvements to visually separate deterministic facts vs LLM text
- Better custom KPI pipeline that returns only the new KPI column to the main KPI dataframe
- More granular row/column security and persona-driven filtering in the backend
- A small async worker for heavy forecasting jobs with caching and cost controls

---

## Contact / Contributing

If you want changes to how the system behaves (beyond docs), open an issue describing the exact change and reference the problem statement sections. For quick collaboration, create a branch and a small PR with code and tests.

---

