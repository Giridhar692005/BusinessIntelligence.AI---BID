# =========================================================
# BUSINESS CONFIGURATION
# =========================================================
#
# This file contains business-specific configuration.
#
# The engine does not depend on a specific industry.
# Change this file when configuring the system for a
# particular company.
#
# Later this can be loaded from PostgreSQL instead.
# =========================================================


BUSINESS_CONFIG = {

    "company_name": "Demo Business",

    "business_type": "ecommerce",

    "business_description": (
        "An online business that sells products directly "
        "to customers."
    ),

    # -----------------------------------------------------
    # Available KPIs for this current demo
    # -----------------------------------------------------

    "kpis": [

        "revenue",
        "orders",
        "visitors",
        "conversion_rate",
        "aov",
        "cac",
        "ad_spend"

    ],
    # Whether a HIGHER value of each KPI is good for the business.
    # True = higher is better, False = lower is better,
    # omit a KPI entirely if direction genuinely depends on context --
    # the narrative will then say "not established" rather than guess.
    "kpi_direction": {
        "revenue": True,
        "conversion_rate": True,
        "orders": True,
        "visitors": True,
        "aov": True,
        "cac": False,          # lower cost-per-acquisition is better
        "ad_spend": None,      # ambiguous on its own -- context-dependent
    },
    # -----------------------------------------------------
    # Personas
    #
    # These are configuration, not LLM logic.
    # -----------------------------------------------------

    "personas": [

        {
            "id": "marketing_manager",

            "display_name":
                "Marketing Manager",

            "focus": [

                "marketing performance",

                "traffic sources",

                "campaign performance",

                "customer acquisition",

                "conversion performance",

                "marketing efficiency"

            ]
        },

        {
            "id": "sales_ops_manager",

            "display_name":
                "Sales/Ops Manager",

            "focus": [

                "sales performance",

                "order volume",

                "operational capacity",

                "fulfillment",

                "customer experience",

                "business execution"

            ]
        }
    ],
    "kpi_relationships": 
    {
       "revenue": ["visitors", "orders", "conversion_rate", "aov", "ad_spend"],
        "orders": ["visitors", "conversion_rate"],
         "cac": ["ad_spend", "orders"]
    }
}