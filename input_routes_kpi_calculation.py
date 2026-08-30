import os
import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from psycopg2.extras import execute_values
import psycopg2
from dotenv import load_dotenv

load_dotenv()

get_connection=psycopg2.connect(
    host=os.environ.get("DB_HOST","localhost"),
    database=os.environ.get("DB_NAME","business_Ai"),
    user=os.environ.get("DB_USER","postgres"),
    password=os.environ.get("DB_PASSWORD"),
    port=int(os.environ.get("DB_PORT",5432))
)


router = APIRouter()


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
        INSERT INTO "Kpis" (date, conversion_rate, net_revenue, aov)
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
            net_revenue     = EXCLUDED.net_revenue,
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
                'SELECT date, net_revenue, conversion_rate, aov FROM "Kpis" ORDER BY date'
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
