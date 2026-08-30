import os
import psycopg2
from dotenv import load_dotenv

# Loads variables from a local .env file (never committed to git).
# See .env.example for the keys this expects.
load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "business_Ai"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD"),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


# ======================================================
# SCHEMA
# ======================================================
# Kept here (not a separate .sql file) so anyone cloning the repo can run
# `python database.py --init` once and have a working table -- no manual
# psql setup needed before the demo.

CREATE_BUSINESS_DECISIONS_TABLE = """
CREATE TABLE IF NOT EXISTS business_decisions (
    id SERIAL PRIMARY KEY,

    kpi VARCHAR(50) NOT NULL,
    anomaly_date DATE NOT NULL,
    root_cause TEXT,

    action_id VARCHAR(100),          -- stable id, e.g. 'orders_investigate_source'
    recommended_action TEXT NOT NULL, -- human-readable text, kept for display/back-compat

    analyst_rating INTEGER CHECK (analyst_rating BETWEEN 1 AND 5),
    action_taken BOOLEAN NOT NULL DEFAULT FALSE,

    outcome VARCHAR(20),              -- 'positive' | 'negative' | 'neutral' | 'unknown'
    outcome_value DOUBLE PRECISION,

    primary_driver_pct_change DOUBLE PRECISION,
    confidence_score DOUBLE PRECISION,

    visitors_change DOUBLE PRECISION,
    orders_change DOUBLE PRECISION,
    revenue_change DOUBLE PRECISION,
    aov_change DOUBLE PRECISION,
    cac_change DOUBLE PRECISION,
    ad_spend_change DOUBLE PRECISION,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

# Speeds up the aggregation query action_engine.get_historical_scores() runs
# on every /root-cause and /narrative call.
CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_business_decisions_action_id
    ON business_decisions (action_id);
"""


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(CREATE_BUSINESS_DECISIONS_TABLE)
    cursor.execute(CREATE_INDEX)
    connection.commit()
    cursor.close()
    connection.close()
    print("business_decisions table ready.")


if __name__ == "__main__":
    import sys

    if "--init" in sys.argv:
        create_tables()
    else:
        try:
            connection = get_connection()
            print("Connected to PostgreSQL successfully!")
            connection.close()
        except Exception as e:
            print("Database connection failed:")
            print(e)