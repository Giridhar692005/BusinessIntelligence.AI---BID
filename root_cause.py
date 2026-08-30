"""
root_cause.py
-------------
Generic statistical root-cause analysis.

The analysis logic is business-agnostic.
Business-specific KPI relationships are loaded from
business_config.py when available.

No LLM is used here.
"""

import pandas as pd

from anomaly_detector import detect_anomalies_zscore

try:
    from business_config import BUSINESS_CONFIG
except ImportError:
    BUSINESS_CONFIG = {}


# =========================================================
# HELPERS
# =========================================================

def _get_kpi_relationships() -> dict:
    return BUSINESS_CONFIG.get("kpi_relationships", {})


def _get_target_factors(target_kpi: str, df: pd.DataFrame) -> list:
    relationships = _get_kpi_relationships()

    configured = relationships.get(
        target_kpi,
        []
    )

    return [
        factor
        for factor in configured
        if factor in df.columns
    ]


def _get_numeric_columns(
    df: pd.DataFrame,
    target_kpi: str
) -> list:
    excluded = {
        "date",
        target_kpi
    }

    return [
        column
        for column in df.columns
        if column not in excluded
        and pd.api.types.is_numeric_dtype(df[column])
    ]


# =========================================================
# GENERIC DRIVER ANALYSIS
# =========================================================

def analyze_drivers(
    df: pd.DataFrame,
    anomaly_date: str,
    target_kpi: str,
    factors: list = None,
    window: int = 14
) -> dict:
    """
    Finds the biggest moving factors relative to the recent
    baseline.

    If factors are configured for the target KPI, those are
    used first. Otherwise all available numeric columns are
    considered.
    """

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    target_date = pd.to_datetime(anomaly_date)

    idx = df.index[
        df["date"] == target_date
    ]

    if len(idx) == 0:
        return {
            "error": f"date {anomaly_date} not found in data"
        }

    idx = idx[0]

    start_idx = max(
        0,
        idx - window
    )

    baseline = df.iloc[
        start_idx:idx
    ]

    if factors is None:
        factors = _get_target_factors(
            target_kpi,
            df
        )

    if not factors:
        factors = _get_numeric_columns(
            df,
            target_kpi
        )

    drivers = {}

    for factor in factors:

        baseline_avg = baseline[
            factor
        ].mean()

        today_value = df.loc[
            idx,
            factor
        ]

        if (
            baseline_avg == 0
            or pd.isna(baseline_avg)
            or pd.isna(today_value)
        ):
            pct_change = 0.0
        else:
            pct_change = (
                (today_value - baseline_avg)
                / baseline_avg
            ) * 100

        drivers[factor] = {
            "today_value": round(
                float(today_value),
                4
            ),
            "baseline_avg": round(
                float(baseline_avg),
                4
            ),
            "pct_change": round(
                float(pct_change),
                2
            )
        }

    ranked = sorted(
        drivers.items(),
        key=lambda x: abs(
            x[1]["pct_change"]
        ),
        reverse=True
    )

    return {
        "anomaly_date": anomaly_date,
        "target_kpi": target_kpi,
        "drivers_ranked": [
            {
                "factor": factor,
                **values
            }
            for factor, values in ranked
        ],
        "primary_driver": (
            ranked[0][0]
            if ranked
            else None
        ),
        "primary_driver_pct_change": (
            ranked[0][1]["pct_change"]
            if ranked
            else None
        )
    }


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def analyze_revenue_drivers(
    df: pd.DataFrame,
    anomaly_date: str,
    window: int = 14
) -> dict:
    """
    Keeps the existing function name used by the rest
    of the application.

    Your current revenue example therefore continues to
    work without changing its input.
    """

    return analyze_drivers(
        df=df,
        anomaly_date=anomaly_date,
        target_kpi="revenue",
        factors=_get_target_factors(
            "revenue",
            df
        ),
        window=window
    )


# =========================================================
# MULTI-KPI OVERLAP
# =========================================================

def check_multi_kpi_overlap(
    df: pd.DataFrame,
    anomaly_date: str,
    kpi_columns: list,
    window: int = 14,
    threshold: float = 2.5
) -> dict:
    """
    Checks which supplied KPIs were anomalous on the same
    date.

    The list of KPIs comes from the caller, so this function
    itself does not assume an industry.
    """

    target_date = pd.to_datetime(
        anomaly_date
    )

    affected = []

    for kpi in kpi_columns:

        if kpi not in df.columns:
            continue

        result = detect_anomalies_zscore(
            df,
            kpi,
            window=window,
            threshold=threshold
        )

        result["date"] = pd.to_datetime(
            result["date"]
        )

        row = result[
            result["date"] == target_date
        ]

        if (
            len(row) > 0
            and bool(
                row.iloc[0]["is_anomaly"]
            )
        ):

            affected.append({
                "kpi": kpi,
                "z_score": round(
                    float(
                        row.iloc[0]["z_score"]
                    ),
                    2
                )
            })

    return {
        "anomaly_date": anomaly_date,
        "affected_kpis": affected,
        "is_multi_factor": len(
            affected
        ) > 1
    }


# =========================================================
# CONFIDENCE
# =========================================================

def compute_confidence(
    drivers_result: dict,
    multi_kpi_result: dict,
    min_history_days: int = 14,
    available_history_days: int = None
) -> dict:
    """
    Deterministic confidence calculation.
    """

    if (
        available_history_days is not None
        and available_history_days < min_history_days
    ):
        return {
            "confidence": "low",
            "score": 0.3,
            "should_abstain": True,
            "reason": (
                f"Only {available_history_days} days "
                f"of history available "
                f"(need {min_history_days}+). "
                f"Not enough data to reliably establish "
                f"what normal looks like for this KPI yet."
            )
        }

    ranked = drivers_result.get(
        "drivers_ranked",
        []
    )

    if len(ranked) < 2:
        return {
            "confidence": "low",
            "score": 0.4,
            "should_abstain": True,
            "reason": (
                "Not enough driver data available "
                "to compare factors."
            )
        }

    top_change = abs(
        ranked[0]["pct_change"]
    )

    second_change = abs(
        ranked[1]["pct_change"]
    )

    if (
        top_change > second_change * 2
        and top_change > 15
    ):
        return {
            "confidence": "high",
            "score": 0.85,
            "should_abstain": False,
            "reason": (
                f"'{ranked[0]['factor']}' moved "
                f"{top_change}%, clearly larger "
                f"than any other factor — strong "
                f"single driver identified."
            )
        }

    elif top_change > 15:
        return {
            "confidence": "medium",
            "score": 0.6,
            "should_abstain": False,
            "reason": (
                f"Multiple factors moved together "
                f"(top two: {top_change}% and "
                f"{second_change}%). Likely a combined "
                f"effect rather than one single cause."
            )
        }

    return {
        "confidence": "low",
        "score": 0.35,
        "should_abstain": True,
        "reason": (
            "No single factor shows a large enough "
            "change to confidently explain this anomaly. "
            "Recommend manual review."
        )
    }


# =========================================================
# FULL ROOT-CAUSE REPORT
# =========================================================

def full_root_cause_report(
    df: pd.DataFrame,
    anomaly_date: str,
    kpi_columns: list = None,
    window: int = 14,
    threshold: float = 2.5
) -> dict:
    """
    Existing public function preserved.

    The caller can continue using exactly the same arguments.

    Business-specific KPI relationships are obtained from
    business_config.py when configured.
    """

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"]
    )

    # -----------------------------------------------------
    # Determine available KPIs
    # -----------------------------------------------------

    if kpi_columns is None:

        configured_kpis = (
            BUSINESS_CONFIG.get(
                "kpis",
                []
            )
        )

        kpi_columns = [

            kpi

            for kpi in configured_kpis

            if kpi in df.columns
        ]


    # -----------------------------------------------------
    # Determine target KPI
    #
    # Preserve current demo behavior:
    # revenue is used when present.
    #
    # For a general business, if revenue does not exist,
    # use the first supplied KPI.
    # -----------------------------------------------------

    if "revenue" in df.columns:

        target_kpi = "revenue"

    elif kpi_columns:

        target_kpi = kpi_columns[0]

    else:

        numeric_columns = _get_numeric_columns(
            df,
            ""
        )

        target_kpi = (
            numeric_columns[0]
            if numeric_columns
            else None
        )


    if target_kpi is None:

        return {
            "error": (
                "No numeric KPI was found in the "
                "uploaded data."
            )
        }


    # -----------------------------------------------------
    # Available history
    # -----------------------------------------------------

    available_history_days = len(
        df[
            df["date"]
            < pd.to_datetime(anomaly_date)
        ]
    )


    # -----------------------------------------------------
    # Drivers
    # -----------------------------------------------------

    drivers_result = analyze_drivers(
        df=df,
        anomaly_date=anomaly_date,
        target_kpi=target_kpi,
        factors=_get_target_factors(
            target_kpi,
            df
        ),
        window=window
    )


    # -----------------------------------------------------
    # Multi-KPI check
    # -----------------------------------------------------

    multi_kpi_result = check_multi_kpi_overlap(
        df=df,
        anomaly_date=anomaly_date,
        kpi_columns=kpi_columns,
        window=window,
        threshold=threshold
    )


    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    confidence_result = compute_confidence(

        drivers_result,

        multi_kpi_result,

        min_history_days=window,

        available_history_days=
            available_history_days
    )


    # -----------------------------------------------------
    # Final report
    # -----------------------------------------------------

    return {
        "anomaly_date": anomaly_date,
        "drivers": drivers_result,
        "multi_kpi_overlap": multi_kpi_result,
        "confidence": confidence_result
    }