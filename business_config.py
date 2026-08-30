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