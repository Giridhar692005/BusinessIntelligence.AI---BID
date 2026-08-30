import os
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


# =========================================================
# 1. LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# 2. CONNECT TO POSTGRESQL
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

WHERE
    recommended_action IS NOT NULL
    AND outcome IS NOT NULL
"""

df = pd.read_sql(query, connection)

connection.close()


print("\nRecords loaded:", len(df))

print("\nColumns:")
print(df.columns.tolist())


# =========================================================
# 4. CREATE TARGET
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
# =========================================================

categorical_features = [
    "kpi",
    "recommended_action"
]


numeric_features = [
    "analyst_rating",

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
# 8. TRAIN / TEST SPLIT
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
# 10. PREDICTION
# =========================================================

predictions = pipeline.predict(
    X_test
)

probabilities = pipeline.predict_proba(
    X_test
)[:, 1]


# =========================================================
# 11. EVALUATION
# =========================================================

accuracy = accuracy_score(
    y_test,
    predictions
)


print("\n")
print("=" * 50)
print("MODEL V2 RESULTS")
print("=" * 50)

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


# ROC-AUC requires both classes in test set
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
# 12. TEST A NEW BUSINESS SITUATION
# =========================================================

new_situation = pd.DataFrame([
    {
        "kpi": "revenue",

        "recommended_action":
            "Review marketing channel performance",

        "analyst_rating": 4,

        "primary_driver_pct_change": 28.88,

        "confidence_score": 0.80,

        "visitors_change": 13.62,

        "orders_change": 28.88,

        "revenue_change": 30.00,

        "aov_change": 19.92,

        "cac_change": -5.00,

        "ad_spend_change": -14.65
    }
])


new_probability = pipeline.predict_proba(
    new_situation
)[:, 1][0]


print("\n")
print("=" * 50)
print("NEW BUSINESS SITUATION")
print("=" * 50)

print(
    "KPI: revenue"
)

print(
    "Action: Review marketing channel performance"
)

print(
    "Predicted probability of positive outcome:",
    round(new_probability, 3)
)


# =========================================================
# 13. RANK ALL REVENUE ACTIONS
# =========================================================

revenue_actions = [
    "Investigate the largest contributing revenue driver",
    "Review pricing and promotional strategy",
    "Review marketing channel performance"
]


recommendation_rows = []


for action in revenue_actions:

    situation = new_situation.copy()

    situation[
        "recommended_action"
    ] = action

    probability = pipeline.predict_proba(
        situation
    )[:, 1][0]

    recommendation_rows.append(
        {
            "action": action,
            "success_probability": round(
                probability,
                3
            )
        }
    )


recommendations = pd.DataFrame(
    recommendation_rows
)


recommendations = recommendations.sort_values(
    "success_probability",
    ascending=False
)


print("\n")
print("=" * 50)
print("RANKED RECOMMENDATIONS")
print("=" * 50)

print(
    recommendations.to_string(
        index=False
    )
)