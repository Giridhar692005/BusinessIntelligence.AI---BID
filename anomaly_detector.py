"""
anomaly_detector.py
--------------------
Core detection logic. Kept separate from the API file so your analysis
logic stays clean and testable on its own, independent of FastAPI.
"""

import pandas as pd
import numpy as np


def detect_anomalies_zscore(df: pd.DataFrame, column: str, window: int = 14, threshold: float = 2.5) -> pd.DataFrame:
    """
    Detects anomalies in a single KPI column using a rolling Z-score method.

    How it works (simple terms):
    - For each day, look at the past `window` days (NOT including today)
    - Calculate what's "normal" (average + how much it usually varies)
    - If today's value is more than `threshold` standard deviations away
      from that normal range, mark it as an anomaly.

    Params:
        df: DataFrame containing at least "date" and the target column
        column: name of the KPI column to check (e.g. "revenue")
        window: how many past days count as "recent history" (default 14)
        threshold: how many standard deviations away = anomaly (default 2.5)

    Returns:
        DataFrame with date, value, rolling_mean, rolling_std, z_score, is_anomaly
    """
    shifted = df[column].shift(1)  # exclude current day from its own baseline
    rolling_mean = shifted.rolling(window=window, min_periods=5).mean()
    rolling_std = shifted.rolling(window=window, min_periods=5).std()

    z_score = (df[column] - rolling_mean) / rolling_std
    is_anomaly = z_score.abs() > threshold

    result = pd.DataFrame({
        "date": df["date"],
        "value": df[column],
        "rolling_mean": rolling_mean,
        "rolling_std": rolling_std,
        "z_score": z_score,
        "is_anomaly": is_anomaly
    })

    # Replace NaN (from early rows with not enough history) with safe defaults.
    # NaN breaks JSON output in the API, so every numeric column must be cleaned.
    result["rolling_mean"] = result["rolling_mean"].fillna(0)
    result["rolling_std"] = result["rolling_std"].fillna(0)
    result["z_score"] = result["z_score"].fillna(0)
    result["is_anomaly"] = result["is_anomaly"].fillna(False)

    return result


def detect_anomalies_multi(df: pd.DataFrame, columns: list, window: int = 14, threshold: float = 2.5) -> dict:
    """
    Runs detect_anomalies_zscore on multiple KPI columns at once.
    Returns a dict: { "revenue": DataFrame, "conversion_rate": DataFrame, ... }
    """
    results = {}
    for col in columns:
        if col in df.columns:
            results[col] = detect_anomalies_zscore(df, col, window, threshold)
    return results
