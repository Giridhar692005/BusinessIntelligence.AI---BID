"""
custom_kpi.py
-------------
Safe validation/calculation for user-defined KPIs.

Existing KPIs are never modified by this module. A user may add
at most three custom KPIs per uploaded dataset/session.

Formula rules:
- Variables refer to uploaded CSV column names, case-insensitively.
- Supported operators: +, -, *, /, ** and parentheses.
- Numeric constants are allowed.
- No Python functions, imports, attributes, indexing, or arbitrary code.

Example:
    (revenue - cost) / revenue * 100

If the CSV contains "COST" and the user types "cost", the existing
column is matched case-insensitively.
"""

from __future__ import annotations

import ast
import math
import re
from typing import Any

import numpy as np
import pandas as pd


MAX_CUSTOM_KPIS = 3
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]{1,39}$")


class CustomKPIError(ValueError):
    """Validation error that is safe to show directly to the user."""


_ALLOWED_BINARY_OPS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
)

_ALLOWED_UNARY_OPS = (
    ast.UAdd,
    ast.USub,
)


def _normalise_lookup(columns: list[str]) -> dict[str, str]:
    """Map case-insensitive column names to their actual CSV spelling."""
    lookup: dict[str, str] = {}

    for column in columns:
        key = str(column).strip().casefold()

        if not key:
            continue

        if key in lookup and lookup[key] != column:
            raise CustomKPIError(
                f"Ambiguous data columns: '{lookup[key]}' and '{column}' "
                "differ only by letter case."
            )

        lookup[key] = column

    return lookup

def merge_kpi_dataframes(
    main_df: pd.DataFrame,
    extra_dfs: list[pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """
    Merge the main dataset with additional daily datasets using the date column.
    """

    if "date" not in main_df.columns:
        raise CustomKPIError("The main dataset must contain a 'date' column.")

    combined = main_df.copy()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")

    combined = combined.dropna(subset=["date"]).copy()

    for index, extra_df in enumerate(extra_dfs or [], start=1):
        if "date" not in extra_df.columns:
            raise CustomKPIError(
                f"Additional dataset {index} must contain a 'date' column."
            )

        extra = extra_df.copy()
        extra["date"] = pd.to_datetime(extra["date"], errors="coerce")

        extra = extra.dropna(subset=["date"]).copy()

        duplicate_dates = extra["date"].duplicated().any()
        if duplicate_dates:
            raise CustomKPIError(
                f"Additional dataset {index} contains duplicate dates."
            )

        overlapping_columns = (
            set(combined.columns) & set(extra.columns)
        ) - {"date"}

        if overlapping_columns:
            raise CustomKPIError(
                f"Additional dataset {index} contains columns already present "
                f"in the main dataset: {', '.join(sorted(overlapping_columns))}"
            )

        combined = combined.merge(
            extra,
            on="date",
            how="left",
            validate="one_to_one",
        )

    return combined

def _extract_and_validate_expression(
    formula: str,
    columns: list[str],
) -> tuple[ast.Expression, dict[str, str]]:
    if not formula or not formula.strip():
        raise CustomKPIError("Formula is empty. Enter a formula such as (revenue - cost) / revenue * 100.")

    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise CustomKPIError(
            f"Invalid formula syntax near '{exc.text.strip() if exc.text else formula}'."
        ) from exc

    lookup = _normalise_lookup(columns)
    resolved: dict[str, str] = {}

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.Expression):
            visit(node.body)
            return

        if isinstance(node, ast.Name):
            key = node.id.strip().casefold()
            if key not in lookup:
                available = ", ".join(map(str, columns[:20]))
                suffix = " ..." if len(columns) > 20 else ""
                raise CustomKPIError(
                    f"Unknown variable '{node.id}'. No such column exists in the uploaded data. "
                    f"Available columns: {available}{suffix}"
                )
            resolved[node.id] = lookup[key]
            return

        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                raise CustomKPIError(
                    "Only numeric constants are allowed in KPI formulas."
                )
            if not math.isfinite(float(node.value)):
                raise CustomKPIError("The formula contains a non-finite numeric constant.")
            return

        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, _ALLOWED_BINARY_OPS):
                raise CustomKPIError(
                    f"Operator '{type(node.op).__name__}' is not allowed. "
                    "Use +, -, *, /, ** and parentheses."
                )
            visit(node.left)
            visit(node.right)
            return

        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _ALLOWED_UNARY_OPS):
                raise CustomKPIError("Only unary + and - are allowed.")
            visit(node.operand)
            return

        # Explicitly reject calls, attributes, subscripts, comparisons, etc.
        raise CustomKPIError(
            f"'{type(node).__name__}' is not allowed in a KPI formula. "
            "Use column names, numbers, arithmetic operators and parentheses only."
        )

    visit(tree)

    if not resolved:
        raise CustomKPIError(
            "The formula must reference at least one variable from the uploaded data."
        )

    return tree, resolved


def _evaluate_ast(node: ast.AST, env: dict[str, pd.Series]) -> pd.Series | float:
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body, env)

    if isinstance(node, ast.Name):
        return env[node.id]

    if isinstance(node, ast.Constant):
        return float(node.value)

    if isinstance(node, ast.UnaryOp):
        value = _evaluate_ast(node.operand, env)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise CustomKPIError("Unsupported unary operator.")

    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left, env)
        right = _evaluate_ast(node.right, env)

        try:
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                    return left / right
            if isinstance(node.op, ast.Pow):
                with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                    return left ** right
        except Exception as exc:
            raise CustomKPIError(
                f"The formula could not be evaluated: {exc}"
            ) from exc

    raise CustomKPIError("Unsupported formula expression.")


def validate_and_calculate_custom_kpi(
    df: pd.DataFrame,
    *,
    name: str,
    definition: str,
    unit: str,
    formula: str,
    driven_by: list[str] | None = None,
    drives: list[str] | None = None,
    higher_is_better: bool = True,
    threshold: float = 2.5,
) -> dict[str, Any]:
    """Validate metadata + formula, calculate the KPI, and return its series."""

    if "date" not in df.columns:
        raise CustomKPIError("The uploaded data must contain a 'date' column.")

    name = (name or "").strip()
    definition = (definition or "").strip()
    unit = (unit or "").strip()
    formula = (formula or "").strip()

    if not NAME_PATTERN.fullmatch(name):
        raise CustomKPIError(
            "KPI name must start with a letter and contain only letters, numbers, spaces, or underscores (2–40 characters)."
        )

    if not definition:
        raise CustomKPIError("KPI definition is required.")

    if len(definition) > 180:
        raise CustomKPIError("KPI definition is too long. Keep it under 180 characters.")

    if len(unit) > 30:
        raise CustomKPIError("Unit is too long. Keep it under 30 characters.")

    try:
        threshold = float(threshold)
    except (TypeError, ValueError) as exc:
        raise CustomKPIError("Threshold must be a number.") from exc

    if not math.isfinite(threshold) or threshold <= 0:
        raise CustomKPIError("Threshold must be a positive number.")

    existing_lookup = _normalise_lookup([str(c) for c in df.columns])
    if name.casefold() in existing_lookup:
        raise CustomKPIError(
            f"A column named '{existing_lookup[name.casefold()]}' already exists. "
            "Choose a different KPI name."
        )

    tree, resolved = _extract_and_validate_expression(
        formula,
        [str(c) for c in df.columns],
    )

    env: dict[str, pd.Series] = {}
    for formula_name, actual_column in resolved.items():
        numeric = pd.to_numeric(df[actual_column], errors="coerce")

        if numeric.notna().sum() == 0:
            raise CustomKPIError(
                f"Variable '{actual_column}' is not numeric, so it cannot be used in a calculated KPI."
            )

        env[formula_name] = numeric

    calculated = _evaluate_ast(tree, env)

    if not isinstance(calculated, pd.Series):
        calculated = pd.Series(calculated, index=df.index)

    calculated = pd.to_numeric(calculated, errors="coerce")

    missing_count = int(calculated.isna().sum())
    if missing_count:
        raise CustomKPIError(
            f"The formula produced {missing_count} missing value(s). "
            "Check whether one of the input columns contains missing values."
        )

    values = calculated.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise CustomKPIError(
            "The formula produced invalid values (infinity or NaN). "
            "Check for division by zero or another invalid calculation."
        )

    metadata = {
        "name": name,
        "definition": definition,
        "unit": unit,
        "formula": formula,
        "variables": list(resolved.values()),
        "driven_by": [str(x).strip() for x in (driven_by or []) if str(x).strip()],
        "drives": [str(x).strip() for x in (drives or []) if str(x).strip()],
        "higher_is_better": bool(higher_is_better),
        "threshold": threshold,
        "custom": True,
    }

    return {
        "metadata": metadata,
        "values": calculated.round(6),
    }
