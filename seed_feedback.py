"""
seed_feedback.py

Generates clean synthetic analyst feedback for the
business recommendation model.

7 KPIs
3 actions per KPI
100 records per action

= 2100 records

IMPORTANT:
This script deletes the previous synthetic records
before generating the new dataset.
"""

import random
from datetime import date, timedelta

from database import get_connection, create_tables
from action_engine import ACTIONS


# =========================================================
# CONFIGURATION
# =========================================================

random.seed(42)

N_PER_ACTION = 100


# =========================================================
# STRONGEST ACTION FOR EACH KPI
# =========================================================

GOOD_ACTIONS = {

    "orders": {
        "orders_check_fulfillment"
    },

    "visitors": {
        "visitors_evaluate_quality"
    },

    "conversion_rate": {
        "conversion_investigate_funnel"
    },

    "aov": {
        "aov_upsell_crosssell"
    },

    "cac": {
        "cac_reallocate_spend"
    },

    "ad_spend": {
        "adspend_reallocate_budget"
    },

    "revenue": {
        "revenue_investigate_driver"
    }
}


# =========================================================
# BUSINESS CONTEXT
# =========================================================

def generate_business_context(kpi):

    context = {

        "visitors_change":
            random.uniform(-20, 20),

        "orders_change":
            random.uniform(-20, 20),

        "revenue_change":
            random.uniform(-20, 20),

        "aov_change":
            random.uniform(-15, 15),

        "cac_change":
            random.uniform(-15, 15),

        "ad_spend_change":
            random.uniform(-15, 15),
    }


    # -----------------------------------------------------
    # Main anomaly
    # -----------------------------------------------------

    anomaly_change = random.uniform(15, 45)


    if random.choice([True, False]):

        anomaly_change *= -1


    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    if kpi == "orders":

        context["orders_change"] = anomaly_change

        context["revenue_change"] = (
            anomaly_change *
            random.uniform(0.7, 1.0)
            +
            random.uniform(-5, 5)
        )

        context["visitors_change"] = (
            anomaly_change *
            random.uniform(0.3, 0.7)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # VISITORS
    # -----------------------------------------------------

    elif kpi == "visitors":

        context["visitors_change"] = anomaly_change

        context["orders_change"] = (
            anomaly_change *
            random.uniform(0.3, 0.7)
            +
            random.uniform(-5, 5)
        )

        context["revenue_change"] = (
            context["orders_change"] *
            random.uniform(0.6, 1.0)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # CONVERSION RATE
    # -----------------------------------------------------

    elif kpi == "conversion_rate":

        context["orders_change"] = (
            anomaly_change *
            random.uniform(0.4, 0.8)
            +
            random.uniform(-5, 5)
        )

        context["revenue_change"] = (
            context["orders_change"] *
            random.uniform(0.7, 1.0)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # AOV
    # -----------------------------------------------------

    elif kpi == "aov":

        context["aov_change"] = anomaly_change

        context["revenue_change"] = (
            anomaly_change *
            random.uniform(0.5, 0.9)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # CAC
    # -----------------------------------------------------

    elif kpi == "cac":

        context["cac_change"] = anomaly_change

        context["ad_spend_change"] = (
            anomaly_change *
            random.uniform(0.4, 0.8)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # AD SPEND
    # -----------------------------------------------------

    elif kpi == "ad_spend":

        context["ad_spend_change"] = anomaly_change

        context["visitors_change"] = (
            anomaly_change *
            random.uniform(0.3, 0.7)
            +
            random.uniform(-5, 5)
        )

        context["orders_change"] = (
            context["visitors_change"] *
            random.uniform(0.3, 0.7)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # REVENUE
    # -----------------------------------------------------

    elif kpi == "revenue":

        context["revenue_change"] = anomaly_change

        context["orders_change"] = (
            anomaly_change *
            random.uniform(0.5, 0.9)
            +
            random.uniform(-5, 5)
        )

        context["aov_change"] = (
            anomaly_change *
            random.uniform(0.2, 0.6)
            +
            random.uniform(-5, 5)
        )

        context["visitors_change"] = (
            anomaly_change *
            random.uniform(0.2, 0.6)
            +
            random.uniform(-5, 5)
        )


    # -----------------------------------------------------
    # Round values
    # -----------------------------------------------------

    for key in context:

        context[key] = round(
            context[key],
            2
        )


    return context


# =========================================================
# CONTEXT SCORE
# =========================================================

def calculate_context_score(
    kpi,
    context
):

    target_change = {

        "orders":
            context["orders_change"],

        "visitors":
            context["visitors_change"],

        "conversion_rate":
            context["orders_change"],

        "aov":
            context["aov_change"],

        "cac":
            -context["cac_change"],

        "ad_spend":
            -context["ad_spend_change"],

        "revenue":
            context["revenue_change"],
    }[kpi]


    score = max(
        -1,
        min(
            1,
            target_change / 45
        )
    )


    return score


# =========================================================
# GENERATE ONE TRAINING ROW
# =========================================================

def synth_row(
    kpi,
    action,
    is_good,
    day_offset
):

    anomaly_date = (
        date(2026, 1, 1)
        +
        timedelta(days=day_offset)
    )


    context = generate_business_context(
        kpi
    )


    context_score = calculate_context_score(
        kpi,
        context
    )


    confidence_score = round(
        random.uniform(
            0.60,
            0.95
        ),
        2
    )


    primary_driver_pct_change = {

        "orders":
            context["orders_change"],

        "visitors":
            context["visitors_change"],

        "conversion_rate":
            context["orders_change"],

        "aov":
            context["aov_change"],

        "cac":
            context["cac_change"],

        "ad_spend":
            context["ad_spend_change"],

        "revenue":
            context["revenue_change"],
    }[kpi]


    # =====================================================
    # ACTION QUALITY
    # =====================================================

    if is_good:

        base_success_probability = 0.72

    else:

        base_success_probability = 0.38


    # =====================================================
    # BUSINESS CONTEXT INFLUENCE
    #
    # Increased from 0.10 to 0.20
    # =====================================================

    probability = (

        base_success_probability

        +

        context_score * 0.20

        +

        (confidence_score - 0.75)
        * 0.15
    )


    probability = max(
        0.05,
        min(
            0.95,
            probability
        )
    )


    # =====================================================
    # OUTCOME
    # =====================================================

    random_value = random.random()


    if random_value < probability:

        outcome = "positive"

    elif random_value < probability + 0.20:

        outcome = "neutral"

    else:

        outcome = "negative"


    # =====================================================
    # ANALYST RATING
    # =====================================================

    if outcome == "positive":

        rating = random.choice(
            [4, 4, 5, 5]
        )

    elif outcome == "neutral":

        rating = random.choice(
            [3, 3, 4]
        )

    else:

        rating = random.choice(
            [2, 2, 3]
        )


    # Add a little noise

    if random.random() < 0.10:

        rating = random.randint(
            2,
            5
        )


    # =====================================================
    # OUTCOME VALUE
    # =====================================================

    if outcome == "positive":

        outcome_value = random.uniform(
            500,
            8000
        )

    elif outcome == "neutral":

        outcome_value = random.uniform(
            -1500,
            1500
        )

    else:

        outcome_value = random.uniform(
            -8000,
            -500
        )


    # =====================================================
    # RETURN RECORD
    # =====================================================

    return {

        "kpi":
            kpi,

        "anomaly_date":
            anomaly_date,

        "root_cause":
            f"{kpi} anomaly driven primarily by this factor (synthetic)",

        "action_id":
            action["id"],

        "recommended_action":
            action["action"],

        "analyst_rating":
            rating,

        "action_taken":
            True,

        "outcome":
            outcome,

        "outcome_value":
            round(
                outcome_value,
                2
            ),

        "primary_driver_pct_change":
            round(
                primary_driver_pct_change,
                2
            ),

        "confidence_score":
            confidence_score,

        "visitors_change":
            context["visitors_change"],

        "orders_change":
            context["orders_change"],

        "revenue_change":
            context["revenue_change"],

        "aov_change":
            context["aov_change"],

        "cac_change":
            context["cac_change"],

        "ad_spend_change":
            context["ad_spend_change"],
    }


# =========================================================
# SEED DATABASE
# =========================================================

def seed():

    create_tables()


    connection = get_connection()

    cursor = connection.cursor()


    # =====================================================
    # DELETE OLD SYNTHETIC DATA
    #
    # Our synthetic records use dates starting from
    # 2026-01-01.
    #
    # We delete only those records.
    # =====================================================

    print(
        "\nRemoving old synthetic training data..."
    )


    cursor.execute(
        """
        DELETE FROM business_decisions
        WHERE anomaly_date >= '2026-01-01'
        """
    )


    deleted = cursor.rowcount


    print(
        f"Deleted {deleted} old synthetic records."
    )


    # =====================================================
    # INSERT QUERY
    # =====================================================

    insert_query = """

        INSERT INTO business_decisions (

            kpi,
            anomaly_date,
            root_cause,
            action_id,
            recommended_action,
            analyst_rating,
            action_taken,
            outcome,
            outcome_value,

            primary_driver_pct_change,
            confidence_score,

            visitors_change,
            orders_change,
            revenue_change,
            aov_change,
            cac_change,
            ad_spend_change

        )

        VALUES (

            %(kpi)s,
            %(anomaly_date)s,
            %(root_cause)s,
            %(action_id)s,
            %(recommended_action)s,
            %(analyst_rating)s,
            %(action_taken)s,
            %(outcome)s,
            %(outcome_value)s,

            %(primary_driver_pct_change)s,
            %(confidence_score)s,

            %(visitors_change)s,
            %(orders_change)s,
            %(revenue_change)s,
            %(aov_change)s,
            %(cac_change)s,
            %(ad_spend_change)s

        )

    """


    rows_inserted = 0

    day_offset = 0


    # =====================================================
    # GENERATE DATA
    # =====================================================

    for kpi, actions in ACTIONS.items():

        good_ids = GOOD_ACTIONS.get(
            kpi,
            set()
        )


        for action in actions:

            is_good = (
                action["id"]
                in good_ids
            )


            for _ in range(
                N_PER_ACTION
            ):

                row = synth_row(

                    kpi,

                    action,

                    is_good,

                    day_offset
                )


                cursor.execute(
                    insert_query,
                    row
                )


                rows_inserted += 1

                day_offset += 1


    # =====================================================
    # COMMIT
    # =====================================================

    connection.commit()


    cursor.close()

    connection.close()


    # =====================================================
    # SUMMARY
    # =====================================================

    print(
        "\n=========================================="
    )

    print(
        "SYNTHETIC DATASET CREATED"
    )

    print(
        "=========================================="
    )

    print(
        f"Old records deleted: {deleted}"
    )

    print(
        f"New records inserted: {rows_inserted}"
    )

    print(
        f"Records per action: {N_PER_ACTION}"
    )

    print(
        "Expected total: 2100"
    )

    print(
        "Business-context features populated."
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    seed()