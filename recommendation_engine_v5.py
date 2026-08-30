import joblib
import pandas as pd
import os

from action_engine import (
    ACTIONS,
    merge_llm_actions,
    get_historical_scores
)


# =========================================================
# LOAD MODEL
# =========================================================

MODEL_PATH = "recommendation_model_v5.joblib"

pipeline = None
features = []

if os.path.exists(MODEL_PATH):
    try:
        model_package = joblib.load(MODEL_PATH)
        pipeline = model_package["pipeline"]
        features = model_package["features"]
    except Exception as e:
        print(f"Warning: Could not load V5 model: {e}")


# =========================================================
# GET CANDIDATE ACTIONS
# =========================================================

def get_candidate_actions(
    target_kpi: str,
    primary_driver: str | None = None,
    llm_actions: list | None = None
):
    """
    Build the candidate action pool.

    Sources:

    1. Configured business actions
    2. Actions associated with the primary driver
    3. LLM-generated situation-specific actions

    The ML model does not generate actions.
    It only ranks them.
    """

    candidate_groups = []


    # -----------------------------------------------------
    # Target KPI
    # -----------------------------------------------------

    if target_kpi:

        candidate_groups.append(
            target_kpi
        )


    # -----------------------------------------------------
    # Primary root-cause driver
    # -----------------------------------------------------

    if primary_driver:

        if primary_driver not in candidate_groups:

            candidate_groups.append(
                primary_driver
            )


    # -----------------------------------------------------
    # Current demo configuration
    #
    # This is temporary business configuration.
    # Later this relationship comes from business metadata.
    # -----------------------------------------------------

    if target_kpi == "revenue":

        related_groups = [

            "orders",

            "conversion_rate",

            "aov",

            "cac",

            "ad_spend",

            "visitors"
        ]


        for group in related_groups:

            if group not in candidate_groups:

                candidate_groups.append(
                    group
                )


    # -----------------------------------------------------
    # Collect configured actions
    # -----------------------------------------------------

    rule_based_actions = []

    seen_ids = set()


    for group in candidate_groups:

        for action in ACTIONS.get(
            group,
            []
        ):

            action_id = action.get(
                "id",
                action.get(
                    "action"
                )
            )


            if action_id in seen_ids:

                continue


            rule_based_actions.append(
                action.copy()
            )


            seen_ids.add(
                action_id
            )


    # -----------------------------------------------------
    # Merge LLM actions
    # -----------------------------------------------------

    return merge_llm_actions(

        rule_based_actions,

        llm_actions or []
    )


# =========================================================
# RANK ACTIONS
# =========================================================

def rank_actions(
    kpi: str,
    context: dict,
    primary_driver: str | None = None,
    llm_actions: list | None = None
):
    """
    Rank candidate actions using:

        1. V5 ML probability
        2. Historical analyst/outcome score

    LLM actions are allowed to enter the candidate pool.
    """


    actions = get_candidate_actions(

        target_kpi=kpi,

        primary_driver=primary_driver,

        llm_actions=llm_actions
    )
    print("TOTAL CANDIDATE ACTIONS:", len(actions))
    print("LLM ACTIONS:", llm_actions)
    print("CANDIDATE SOURCES:", [a.get("source") for a in actions])

    if not actions:

        return []


    # =====================================================
    # CREATE MODEL ROWS
    # =====================================================

    rows = []


    for action in actions:
        row = {
        "kpi": kpi,
        "recommended_action": action.get("action"),
        "source": action.get("source", "rule_based")
       }
    row.update(context)
    rows.append(row)

    action_df = pd.DataFrame(
        rows
    )


    # =====================================================
    # ADD MISSING FEATURES
    # =====================================================

    for feature in features:

        if feature not in action_df.columns:

            action_df[
                feature
            ] = None


    # =====================================================
    # ML PROBABILITY
    # =====================================================

    if pipeline is not None:
     action_df["ml_probability"] = pipeline.predict_proba(action_df[features])[:, 1]
    else:
      action_df["ml_probability"] = 0.5 

# =========================================================
# HISTORICAL SCORE
# =========================================================

    historical_scores = get_historical_scores(kpi)
    if not historical_scores:
      print(f"No historical feedback found for KPI '{kpi}'. Using neutral historical scores.")

    action_id_lookup = {

    action.get("action"):
        action.get("id")

    for action in actions
  }


    action_df[
    "historical_score"
     ] = action_df[
    "recommended_action"
    ].map(

    lambda action_name:

        historical_scores.get(

            action_id_lookup.get(
                action_name
            ),

            0.5
        )
)

    # =====================================================
    # FINAL SCORE
    # =====================================================
    #
    # For now:
    #
    #   70% ML
    #   30% historical feedback
    #
    # Later we can learn these weights from real data.
    # =====================================================

    action_df["llm_bonus"] = action_df["source"].eq("llm").astype(float) * 0.12

    action_df["final_score"] = (
    0.62 * action_df["ml_probability"]
    + 0.26 * action_df["historical_score"]
    + action_df["llm_bonus"]
)

    # =====================================================
    # SORT
    # =====================================================

    action_df = (

        action_df

        .sort_values(

            "final_score",

            ascending=False
        )

        .reset_index(
            drop=True
        )
    )
    action_df = action_df.head(3)

    # =====================================================
    # BUILD RESULT
    # =====================================================

    results = []


    for _, row in action_df.iterrows():

        action_name = row[
            "recommended_action"
        ]


        original_action = next(

            (

                action

                for action in actions

                if action.get(
                    "action"
                ) == action_name
            ),

            {}
        )


        result = original_action.copy()


        result[
            "ml_probability"
        ] = round(

            float(
                row[
                    "ml_probability"
                ]
            ),

            3
        )


        result[
            "historical_score"
        ] = round(

            float(
                row[
                    "historical_score"
                ]
            ),

            3
        )


        result[
            "final_score"
        ] = round(

            float(
                row[
                    "final_score"
                ]
            ),

            3
        )


        results.append(
            result
        )


    return results