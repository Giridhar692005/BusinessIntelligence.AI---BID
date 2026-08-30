import os
import psycopg2

from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score


# --------------------------------------------------
# 1. Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# 2. Connect to PostgreSQL
# --------------------------------------------------

connection = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    database=os.environ.get("DB_NAME", "business_Ai"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD"),
    port=int(os.environ.get("DB_PORT", 5432)),
)

cursor = connection.cursor()


# --------------------------------------------------
# 3. Get training data
# --------------------------------------------------

cursor.execute("""
    SELECT
        kpi,
        recommended_action,
        analyst_rating,
        outcome
    FROM business_decisions
    ORDER BY id;
""")

rows = cursor.fetchall()

cursor.close()
connection.close()


print("Records loaded:", len(rows))


# --------------------------------------------------
# 4. Convert database rows into X and y
# --------------------------------------------------

X = []
y = []


for kpi, action, rating, outcome in rows:

    X.append({
        "kpi": kpi,
        "action": action,
        "analyst_rating": rating
    })

    if outcome == "positive":
        y.append(1)
    else:
        y.append(0)


# --------------------------------------------------
# 5. Convert to pandas DataFrame
# --------------------------------------------------

import pandas as pd

X = pd.DataFrame(X)
y = pd.Series(y)


print("\nTraining features:")
print(X.head())

print("\nTarget distribution:")
print(y.value_counts())


# --------------------------------------------------
# 6. Define categorical and numerical features
# --------------------------------------------------

categorical_features = [
    "kpi",
    "action"
]

numerical_features = [
    "analyst_rating"
]


# --------------------------------------------------
# 7. Encode categorical information
# --------------------------------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        ),
        (
            "numerical",
            "passthrough",
            numerical_features
        )
    ]
)


# --------------------------------------------------
# 8. Create small model
# --------------------------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    random_state=42
)


pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)


# --------------------------------------------------
# 9. Train/test split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)


print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# --------------------------------------------------
# 10. Train
# --------------------------------------------------

pipeline.fit(X_train, y_train)


# --------------------------------------------------
# 11. Evaluate
# --------------------------------------------------

predictions = pipeline.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n==============================")
print("MODEL RESULTS")
print("==============================")

print("Accuracy:", round(accuracy, 3))

print("\nClassification report:")
print(
    classification_report(
        y_test,
        predictions,
        target_names=["Not Positive", "Positive"]
    )
)


# --------------------------------------------------
# 12. Test the model on a new decision
# --------------------------------------------------

new_decision = pd.DataFrame([
    {
        "kpi": "revenue",
        "action": "Review marketing channel performance",
        "analyst_rating": 4
    }
])


probability = pipeline.predict_proba(
    new_decision
)[0][1]


print("\n==============================")
print("NEW RECOMMENDATION")
print("==============================")

print("KPI:", new_decision.iloc[0]["kpi"])
print("Action:", new_decision.iloc[0]["action"])
print("Analyst rating:", new_decision.iloc[0]["analyst_rating"])

print(
    "Predicted probability of positive outcome:",
    round(probability, 3)
)