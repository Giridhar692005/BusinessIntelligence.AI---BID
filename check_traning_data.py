import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

connection = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    database=os.environ.get("DB_NAME", "business_Ai"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD"),
    port=int(os.environ.get("DB_PORT", 5432)),
)


query = """
SELECT
    kpi,
    recommended_action,
    analyst_rating,
    outcome,
    primary_driver_pct_change,
    confidence_score,
    visitors_change,
    orders_change,
    revenue_change,
    aov_change,
    cac_change,
    ad_spend_change
FROM business_decisions
WHERE anomaly_date >= '2026-01-01'
"""


df = pd.read_sql(query, connection)

connection.close()


print("\n==============================")
print("DATASET CHECK")
print("==============================")

print("Records:", len(df))

print("\nMissing values:")
print(df.isnull().sum())

print("\nKPIs:")
print(df["kpi"].value_counts())

print("\nOutcomes:")
print(df["outcome"].value_counts())

print("\nActions:")
print(df["recommended_action"].value_counts())


print("\n==============================")
print("ACTION → OUTCOME")
print("==============================")

action_outcome = pd.crosstab(
    df["recommended_action"],
    df["outcome"],
    normalize="index"
)

print(
    action_outcome.round(3)
)


print("\n==============================")
print("AVERAGE BUSINESS CONTEXT")
print("==============================")

context_columns = [
    "primary_driver_pct_change",
    "confidence_score",
    "visitors_change",
    "orders_change",
    "revenue_change",
    "aov_change",
    "cac_change",
    "ad_spend_change",
]

print(
    df[context_columns]
    .describe()
    .round(2)
)


print("\n==============================")
print("POSITIVE RATE BY KPI")
print("==============================")

positive_rate = (
    df.assign(
        positive=df["outcome"].eq("positive")
    )
    .groupby("kpi")["positive"]
    .mean()
    .sort_values(ascending=False)
)

print(
    positive_rate.round(3)
)