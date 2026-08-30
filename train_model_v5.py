import os
import joblib
import psycopg2
import pandas as pd

from dotenv import load_dotenv

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score
)

from sklearn.compose import ColumnTransformer

from sklearn.pipeline import Pipeline

from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler
)

from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score
)

from recommendation_config import (
    MODEL_CONFIG,
    IGNORED_COLUMNS
)


load_dotenv()



# 2. DATABASE CONNECTION

connection = psycopg2.connect(
    host=os.environ.get("DB_HOST","localhost"),
    database=os.environ.get("DB_NAME","business_Ai"),
    user=os.environ.get("DB_USER","postgres"),
    password=os.environ.get("DB_PASSWORD"),
    port=int(os.environ.get("DB_PORT",5432))
)



# 3. LOAD DATA

#
# IMPORTANT:
# We no longer hard-code KPI columns.
#
# SELECT * lets the business schema determine what is
# available.


query = """
SELECT *
FROM business_decisions
WHERE
    recommended_action IS NOT NULL
    AND outcome IS NOT NULL
"""


df = pd.read_sql(
    query,
    connection
)


connection.close()


print(
    "\nRecords loaded:",
    len(df)
)



# 4. BASIC VALIDATION


required_columns = {

    "kpi",

    "recommended_action",

    "outcome"
}


missing = (

    required_columns
    -
    set(df.columns)
)


if missing:

    raise ValueError(
        "Required columns missing from "
        f"business_decisions: {missing}"
    )



# 5. TARGET


df["target"] = (

    df["outcome"]
    .astype(str)
    .str.lower()
    .eq("positive")
    .astype(int)
)


print(
    "\nTarget distribution:"
)

print(
    df["target"].value_counts()
)



# 6. DISCOVER FEATURES AUTOMATICALLY


# These columns identify the decision itself.

categorical_candidates = [

    "kpi",

    "recommended_action"
]



# Find numeric columns automatically


numeric_candidates = [

    column

    for column in df.columns

    if (

        pd.api.types.is_numeric_dtype(
            df[column]
        )

        and

        column != "target"

        and

        column not in IGNORED_COLUMNS

    )
]



# Remove fields that belong to feedback rather than
# information available BEFORE the decision.

#
# analyst_rating is deliberately excluded.
# outcome_value is also excluded because it is known
# AFTER the action.


POST_DECISION_COLUMNS = {

    "analyst_rating",

    "outcome_value"
}


numeric_features = [

    column

    for column in numeric_candidates

    if column not in POST_DECISION_COLUMNS
]



# Only use categorical columns that actually exist


categorical_features = [

    column

    for column in categorical_candidates

    if column in df.columns
]



# Final feature list


features = (

    categorical_features

    +

    numeric_features
)


if not features:

    raise ValueError(
        "No usable training features were found."
    )


print(
    "\nAutomatically discovered features:"
)

print(
    features
)


print(
    "\nCategorical features:"
)

print(
    categorical_features
)


print(
    "\nNumeric features:"
)

print(
    numeric_features
)



# 7. TRAINING DATA


X = df[
    features
]

y = df[
    "target"
]



# 8. PREPROCESSING


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


transformers = []


if categorical_features:

    transformers.append(

        (
            "categorical",

            categorical_pipeline,

            categorical_features
        )
    )


if numeric_features:

    transformers.append(

        (
            "numeric",

            numeric_pipeline,

            numeric_features
        )
    )


preprocessor = ColumnTransformer(

    transformers=transformers
)



# 9. MODEL


model = LogisticRegression(

    max_iter=
        MODEL_CONFIG["max_iter"],

    class_weight=
        MODEL_CONFIG["class_weight"]
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



# 10. TRAIN / TEST SPLIT


X_train, X_test, y_train, y_test = (

    train_test_split(

        X,

        y,

        test_size=
            MODEL_CONFIG["test_size"],

        random_state=
            MODEL_CONFIG["random_state"],

        stratify=y
    )
)


print(
    "\nTraining records:",
    len(X_train)
)

print(
    "Testing records:",
    len(X_test)
)



# 11. TRAIN


pipeline.fit(

    X_train,

    y_train
)



# 12. TEST


predictions = pipeline.predict(

    X_test
)


probabilities = (

    pipeline.predict_proba(
        X_test
    )[:, 1]
)


accuracy = accuracy_score(

    y_test,

    predictions
)


print("\n")

print(
    "=" * 60
)

print(
    "MODEL V5 RESULTS"
)

print(
    "=" * 60
)


print(

    "Accuracy:",

    round(
        accuracy,
        3
    )
)


print(
    "\nClassification report:"
)


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


if len(
    set(y_test)
) == 2:

    auc = roc_auc_score(

        y_test,

        probabilities
    )

    print(

        "ROC-AUC:",

        round(
            auc,
            3
        )
    )



# 13. CROSS VALIDATION


print("\n")

print(
    "=" * 60
)

print(
    "5-FOLD CROSS VALIDATION"
)

print(
    "=" * 60
)


cv = StratifiedKFold(

    n_splits=
        MODEL_CONFIG["cv_folds"],

    shuffle=True,

    random_state=
        MODEL_CONFIG["random_state"]
)


cv_accuracy = cross_val_score(

    pipeline,

    X,

    y,

    cv=cv,

    scoring="accuracy"
)


cv_auc = cross_val_score(

    pipeline,

    X,

    y,

    cv=cv,

    scoring="roc_auc"
)


print(

    "Fold accuracies:",

    [
        round(
            float(score),
            3
        )

        for score in cv_accuracy
    ]
)


print(

    "Mean CV accuracy:",

    round(
        float(cv_accuracy.mean()),
        3
    )
)


print(

    "CV accuracy std:",

    round(
        float(cv_accuracy.std()),
        3
    )
)


print(

    "Fold ROC-AUC:",

    [
        round(
            float(score),
            3
        )

        for score in cv_auc
    ]
)


print(

    "Mean CV ROC-AUC:",

    round(
        float(cv_auc.mean()),
        3
    )
)



# 14. FEATURE IMPORTANCE


print("\n")

print(
    "=" * 60
)

print(
    "MODEL FEATURE IMPORTANCE"
)

print(
    "=" * 60
)


feature_names = (

    pipeline

    .named_steps[
        "preprocessor"
    ]

    .get_feature_names_out()
)


coefficients = (

    pipeline

    .named_steps[
        "model"
    ]

    .coef_[0]
)


importance_df = pd.DataFrame({

    "feature":
        feature_names,

    "coefficient":
        coefficients,

    "absolute_importance":
        abs(coefficients)
})


importance_df = (

    importance_df

    .sort_values(

        "absolute_importance",

        ascending=False
    )
)


print(

    importance_df[
        [
            "feature",

            "coefficient"
        ]
    ]

    .head(25)

    .to_string(
        index=False
    )
)



# 15. SAVE MODEL


MODEL_PATH = (
    "recommendation_model_v5.joblib"
)


model_package = {

    "pipeline":
        pipeline,

    "features":
        features,

    "categorical_features":
        categorical_features,

    "numeric_features":
        numeric_features
}


joblib.dump(

    model_package,

    MODEL_PATH
)


print("\n")

print(
    f"Model saved to: {MODEL_PATH}"
)

# 16. INFORMATION FOR INFERENCE
print("\n")

print(
    "=" * 60
)

print(
    "V5 MODEL SCHEMA"
)

print(
    "=" * 60
)

print(
    "The saved model expects these fields:"
)

for feature in features:

    print(
        f" - {feature}"
    )