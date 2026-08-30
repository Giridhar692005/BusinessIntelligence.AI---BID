# =========================================================
# recommendation_config.py
# =========================================================
#
# BUSINESS-SPECIFIC CONFIGURATION ONLY
#
# Change this file when using the system for another
# company/business.
#
# Do NOT put ML logic here.
# =========================================================


# ---------------------------------------------------------
# CURRENT DEMO BUSINESS
# ---------------------------------------------------------

BUSINESS_CONFIG = {

    "company_name": "Demo Business",

    "business_type": "ecommerce",

    "description": (
        "An online business selling products directly "
        "to customers."
    )
}


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

DATABASE_CONFIG = {

    "host": "localhost",

    "database": "business_Ai",

    "user": "postgres",

    "port": 5432
}


# ---------------------------------------------------------
# TRAINING CONFIGURATION
#
# These are ML settings, not business knowledge.
# You normally won't change them for a new business.
# ---------------------------------------------------------

MODEL_CONFIG = {

    "test_size": 0.25,

    "random_state": 42,

    "cv_folds": 5,

    "max_iter": 3000,

    "class_weight": "balanced"
}


# ---------------------------------------------------------
# DATABASE COLUMNS TO IGNORE
#
# These are technical columns rather than business
# features.
#
# We don't specify KPI names here.
# ---------------------------------------------------------
IGNORED_COLUMNS = {

    # Database / metadata
    "id",
    "anomaly_date",
    "created_at",
    "updated_at",

    # Explanation metadata
    "root_cause",

    # Internal action identifier
    "action_id",

    # -----------------------------------------------------
    # POST-DECISION INFORMATION
    # -----------------------------------------------------
    #
    # These values are known only after the recommendation
    # has been evaluated.
    #
    "outcome",
    "outcome_value",
    "analyst_rating",
    "action_taken"

}

# ---------------------------------------------------------
# CURRENT DEMO TEST CASE
#
# This is only for testing your current ecommerce example.
#
# Later this should come from the actual root-cause
# pipeline instead of being manually entered.
# ---------------------------------------------------------

DEMO_CONTEXT = {

    "kpi": "revenue",

    "primary_driver_pct_change": 28.88,

    "confidence_score": 0.80,

    "visitors_change": 13.62,

    "orders_change": 28.88,

    "revenue_change": 30.00,

    "aov_change": 19.92,

    "cac_change": -5.00,

    "ad_spend_change": -14.65
}