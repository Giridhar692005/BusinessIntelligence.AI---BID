from recommendation_engine_v5 import rank_actions


# =========================================================
# TEST SCENARIOS
# =========================================================

situations = {

    "A - Revenue increase driven by orders": {

        "kpi": "revenue",

        "primary_driver_pct_change": 28.88,

        "confidence_score": 0.80,

        "visitors_change": 13.62,

        "orders_change": 28.88,

        "revenue_change": 30.00,

        "aov_change": 19.92,

        "cac_change": -5.00,

        "ad_spend_change": -14.65
    },


    "B - Revenue collapse": {

        "kpi": "revenue",

        "primary_driver_pct_change": -30.00,

        "confidence_score": 0.85,

        "visitors_change": -20.00,

        "orders_change": -25.00,

        "revenue_change": -30.00,

        "aov_change": -5.00,

        "cac_change": 15.00,

        "ad_spend_change": 20.00
    },


    "C - Revenue rising but AOV falling": {

        "kpi": "revenue",

        "primary_driver_pct_change": 25.00,

        "confidence_score": 0.78,

        "visitors_change": 20.00,

        "orders_change": 30.00,

        "revenue_change": 10.00,

        "aov_change": -15.00,

        "cac_change": -5.00,

        "ad_spend_change": 5.00
    },


    "D - Revenue falling while ad spend rises": {

        "kpi": "revenue",

        "primary_driver_pct_change": -20.00,

        "confidence_score": 0.82,

        "visitors_change": 5.00,

        "orders_change": -18.00,

        "revenue_change": -20.00,

        "aov_change": -3.00,

        "cac_change": 30.00,

        "ad_spend_change": 35.00
    },


    "E - Traffic up but orders down": {

        "kpi": "revenue",

        "primary_driver_pct_change": -10.00,

        "confidence_score": 0.76,

        "visitors_change": 25.00,

        "orders_change": -10.00,

        "revenue_change": 2.00,

        "aov_change": 5.00,

        "cac_change": 15.00,

        "ad_spend_change": 10.00
    }
}


# =========================================================
# RUN TEST
# =========================================================

for name, context in situations.items():

    print("\n")
    print("=" * 75)

    print(name)

    print("=" * 75)

    print(
        f"Revenue: {context['revenue_change']}% | "
        f"Orders: {context['orders_change']}% | "
        f"Visitors: {context['visitors_change']}% | "
        f"AOV: {context['aov_change']}% | "
        f"CAC: {context['cac_change']}% | "
        f"Ad spend: {context['ad_spend_change']}%"
    )


    recommendations = rank_actions(

        context["kpi"],

        context
    )


    print("\nRecommendations:")


    for index, recommendation in enumerate(

        recommendations,

        start=1

    ):

        print(

            f"{index}. "
            f"{recommendation['action']} "
            f"-> "
            f"{recommendation['success_probability']:.3f}"
        )