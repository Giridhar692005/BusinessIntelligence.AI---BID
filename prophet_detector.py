"""
prophet_detector.py
--------------------
Forecasting-based anomaly detection, complementing the existing rolling
z-score detector in anomaly_detector.py.

Why this exists (not a replacement, an addition):
  - The z-score detector is fast, dependency-light, and good at catching
    sudden spikes/drops -- keep it as the baseline.
  - It doesn't know about day-of-week seasonality, so a normal weekend
    spike can look anomalous, and gradual drift (e.g. AOV creeping up
    over weeks) may never clearly cross a fixed z-score threshold.
  - Prophet models trend + weekly seasonality explicitly and gives a
    forecast with a confidence interval, so "anomalous" means "outside
    what we'd expect given the pattern," not just "far from the mean."
    This is also literally what the AIC brief lists under
    "Anomaly detection, contribution analysis, forecasting..."

Output columns are kept compatible with detect_anomalies_zscore()'s
result shape (date, value, is_anomaly) so this can be merged with it and
plugged into the same downstream code (root_cause.py, /plot, etc.)
without changing their interfaces.
"""

import pandas as pd

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def detect_anomalies_prophet(
    df: pd.DataFrame,
    kpi: str,
    interval_width: float = 0.90,
    weekly_seasonality: bool = True,
) -> pd.DataFrame:
    """
    Fits Prophet on the full KPI series and flags any day where the
    actual value falls outside the model's confidence interval.
    interval_width: 0.90 means a 90% confidence band (roughly comparable
    in strictness to a z-score threshold around 1.65; use 0.95-0.99 for
    something closer to the 2.5 sigma default elsewhere in the project).
    """
    if not PROPHET_AVAILABLE:
        raise ImportError(
            "prophet is not installed. Run: pip install prophet "
            "(or: conda install -c conda-forge prophet if pip struggles "
            "with the cmdstanpy backend on Windows)."
        )

    if kpi not in df.columns:
        raise ValueError(f"Column '{kpi}' not found in uploaded data")

    working = df[["date", kpi]].rename(columns={"date": "ds", kpi: "y"}).dropna()

    model = Prophet(
        interval_width=interval_width,
        weekly_seasonality=weekly_seasonality,
        yearly_seasonality=False,  # 180 days of data isn't enough to fit a real yearly cycle
        daily_seasonality=False,
    )
    model.fit(working)

    forecast = model.predict(working[["ds"]])

    result = working.merge(
        forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]],
        on="ds",
    )

    result["is_anomaly"] = (
        (result["y"] < result["yhat_lower"]) |
        (result["y"] > result["yhat_upper"])
    )

    result = result.rename(columns={
        "ds": "date",
        "y": "value",
        "yhat": "predicted",
        "yhat_lower": "lower_bound",
        "yhat_upper": "upper_bound",
    })

    return result[["date", "value", "predicted", "lower_bound", "upper_bound", "is_anomaly"]]


def detect_anomalies_ensemble(
    df: pd.DataFrame,
    kpi: str,
    zscore_fn,
    window: int = 14,
    threshold: float = 2.5,
    interval_width: float = 0.90,
) -> pd.DataFrame:
    """
    Runs both detectors and flags a day as anomalous if EITHER fires.

    zscore_fn: pass in detect_anomalies_zscore from anomaly_detector.py
    (kept as a parameter rather than importing it here, so this module
    has no hard dependency on that file's exact location/name changing).

    Returns one merged DataFrame with:
      - is_anomaly_zscore, is_anomaly_prophet: what each method decided
      - is_anomaly: the combined (OR) flag
      - detected_by: 'zscore', 'prophet', 'both', or 'none' -- useful to
        show in the demo/pitch as evidence you're using the right tool
        for spike vs. drift anomalies rather than one blunt threshold.
    """
    z_result = zscore_fn(df, kpi, window=window, threshold=threshold)
    z_result = z_result[["date", "value", "is_anomaly"]].rename(
        columns={"is_anomaly": "is_anomaly_zscore"}
    )

    if PROPHET_AVAILABLE:
        p_result = detect_anomalies_prophet(df, kpi, interval_width=interval_width)
        p_result = p_result.rename(columns={"is_anomaly": "is_anomaly_prophet"})

        merged = z_result.merge(
            p_result[["date", "predicted", "lower_bound", "upper_bound", "is_anomaly_prophet"]],
            on="date",
            how="left",
        )
        merged["is_anomaly_prophet"] = merged["is_anomaly_prophet"].fillna(False)
    else:
        # Graceful degradation: ensemble behaves like plain z-score if
        # Prophet isn't installed, rather than crashing the endpoint.
        merged = z_result.copy()
        merged["is_anomaly_prophet"] = False
        merged["predicted"] = None
        merged["lower_bound"] = None
        merged["upper_bound"] = None

    merged["is_anomaly"] = merged["is_anomaly_zscore"] | merged["is_anomaly_prophet"]

    def _label(row):
        if row["is_anomaly_zscore"] and row["is_anomaly_prophet"]:
            return "both"
        if row["is_anomaly_zscore"]:
            return "zscore"
        if row["is_anomaly_prophet"]:
            return "prophet"
        return "none"

    merged["detected_by"] = merged.apply(_label, axis=1)

    return merged
