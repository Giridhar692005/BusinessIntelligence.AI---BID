import os
import joblib
import psycopg2
import pandas as pd

from dotenv import load_dotenv

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score
)

from action_engine import ACTIONS


# =========================================================
# 1. LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# 2. DATABASE
# =========================================================

connection = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    database=os.environ.get("DB_NAME", "business_Ai"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD"),
    port=int(os.environ.get("DB_PORT", 5432)),
)


# =========================================================
# 3. LOAD TRAINING DATA
# =========================================================

query = """
SELECT
    kpi,
    recommended_action,
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

WHERE
    recommended_action IS NOT NULL
    AND outcome IS NOT NULL
"""

df = pd.read_sql(query, connection)

connection.close()


print("\nRecords loaded:", len(df))


# =========================================================
# 4. TARGET
# =========================================================

df["target"] = (
    df["outcome"]
    .str.lower()
    .eq("positive")
    .astype(int)
)


print("\nTarget distribution:")
print(df["target"].value_counts())


# =========================================================
# 5. FEATURES
#
# IMPORTANT:
# analyst_rating is intentionally NOT included.
# =========================================================

categorical_features = [
    "kpi",
    "recommended_action"
]


numeric_features = [
    "primary_driver_pct_change",
    "confidence_score",

    "visitors_change",
    "orders_change",
    "revenue_change",
    "aov_change",
    "cac_change",
    "ad_spend_change"
]


features = (
    categorical_features
    + numeric_features
)


X = df[features]

y = df["target"]


# =========================================================
# 6. PREPROCESSING
# =========================================================

categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),

        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ]
)


numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        ),

        (
            "scaler",
            StandardScaler()
        )
    ]
)


preprocessor = ColumnTransformer(
    transformers=[

        (
            "categorical",
            categorical_pipeline,
            categorical_features
        ),

        (
            "numeric",
            numeric_pipeline,
            numeric_features
        )
    ]
)


# =========================================================
# 7. MODEL
# =========================================================

model = LogisticRegression(
    max_iter=2000,
    class_weight="balanced"
)


pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor
        ),

        (
            "model",
            model
        )
    ]
)


# =========================================================
# 8. TRAIN / TEST
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)


print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# =========================================================
# 9. TRAIN
# =========================================================

pipeline.fit(
    X_train,
    y_train
)


# =========================================================
# 10. EVALUATE
# =========================================================

predictions = pipeline.predict(
    X_test
)

probabilities = pipeline.predict_proba(
    X_test
)[:, 1]


accuracy = accuracy_score(
    y_test,
    predictions
)


print("\n")
print("=" * 55)
print("MODEL V3 RESULTS")
print("=" * 55)

print(
    "Accuracy:",
    round(accuracy, 3)
)


print("\nClassification report:")

print(
    classification_report(
        y_test,
        predictions,
        target_names=[
            "Not Positive",
            "Positive"
        ]
    )
)


if len(set(y_test)) == 2:

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    print(
        "ROC-AUC:",
        round(auc, 3)
    )


# =========================================================
# 11. SAVE MODEL
# =========================================================

MODEL_PATH = "recommendation_model_v3.joblib"

joblib.dump(
    pipeline,
    MODEL_PATH
)

print(
    f"\nModel saved to: {MODEL_PATH}"
)


# =========================================================
# 12. FUNCTION TO CREATE BUSINESS CONTEXT
# =========================================================

def create_context(
    kpi,
    primary_driver_pct_change,
    confidence_score,
    visitors_change,
    orders_change,
    revenue_change,
    aov_change,
    cac_change,
    ad_spend_change
):

    return {
        "kpi": kpi,

        "primary_driver_pct_change":
            primary_driver_pct_change,

        "confidence_score":
            confidence_score,

        "visitors_change":
            visitors_change,

        "orders_change":
            orders_change,

        "revenue_change":
            revenue_change,

        "aov_change":
            aov_change,

        "cac_change":
            cac_change,

        "ad_spend_change":
            ad_spend_change
    }


# =========================================================
# 13. DYNAMIC ACTION RANKING
# =========================================================

def rank_actions_for_context(
    kpi,
    context
):

    actions = ACTIONS.get(
        kpi,
        []
    )

    if not actions:

        print(
            f"\nNo actions found for KPI: {kpi}"
        )

        return []


    rows = []


    for action in actions:

        row = {
            "kpi": kpi,

            "recommended_action":
                action["action"],

            **context
        }

        rows.append(row)


    action_df = pd.DataFrame(
        rows
    )


    action_df["success_probability"] = (
        pipeline.predict_proba(
            action_df[features]
        )[:, 1]
    )


    action_df = action_df.sort_values(
        "success_probability",
        ascending=False
    )


    return action_df[
        [
            "recommended_action",
            "success_probability"
        ]
    ]


# =========================================================
# 14. TEST WITH A NEW BUSINESS SITUATION
# =========================================================

print("\n")
print("=" * 55)
print("NEW BUSINESS SITUATION")
print("=" * 55)


new_context = create_context(

    kpi="revenue",

    primary_driver_pct_change=28.88,

    confidence_score=0.80,

    visitors_change=13.62,

    orders_change=28.88,

    revenue_change=30.00,

    aov_change=19.92,

    cac_change=-5.00,

    ad_spend_change=-14.65
)


print(
    "\nKPI:",
    new_context["kpi"]
)


# =========================================================
# 15. RANK ALL ACTIONS AUTOMATICALLY
# =========================================================

recommendations = rank_actions_for_context(
    "revenue",
    new_context
)


print("\n")
print("=" * 55)
print("DYNAMIC RECOMMENDATIONS")
print("=" * 55)


print(
    recommendations.to_string(
        index=False
    )
)