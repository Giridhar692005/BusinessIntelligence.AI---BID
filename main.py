"""
main.py
-------
FastAPI service exposing anomaly detection as web endpoints.

Your friend's Node.js backend (or frontend directly) calls these endpoints
over HTTP to get anomaly results and plot images.

Run locally with:
    uvicorn main:app --reload --port 8000

Then open http://127.0.0.1:8000/docs to see and test all endpoints
in an interactive page (FastAPI creates this automatically).
"""
import os
import io
import base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # needed so matplotlib works without a display (server-safe)
import matplotlib.pyplot as plt

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Form

import json
from report_pdf import create_report_pdf
from anomaly_detector import detect_anomalies_zscore, detect_anomalies_multi
from root_cause import full_root_cause_report
from action_engine import generate_actions, rank_actions, merge_llm_actions, get_historical_scores

from pydantic import BaseModel
from prophet_detector import detect_anomalies_ensemble, PROPHET_AVAILABLE

from fastapi import APIRouter, UploadFile, File, HTTPException
from psycopg2.extras import execute_values
import psycopg2
from dotenv import load_dotenv
from database import get_connection
from io import BytesIO
from business_config import BUSINESS_CONFIG
from recommendation_engine_v5 import rank_actions as rank_v5_actions

app = FastAPI(title="KPI Anomaly Detection API")

load_dotenv()

router = APIRouter()
# CORS lets your frontend (running on a different port/domain) call this API.
# For the hackathon, "*" (allow all) is fine. Tighten this later for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Which columns in the uploaded CSV are treated as KPIs by default
DEFAULT_KPI_COLUMNS = BUSINESS_CONFIG.get("kpis", [])
@router.post("/upload-orders")
async def upload_orders(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    required_cols = {"order_id", "customer_id", "product_id", "unit_price",
                      "quantity", "order_date"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    if "production_cost" not in df.columns:
        df["production_cost"] = None

    # pandas uses NaN for missing values; Postgres needs actual None/NULL
    df = df.where(pd.notnull(df), None)

    records = df[[
        "order_id", "customer_id", "product_id", "unit_price",
        "production_cost", "quantity", "order_date",
    ]].values.tolist()

    query = """
        INSERT INTO "RawData"
            (order_id, customer_id, product_id, unit_price, production_cost, quantity, order_date)
        VALUES %s
        ON CONFLICT (order_id) DO UPDATE SET
            customer_id      = EXCLUDED.customer_id,
            product_id       = EXCLUDED.product_id,
            unit_price       = EXCLUDED.unit_price,
            production_cost  = EXCLUDED.production_cost,
            quantity          = EXCLUDED.quantity,
            order_date        = EXCLUDED.order_date
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, records)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")
    finally:
        conn.close()

    return {"status": "ok", "rows_upserted": len(records)}


# ============================================================
# Upload: marketing CSV -> "MarketingData"
# Expected columns: date, ad_spend, website_visits
# ============================================================
@router.post("/upload-marketing")
async def upload_marketing(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    required_cols = {"date", "ad_spend", "website_visits"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    df = df.where(pd.notnull(df), None)

    records = df[["date", "ad_spend", "website_visits"]].values.tolist()

    query = """
        INSERT INTO "MarketingData" (date, ad_spend, website_visits)
        VALUES %s
        ON CONFLICT (date) DO UPDATE SET
            ad_spend        = EXCLUDED.ad_spend,
            website_visits  = EXCLUDED.website_visits
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, records)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")
    finally:
        conn.close()

    return {"status": "ok", "rows_upserted": len(records)}


# ============================================================
# Calculate: recompute conversion_rate, net_revenue, aov for
# every day and save into "Kpis". Same query as the Node side -
# SQL logic didn't need to change, only the code that runs it.
# ============================================================
@router.post("/calculate-kpis")
async def calculate_kpis():
    query = """
        INSERT INTO "Kpis" (date, conversion_rate, revenue, aov)
        SELECT
            r.order_date,
            ROUND(COUNT(DISTINCT r.customer_id)::numeric / NULLIF(m.website_visits, 0), 4) AS conversion_rate,
            SUM(r.unit_price * r.quantity) AS net_revenue,
            ROUND(SUM(r.unit_price * r.quantity) / NULLIF(COUNT(DISTINCT r.customer_id), 0), 2) AS aov
        FROM "RawData" r
        LEFT JOIN "MarketingData" m ON r.order_date = m.date
        GROUP BY r.order_date, m.website_visits
        ON CONFLICT (date) DO UPDATE SET
            conversion_rate = EXCLUDED.conversion_rate,
            revenue     = EXCLUDED.revenue,
            aov             = EXCLUDED.aov
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            days_calculated = cur.rowcount
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"KPI calculation failed: {e}")
    finally:
        conn.close()

    return {"status": "ok", "days_calculated": days_calculated}


# ============================================================
# Read back the calculated KPIs - this is what the anomaly
# detection / plotting endpoints can query instead of requiring
# a pre-computed CSV upload from the browser.
# ============================================================
@router.get("/kpis")
async def get_kpis():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT date, revenue, conversion_rate, aov FROM "Kpis" ORDER BY date'
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row[0].isoformat(),
            "revenue": float(row[1]) if row[1] is not None else None,
            "conversion_rate": float(row[2]) if row[2] is not None else None,
            "aov": float(row[3]) if row[3] is not None else None,
        }
        for row in rows
    ]


app.include_router(router)


def _load_csv(file_bytes: bytes) -> pd.DataFrame:
    """Reads uploaded CSV bytes into a DataFrame with a proper date column."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


@app.get("/")
def health_check():
    """Simple endpoint to confirm the API is running."""
    return {"status": "ok", "message": "KPI Anomaly Detection API is running"}


@app.post("/detect")
async def detect(
    file: UploadFile = File(...),
    kpi: str = Query(..., description="Column name to check, e.g. 'revenue'"),
    window: int = Query(14, description="Rolling window size in days"),
    threshold: float = Query(2.5, description="Z-score cutoff for flagging anomalies"),
):
    """
    Upload a CSV, specify a KPI column, get back anomaly results as JSON.

    Example call from frontend (JavaScript):
        const formData = new FormData();
        formData.append("file", csvFile);
        fetch("http://your-api-url/detect?kpi=revenue&window=14&threshold=2.5", {
            method: "POST",
            body: formData
        })
    """
    contents = await file.read()
    df = _load_csv(contents)

    if kpi not in df.columns:
        return JSONResponse(status_code=400, content={"error": f"Column '{kpi}' not found in uploaded data"})

    result = detect_anomalies_zscore(df, kpi, window=window, threshold=threshold)

    # Convert to a clean JSON-friendly format
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    records = result.to_dict(orient="records")

    anomaly_count = int(result["is_anomaly"].sum())

    return {
        "kpi": kpi,
        "window": window,
        "threshold": threshold,
        "total_days": len(result),
        "anomaly_count": anomaly_count,
        "data": records
    }
@app.post("/detect-strong")
async def detect_strong(
    file: UploadFile = File(...),
    kpi: str = Query(..., description="Column name to check, e.g. 'revenue'"),
    window: int = Query(14, description="Rolling window size for the z-score detector"),
    threshold: float = Query(2.5, description="Z-score cutoff for the z-score detector"),
    interval_width: float = Query(0.90, description="Prophet confidence interval width (0-1)"),
):
    """
    Stronger anomaly detection: combines the existing rolling z-score
    detector (good at sudden spikes) with Prophet forecasting (accounts
    for weekly seasonality and gradual drift, which a fixed z-score
    threshold tends to under-catch).
 
    A day is flagged anomalous if EITHER method fires. The 'detected_by'
    field on each row shows which one(s) caught it -- useful evidence
    for the pitch that different anomaly types need different math.
 
    Falls back to z-score-only behavior if prophet isn't installed,
    rather than failing the request.
    """
    contents = await file.read()
    df = _load_csv(contents)
 
    if kpi not in df.columns:
        return JSONResponse(status_code=400, content={"error": f"Column '{kpi}' not found in uploaded data"})
 
    result = detect_anomalies_ensemble(
        df, kpi, detect_anomalies_zscore,
        window=window, threshold=threshold, interval_width=interval_width,
    )
 
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    records = result.to_dict(orient="records")
 
    return {
        "kpi": kpi,
        "prophet_available": PROPHET_AVAILABLE,
        "window": window,
        "threshold": threshold,
        "interval_width": interval_width,
        "total_days": len(result),
        "anomaly_count": int(result["is_anomaly"].sum()),
        "zscore_only_count": int((result["is_anomaly_zscore"] & ~result["is_anomaly_prophet"]).sum()),
        "prophet_only_count": int((result["is_anomaly_prophet"] & ~result["is_anomaly_zscore"]).sum()),
        "both_count": int((result["is_anomaly_zscore"] & result["is_anomaly_prophet"]).sum()),
        "data": records
    }

@app.post("/detect-all")
async def detect_all(
    file: UploadFile = File(...),
    window: int = Query(14),
    threshold: float = Query(2.5),
):
    """
    Same as /detect, but runs on all default KPI columns at once
    (revenue, conversion_rate, aov, cac) and returns them together.
    Useful for loading a full dashboard in one API call.
    """
    contents = await file.read()
    df = _load_csv(contents)

    available_kpis = [c for c in DEFAULT_KPI_COLUMNS if c in df.columns]
    results = detect_anomalies_multi(df, available_kpis, window=window, threshold=threshold)
    response = {}
    for kpi, result in results.items():
        result = result.copy()
        result = result.replace({np.nan: None})
        result["date"] = result["date"].dt.strftime("%Y-%m-%d")
        response[kpi] = {
            "anomaly_count": int(result["is_anomaly"].sum()),
            "data": result.to_dict(orient="records")
        }
    return response

from chatbot import chat as run_chat, upload_pdf_to_gemini



class ChatRequest(BaseModel):
    message: str
    history: list = []



@app.post("/chat")
async def chat_endpoint(
    req: str = Form(...),
    file: UploadFile = File(...),
    pdf: UploadFile | None = File(None),
):
    contents = await file.read()
    kpi_df = _load_csv(contents)
    kpi_df["date"] = pd.to_datetime(kpi_df["date"])

    request_data = ChatRequest.model_validate_json(req)

    if pdf is not None:
        pdf_bytes = await pdf.read()
        pdf_stream = io.BytesIO(pdf_bytes)

        return run_chat(
            request_data.message,
            request_data.history,
            kpi_df,
            REVIEWS_DF,
            pdf_file=pdf_stream,
        )

    return run_chat(
        request_data.message,
        request_data.history,
        kpi_df,
        REVIEWS_DF,
    )

@app.post("/plot")
async def plot(
    file: UploadFile = File(...),
    kpi: str = Query(..., description="Column name to plot, e.g. 'revenue'"),
    window: int = Query(14),
    threshold: float = Query(2.5),
):
    """
    Upload a CSV, get back an actual PNG image of the KPI plot with
    anomalies marked as black X's. Returns the image directly, so your
    frontend can show it with a simple <img src="..."> tag pointing at
    this endpoint (or by displaying the returned image bytes).
    """
    contents = await file.read()
    df = _load_csv(contents)

    if kpi not in df.columns:
        return JSONResponse(status_code=400, content={"error": f"Column '{kpi}' not found in uploaded data"})

    result = detect_anomalies_zscore(df, kpi, window=window, threshold=threshold)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(result["date"], result["value"], color="steelblue", linewidth=1.5, label=kpi)

    anomalies = result[result["is_anomaly"]]
    ax.scatter(anomalies["date"], anomalies["value"], color="black", s=80,
               marker="x", linewidths=2, zorder=5, label="Anomaly")

    ax.set_title(f"{kpi} — Trend with Anomalies Marked")
    ax.set_xlabel("Date")
    ax.set_ylabel(kpi)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    # Save the plot into memory (not to disk) and send it back as an image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@app.post("/plot-base64")
async def plot_base64(
    file: UploadFile = File(...),
    kpi: str = Query(...),
    window: int = Query(14),
    threshold: float = Query(2.5),
):
    """
    Same as /plot, but returns the image encoded as a base64 string inside JSON
    instead of raw image bytes. Some frontends (especially React) find this
    easier to work with than a raw image stream.
    """
    contents = await file.read()
    df = _load_csv(contents)

    if kpi not in df.columns:
        return JSONResponse(status_code=400, content={"error": f"Column '{kpi}' not found in uploaded data"})

    result = detect_anomalies_zscore(df, kpi, window=window, threshold=threshold)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(result["date"], result["value"], color="steelblue", linewidth=1.5, label=kpi)

    anomalies = result[result["is_anomaly"]]
    ax.scatter(anomalies["date"], anomalies["value"], color="black", s=80,
               marker="x", linewidths=2, zorder=5, label="Anomaly")

    ax.set_title(f"{kpi} — Trend with Anomalies Marked")
    ax.set_xlabel("Date")
    ax.set_ylabel(kpi)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)

    encoded = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "kpi": kpi,
        "anomaly_count": int(result["is_anomaly"].sum()),
        "image_base64": f"data:image/png;base64,{encoded}"
    }


from product_drivers import get_product_contribution_from_db, as_extra_drivers, get_net_profit_for_date

@app.get("/product-drivers")
async def product_drivers(
    date: str = Query(...),
    window: int = Query(14),
    top_n: int = Query(5),
):
    try:
        result = get_product_contribution_from_db(date, window=window, top_n=top_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product driver analysis failed: {e}")
    return result


@app.get("/net-profit")
async def net_profit(date: str = Query(...)):
    try:
        return get_net_profit_for_date(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Net profit calculation failed: {e}")
    
    
@app.post("/root-cause")
async def root_cause(
    file: UploadFile = File(...),
    date: str = Query(..., description="The anomaly date to explain, format YYYY-MM-DD"),
    window: int = Query(14, description="Rolling window size in days"),
    threshold: float = Query(
        2.5,
        description="Z-score cutoff used for the multi-KPI overlap check"
    ),
):
    """
    Returns:
    1. Root-cause analysis
    2. Candidate business actions
    3. Ranked recommendations
    """

    contents = await file.read()

    df = _load_csv(contents)

    if not DEFAULT_KPI_COLUMNS:
      return JSONResponse(
        status_code=400,
        content={"error": "No KPIs are configured."}
      )

    # --------------------------------------------------
    # STEP 1: Existing root-cause engine
    # --------------------------------------------------

    extra_drivers = []
    try:
       contribution = get_product_contribution_from_db(date, window=window)
       extra_drivers = as_extra_drivers(contribution)
    except Exception:
        pass  # product breakdown is optional -- never let it block the KPI-level report

    report = full_root_cause_report(
      df, date,
      kpi_columns=[...],  # whatever you already pass
      window=window,
      threshold=threshold,
      extra_drivers=extra_drivers,
    )

   # --------------------------------------------------
# STEP 2: Determine the main driver
# --------------------------------------------------

    root_cause_kpi = None

    if isinstance(report, dict):

    # Your actual root-cause report structure
       drivers = report.get("drivers")

    if isinstance(drivers, dict):

        primary_driver = drivers.get("primary_driver")

        if isinstance(primary_driver, str):
            root_cause_kpi = primary_driver


    # Fallbacks for older report formats
    if root_cause_kpi is None:

        possible_keys = [
            "root_cause",
            "main_driver",
            "driver",
            "primary_driver",
            "root_cause_kpi"
        ]

        for key in possible_keys:

            value = report.get(key)

            if isinstance(value, str):

                root_cause_kpi = value
                break

            if isinstance(value, dict):

                for subkey in [
                    "kpi",
                    "driver",
                    "name",
                    "factor"
                ]:

                    subvalue = value.get(subkey)

                    if isinstance(subvalue, str):

                        root_cause_kpi = subvalue
                        break

            if root_cause_kpi:
                break


# --------------------------------------------------
# STEP 3: Fallback
# --------------------------------------------------

    if root_cause_kpi is None:
       root_cause_kpi = "revenue"

    # --------------------------------------------------
    # STEP 4: Generate candidate actions
    # --------------------------------------------------

    ranked_actions = rank_v5_actions(
    kpi=report.get("drivers", {}).get("target_kpi"),
    context={
        "primary_driver_pct_change": report.get("drivers", {}).get("primary_driver_pct_change"),
        "confidence_score": report.get("confidence", {}).get("score")
    },
    primary_driver=root_cause_kpi
    )    [:3]

    # --------------------------------------------------
    # STEP 6: Return everything together
    # --------------------------------------------------

    return {
        "date": date,

        "root_cause": report,

        "decision_engine": {
            "primary_driver": root_cause_kpi,
            "recommendations": ranked_actions
        }
    }
# --- Add these imports near your other imports at the top of main.py ---
from llm_narrative import generate_all_narratives, generate_narrative, extract_business_factors, generate_llm_actions, PERSONAS
from text_retrieval import load_reviews, get_supporting_evidence

# Load once at startup, not per-request -- avoids re-reading the CSV on
# every call. Update the path if you place synthetic_reviews.csv elsewhere.
REVIEWS_DF = load_reviews("synthetic_reviews.csv")
@app.post("/upload-reviews")
async def upload_reviews(file: UploadFile = File(...)):
    global REVIEWS_DF

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .csv file."
        )

    contents = await file.read()

    try:
        reviews_df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse CSV: {exc}"
        )

    required_columns = {"date", "text"}
    missing_columns = required_columns - set(reviews_df.columns)

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing columns: {missing_columns}"
        )

    reviews_df["date"] = pd.to_datetime(reviews_df["date"])
    REVIEWS_DF = reviews_df

    return {
        "status": "ok",
        "rows_loaded": len(reviews_df)
    }

# --- Add this endpoint anywhere after your existing /root-cause endpoint ---

@app.post("/narrative")
async def narrative(
    file: UploadFile = File(...),
    date: str = Query(
        ...,
        description="The anomaly date to explain, format YYYY-MM-DD"
    ),
    window: int = Query(14),
    threshold: float = Query(2.5),
    persona: str = Query(
        None,
        description=(
            "Optional. One of: marketing_manager, sales_ops_manager. "
            "If omitted, returns narratives for ALL personas."
        )
    ),
    use_reviews: bool = Query(
        True,
        description=(
            "Whether to pull in customer review/ticket evidence via RAG."
        )
    ),
):
    """
    Full Business Intelligence pipeline.

    Pipeline:

        CSV
         ↓
        Root Cause Analysis
         ↓
        Customer Evidence / RAG
         ↓
        LLM Narrative
         ↓
        LLM Business-Factor Extraction
         ↓
        Structured business context

    The structured business context will later be used by
    the learning / recommendation model.
    """

    # --------------------------------------------------
    # 1. Read CSV
    # --------------------------------------------------

    contents = await file.read()

    df = _load_csv(contents)


    # --------------------------------------------------
    # 2. Validate required data
    # --------------------------------------------------

    if not DEFAULT_KPI_COLUMNS:
       return JSONResponse(status_code=400, content={"error": "No KPIs are configured."})


    # --------------------------------------------------
    # 3. Statistical root-cause analysis
    # --------------------------------------------------

    extra_drivers = []
    try:
        contribution = get_product_contribution_from_db(date, window=window)
        extra_drivers = as_extra_drivers(contribution)
    except Exception:
        pass  # product breakdown is optional -- never let it block the KPI-level report

    report = full_root_cause_report(
    df, date,
    kpi_columns=[...],  # whatever you already pass
    window=window,
    threshold=threshold,
    extra_drivers=extra_drivers,
    )
    net_profit = None
    try:
       net_profit = get_net_profit_for_date(date)
    except Exception:
       pass  # optional -- never block the KPI-level report if RawData isn't populated

    report["net_profit_snapshot"] = net_profit

    # --------------------------------------------------
    # 4. Retrieve supporting evidence
    # --------------------------------------------------

    evidence = None

    if use_reviews:

        evidence = get_supporting_evidence(
            report,
            REVIEWS_DF,
            date_window_days=3,
            top_k=5
        )


    # --------------------------------------------------
    # 5. Generate human-readable narrative
    # --------------------------------------------------

    if persona:
        if persona not in PERSONAS:
          return JSONResponse(
            status_code=400,
            content={
                "error": f"Unknown persona '{persona}'. Options: {list(PERSONAS)}"
            }
        )
        narrative_result = generate_narrative(
        report,
        persona,
        evidence=evidence
        )

        narrative_text = narrative_result.get("narrative", "")
        narratives_result = {
        persona: narrative_result
        }

    else:
        narratives_result = generate_all_narratives(
        report,
        evidence=evidence
        )

    narrative_text = ""

    for result in narratives_result.values():
        if isinstance(result, dict) and result.get("narrative"):
            narrative_text = result["narrative"]
            break    
    # Determine primary driver
    root_cause_kpi = report["drivers"]["primary_driver"]


    # --------------------------------------------------
    # 6. Extract structured business factors
    # --------------------------------------------------

    business_factors = extract_business_factors(
        report,
        evidence=evidence
    )


    # --------------------------------------------------
    # 7. Candidate actions: rule-based + LLM-augmented,
    #    ranked using real analyst feedback from Postgres
    # --------------------------------------------------
# --------------------------------------------------
# 7. LLM-generated actions + V5 ranking
# --------------------------------------------------

    root_cause_kpi = report.get("drivers", {}).get("target_kpi") or "revenue"

    llm_actions = generate_llm_actions(
      report,
      evidence=evidence,
      narrative=narrative_text
    )

    business_context = {
       "primary_driver_pct_change": report.get("drivers", {}).get("primary_driver_pct_change"),
       "confidence_score": report.get("confidence", {}).get("score")
    }

    for driver in report.get("drivers", {}).get("drivers_ranked", []):
       factor = driver.get("factor")
       change = driver.get("pct_change")
       if factor:
          business_context[f"{factor}_change"] = change

    target_kpi = report.get("drivers", {}).get("target_kpi")

    ranked_actions = rank_v5_actions(
    kpi=target_kpi,
    context=business_context,
    primary_driver=root_cause_kpi,
    llm_actions=llm_actions
   )

    ranked_actions = ranked_actions[:3]
    # --------------------------------------------------
    # 8. Return everything
    # --------------------------------------------------

    return {
    "report": report,
    "evidence": evidence,

    "narratives": narratives_result,

    "decision_engine": {
        "primary_driver": root_cause_kpi,
        "recommendations": ranked_actions
    }
}

@app.post("/report")
async def generate_report(
    file: UploadFile = File(...),
    kpi: str = Query(...),
    date: str = Query(...),
    window: int = Query(14),
    threshold: float = Query(2.5),
    use_reviews: bool = Query(True),
):
    contents = await file.read()
    df = _load_csv(contents)

    if kpi not in df.columns:
        return JSONResponse(
            status_code=400,
            content={"error": f"Column '{kpi}' not found in uploaded data"},
        )

    report = full_root_cause_report(
        df,
        date,
        kpi_columns=[c for c in DEFAULT_KPI_COLUMNS if c in df.columns],
        window=window,
        threshold=threshold,
    )

    evidence = None

    if use_reviews:
        evidence = get_supporting_evidence(
            report,
            REVIEWS_DF,
            date_window_days=3,
            top_k=5,
        )

    narratives_result = generate_all_narratives(
        report,
        evidence=evidence,
    )

    narrative_text = ""

    for result in narratives_result.values():
        if isinstance(result, dict) and result.get("narrative"):
            narrative_text = result["narrative"]
            break

    llm_actions = generate_llm_actions(
        report,
        evidence=evidence,
        narrative=narrative_text,
    )

    drivers = report.get("drivers", {})

    business_context = {
        "primary_driver_pct_change": drivers.get("primary_driver_pct_change"),
        "confidence_score": report.get("confidence", {}).get("score"),
    }

    for driver in drivers.get("drivers_ranked", []):
        factor = driver.get("factor")
        change = driver.get("pct_change")

        if factor:
            business_context[f"{factor}_change"] = change

    from recommendation_engine_v5 import rank_actions as rank_v5_actions

    recommendations = rank_v5_actions(
        kpi=kpi,
        context=business_context,
        primary_driver=drivers.get("primary_driver"),
        llm_actions=llm_actions,
    )[:3]

    # -----------------------------------------------------
    # Create graph
    # -----------------------------------------------------

    result = detect_anomalies_zscore(
        df,
        kpi,
        window=window,
        threshold=threshold,
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        result["date"],
        result["value"],
        linewidth=1.5,
        label=kpi,
    )

    anomalies = result[result["is_anomaly"]]

    ax.scatter(
        anomalies["date"],
        anomalies["value"],
        s=80,
        marker="x",
        linewidths=2,
        zorder=5,
        label="Anomaly",
    )

    ax.axvline(
        pd.to_datetime(date),
        linestyle="--",
        linewidth=1,
        label="Selected date",
    )

    ax.set_title(
        f"{kpi} - Trend with Anomalies"
    )

    ax.set_xlabel("Date")
    ax.set_ylabel(kpi)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    graph_buffer = BytesIO()
    fig.savefig(
        graph_buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)
    graph_buffer.seek(0)

    # -----------------------------------------------------
    # Create PDF
    # -----------------------------------------------------

    pdf_buffer = create_report_pdf(
        kpi=kpi,
        date=date,
        report=report,
        narratives=narratives_result,
        evidence=evidence,
        recommendations=recommendations,
        graph_buffer=graph_buffer,
    )

    filename = f"{kpi}_report_{date}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

@app.get("/actions")
async def get_actions(
    kpi: str = Query(...)
):
    """
    Return candidate business actions for a KPI.
    """

    actions = generate_actions(kpi)

    if not actions:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"No actions available for KPI '{kpi}'"
            }
        )

    return {
        "kpi": kpi,
        "actions": actions
    }
class Feedback(BaseModel):
    kpi: str
    anomaly_date: str
    root_cause: str
    action_id: str | None = None  # links back to action_engine.ACTIONS ids
    recommended_action: str

    analyst_rating: int
    action_taken: bool

    outcome: str
    outcome_value: float | None = None

    primary_driver_pct_change: float | None = None
    confidence_score: float | None = None

    visitors_change: float | None = None
    orders_change: float | None = None
    revenue_change: float | None = None
    aov_change: float | None = None
    cac_change: float | None = None
    ad_spend_change: float | None = None

@app.post("/feedback")
async def submit_feedback(feedback: Feedback):

    try:

        connection = get_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO business_decisions (
                kpi,
                anomaly_date,
                root_cause,
                action_id,
                recommended_action,
                analyst_rating,
                action_taken,
                outcome,
                outcome_value,

                primary_driver_pct_change,
                confidence_score,

                visitors_change,
                orders_change,
                revenue_change,
                aov_change,
                cac_change,
                ad_spend_change
            )

            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s
            )

            RETURNING id;
        """

        cursor.execute(
            query,
            (
                feedback.kpi,
                feedback.anomaly_date,
                feedback.root_cause,
                feedback.action_id,
                feedback.recommended_action,

                feedback.analyst_rating,
                feedback.action_taken,

                feedback.outcome,
                feedback.outcome_value,

                feedback.primary_driver_pct_change,
                feedback.confidence_score,

                feedback.visitors_change,
                feedback.orders_change,
                feedback.revenue_change,
                feedback.aov_change,
                feedback.cac_change,
                feedback.ad_spend_change
            )
        )

        decision_id = cursor.fetchone()[0]

        connection.commit()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Feedback stored successfully",
            "decision_id": decision_id
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@app.get("/feedback")
async def list_feedback(
    kpi: str = Query(None, description="Optional filter, e.g. 'revenue'"),
    limit: int = Query(50, le=500),
):
    """
    Returns stored analyst decisions -- useful for the demo (show the
    "before" list) and as the raw material for the eventual preference
    learning / bandit layer, which will train on exactly this data.
    """
    try:
        connection = get_connection()
        cursor = connection.cursor()

        if kpi:
            cursor.execute(
                """
                SELECT id, kpi, anomaly_date, action_id, recommended_action,
                       analyst_rating, action_taken, outcome, outcome_value,
                       confidence_score, created_at
                FROM business_decisions
                WHERE kpi = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (kpi.strip().lower(), limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, kpi, anomaly_date, action_id, recommended_action,
                       analyst_rating, action_taken, outcome, outcome_value,
                       confidence_score, created_at
                FROM business_decisions
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        connection.close()

        # Dates/timestamps aren't JSON-serializable by default
        for row in rows:
            if row.get("anomaly_date"):
                row["anomaly_date"] = str(row["anomaly_date"])
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()

        return {"count": len(rows), "feedback": rows}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.get("/actions/scores")
async def get_action_scores(kpi: str = Query(None)):
    """
    Exposes the learned historical_scores map directly -- handy for a demo
    slide showing "here's what the system has learned from analyst
    feedback so far" without needing to open Postgres.
    """
    return get_historical_scores(kpi)