"""
Product-level contribution analysis.

Explains a revenue movement by ranking which *products* drove it, using
the same "compare to a trailing baseline" logic root_cause.py already
uses for KPI factors -- just applied per product_id instead of per KPI.

Reads straight from the "RawData" table (already populated by
/upload-orders), so this works without a separate file upload once
orders have been uploaded once.
"""

import pandas as pd
from database import get_connection


MAX_PRODUCTS_RETURNED = 6  # hard ceiling -- caller can ask for fewer, never more


def _fetch_orders_window(end_date: pd.Timestamp, window: int) -> pd.DataFrame:
    """
    Pull *pre-aggregated* daily revenue/units per product between
    (end_date - window) and end_date, inclusive. Aggregating in SQL
    (GROUP BY order_date, product_id) instead of pulling every raw order
    line keeps the result to (days x products) rows rather than one row
    per order -- much lighter on the DB for a wide window or big catalog.
    """
    start_date = end_date - pd.Timedelta(days=window)

    query = """
        SELECT order_date,
               product_id,
               SUM(unit_price * quantity) AS revenue,
               SUM(quantity) AS quantity
        FROM "RawData"
        WHERE order_date BETWEEN %s AND %s
        GROUP BY order_date, product_id
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (start_date.date(), end_date.date()))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    df["order_date"] = pd.to_datetime(df["order_date"])
    # Already aggregated to one row per (date, product), so this "revenue"
    # here is really unit_price -- kept as unit_price*quantity so it can
    # feed straight into analyze_product_contribution() unchanged, which
    # expects a per-line-style (unit_price, quantity) shape.
    df = df.rename(columns={"revenue": "unit_price"})
    df["unit_price"] = df["unit_price"] / df["quantity"].replace(0, pd.NA)
    return df


def analyze_product_contribution(orders_df: pd.DataFrame, date: str, window: int = 14, top_n: int = None) -> dict:
    """
    Rank products by how much they contributed to the revenue change on `date`,
    relative to each product's own trailing `window`-day baseline.

    orders_df needs columns: order_date, product_id, unit_price, quantity
    (exactly what RawData / the raw orders CSV already has). Kept as a
    plain dataframe-in function so it's testable without a DB connection.
    """
    df = orders_df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["revenue"] = df["unit_price"].astype(float) * df["quantity"].astype(float)

    target_date = pd.to_datetime(date)
    start_date = target_date - pd.Timedelta(days=window)
    df = df[(df["order_date"] >= start_date) & (df["order_date"] <= target_date)]

    if df.empty:
        return {"target_date": date, "window": window, "products": [],
                "warning": "No orders found in this date range."}

    daily = (
        df.groupby(["order_date", "product_id"])
        .agg(revenue=("revenue", "sum"), units=("quantity", "sum"))
        .reset_index()
    )
    daily["avg_price"] = daily["revenue"] / daily["units"].replace(0, pd.NA)

    baseline_mask = daily["order_date"] < target_date
    today_mask = daily["order_date"] == target_date

    baseline = (
        daily[baseline_mask]
        .groupby("product_id")
        .agg(revenue_baseline=("revenue", "mean"),
             units_baseline=("units", "mean"),
             avg_price_baseline=("avg_price", "mean"),
             data_points=("revenue", "count"))
    )
    today = (
        daily[today_mask]
        .set_index("product_id")[["revenue", "units", "avg_price"]]
        .rename(columns={"revenue": "revenue_today", "units": "units_today", "avg_price": "avg_price_today"})
    )

    merged = baseline.join(today, how="outer").fillna(0)

    products = []
    for product_id, row in merged.iterrows():
        revenue_today = float(row.get("revenue_today", 0))
        revenue_baseline = float(row.get("revenue_baseline", 0))
        delta = revenue_today - revenue_baseline
        pct_change = round((delta / revenue_baseline) * 100, 2) if revenue_baseline else None

        units_today = float(row.get("units_today", 0))
        units_baseline = float(row.get("units_baseline", 0))
        price_today = float(row.get("avg_price_today", 0))
        price_baseline = float(row.get("avg_price_baseline", 0))

        # Two-factor price/volume decomposition of this product's own delta.
        # volume_effect: how much revenue moved because units sold changed
        # price_effect: how much revenue moved because the price changed
        volume_effect = (units_today - units_baseline) * price_baseline
        price_effect = (price_today - price_baseline) * units_today

        products.append({
            "product_id": product_id,
            "revenue_today": round(revenue_today, 2),
            "revenue_baseline": round(revenue_baseline, 2),
            "delta": round(delta, 2),
            "pct_change": pct_change,
            "volume_effect": round(volume_effect, 2),
            "price_effect": round(price_effect, 2),
            "data_points": int(row.get("data_points", 0)),
        })

    total_delta = sum(p["delta"] for p in products)
    safe_total = total_delta if total_delta != 0 else 1e-9
    for p in products:
        p["contribution_pct"] = round((p["delta"] / safe_total) * 100, 1)

    products.sort(key=lambda p: abs(p["delta"]), reverse=True)
    # Products with under 5 days of baseline history -- new/sparse products,
    # flag them rather than let the ranking imply false confidence.
    low_confidence = [p["product_id"] for p in products if p["data_points"] < 5]

    top_n = min(top_n, MAX_PRODUCTS_RETURNED) if top_n else 5
    products = products[:top_n]

    total_today = merged["revenue_today"].sum() if "revenue_today" in merged else 0
    total_baseline = merged["revenue_baseline"].sum() if "revenue_baseline" in merged else 0

    return {
        "target_date": date,
        "window": window,
        "total_revenue_today": round(float(total_today), 2),
        "total_revenue_baseline": round(float(total_baseline), 2),
        "total_delta": round(float(total_today - total_baseline), 2),
        "primary_product_driver": products[0]["product_id"] if products else None,
        "primary_product_contribution_pct": products[0]["contribution_pct"] if products else None,
        "products": products,
        "low_confidence_products": low_confidence,
    }


def get_product_contribution_from_db(date: str, window: int = 14, top_n: int = 5) -> dict:
    """DB-backed wrapper -- reads RawData (pre-aggregated), then reuses the pure function above."""
    top_n = min(top_n, MAX_PRODUCTS_RETURNED) if top_n else 5
    target_date = pd.to_datetime(date)
    orders_df = _fetch_orders_window(target_date, window)
    if orders_df.empty:
        return {"target_date": date, "window": window, "products": [],
                "warning": "No orders in RawData for this date range. Has /upload-orders been run?"}
    return analyze_product_contribution(orders_df, date, window=window, top_n=top_n)

def as_extra_drivers(contribution_result: dict) -> list:
    """
    Reshape analyze_product_contribution()'s output into the same
    {"factor", "today_value", "baseline_avg", "pct_change", ...} shape
    root_cause.py's drivers use, so it can be passed straight into
    full_root_cause_report(extra_drivers=...).
    """
    return [
        {
            "factor": p["product_id"],
            "today_value": p["revenue_today"],
            "baseline_avg": p["revenue_baseline"],
            "pct_change": p["pct_change"] if p["pct_change"] is not None else 0.0,
            "driver_type": "product",
            "contribution_pct": p["contribution_pct"],
            "volume_effect": p["volume_effect"],
            "price_effect": p["price_effect"],
        }
        for p in contribution_result.get("products", [])
    ]
def get_net_profit_for_date(date: str) -> dict:
    """
    On-demand net profit/loss for a single day, computed straight from
    RawData: (unit_price - production_cost) * quantity, summed.

    Deliberately NOT a tracked KPI in Kpis / business_config -- this is
    a point-in-time snapshot computed only when asked for, not part of
    the anomaly-detection pipeline.
    """
    target_date = pd.to_datetime(date).date()

    query = """
        SELECT
            SUM(unit_price * quantity) AS revenue,
            SUM(COALESCE(production_cost, 0) * quantity) AS cost,
            COUNT(*) FILTER (WHERE production_cost IS NULL) AS missing_cost_lines,
            COUNT(*) AS total_lines
        FROM "RawData"
        WHERE order_date = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (target_date,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None or row[0] is None:
        return {
            "date": date,
            "revenue": 0.0,
            "cost": 0.0,
            "net_profit": 0.0,
            "is_profit": None,
            "warning": "No orders found for this date.",
        }

    revenue, cost, missing_cost_lines, total_lines = row
    revenue = float(revenue or 0)
    cost = float(cost or 0)
    net_profit = round(revenue - cost, 2)

    result = {
        "date": date,
        "revenue": round(revenue, 2),
        "cost": round(cost, 2),
        "net_profit": net_profit,
        "is_profit": net_profit >= 0,
    }

    if missing_cost_lines:
        result["warning"] = (
            f"{missing_cost_lines} of {total_lines} order lines had no "
            f"production_cost on file -- cost (and net_profit) is understated."
        )

    return result