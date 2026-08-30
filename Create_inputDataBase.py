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
CREATE_TABLE_RAWDATA = """
CREATE TABLE IF NOT EXISTS RawData(
  order_id        VARCHAR(20) PRIMARY KEY,
  customer_id     VARCHAR(20) NOT NULL,
  product_id      VARCHAR(30) NOT NULL,
  unit_price      NUMERIC(10, 2) NOT NULL,
  quantity        INTEGER NOT NULL,
  order_date      DATE NOT NULL,
  production_cost NUMERIC(10, 2) NOT NULL
);
"""
CREATE_TABLE_MARKETINGDATA = """
CREATE TABLE IF NOT EXISTS MarketingData (
  date            DATE PRIMARY KEY,
  ad_spend        NUMERIC(10, 2),
  website_visits  INTEGER
);
"""
CREATE_TABLE_KPIDATA = """
CREATE TABLE IF NOT EXISTS Kpis (
  date              DATE PRIMARY KEY,
  conversion_rate   NUMERIC(6, 4),
  revenue           NUMERIC(12, 2),
  aov               NUMERIC(10, 2)
);
"""
# Unquoted identifier -> Postgres folds it to lowercase (rawdata), same as
# the unquoted RawData in CREATE_TABLE_RAWDATA above, so this matches.
# IF NOT EXISTS makes --init safe to re-run.
CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_rawdata_order_date ON RawData (order_date);
"""


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(CREATE_TABLE_RAWDATA)
        cursor.execute(CREATE_INDEX)
        cursor.execute(CREATE_TABLE_MARKETINGDATA)
        cursor.execute(CREATE_TABLE_KPIDATA)
        connection.commit()
        print("Input tables ready")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


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