"""
generate_synthetic_reviews.py
------------------------------
Creates synthetic customer reviews spread across the same 180-day window
as your KPI data. Review VOLUME and SENTIMENT spike around the same four
anomaly events already planted in your KPI synthetic data, so the RAG
layer has something real to retrieve when explaining an anomaly:

    - Flash sale spike     -> excited "great deal" reviews, higher volume
    - Site outage crash    -> frustrated "site was down / checkout failed"
                               complaints, higher volume
    - Marketing overspend  -> "saw the same ad everywhere" comments
    - Gradual AOV drift    -> "used a coupon", "bought the cheaper option"
                               comments, spread over a longer window

Every other day gets a small amount of ordinary "ambient" review noise
(shipping speed, product quality, generic feedback) so retrieval has to
actually distinguish signal from noise -- not just find "the only reviews
that exist."

IMPORTANT: Update ANOMALY_EVENTS below so the dates match exactly what
your KPI synthetic-data script planted. As shipped here, the anomalies
are spread evenly across the 180-day window as a placeholder -- swap in
your real anomaly dates so the review evidence lines up with what
/root-cause actually flags.
"""

import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)

# --- Adjust to match your actual KPI synthetic data ---
START_DATE = datetime(2026, 7, 27)
TOTAL_DAYS = 30

ANOMALY_EVENTS = {
    "flash_sale":       {"date": START_DATE + timedelta(days=40),  "window": 1},
    "outage":           {"date": START_DATE + timedelta(days=85),  "window": 1},
    "overspend":        {"date": START_DATE + timedelta(days=120), "window": 2},
    "aov_drift_start":  {"date": START_DATE + timedelta(days=145), "window": 20},  # gradual
}

# --- Text pools ---

AMBIENT_REVIEWS = [
    "Shipping was faster than I expected, product arrived in great shape.",
    "Decent quality for the price, would probably buy again.",
    "Packaging could be better but the item itself is fine.",
    "Customer service was helpful when I had a sizing question.",
    "Not bad, took a bit longer to arrive than the estimate said.",
    "Exactly as described on the product page.",
    "Love this, already ordered a second one for a friend.",
    "It's okay, nothing special but does the job.",
    "Great value, will be shopping here again.",
    "The color was slightly different from the photos but still nice.",
]

FLASH_SALE_REVIEWS = [
    "Grabbed three of these during the flash sale, incredible price!",
    "Saw the deal pop up and bought immediately, glad I did.",
    "Best discount I've seen from this store all year, stocked up.",
    "The sale price was too good to pass up, ordered right away.",
    "Checked out fast before the flash sale ended, worth it.",
    "Told my friends about the sale, we all ordered together.",
    "Site was busy during the sale but I got my order in.",
    "Cart almost sold out during the flash sale, happy I got mine.",
]

OUTAGE_REVIEWS = [
    "Checkout kept failing, had to try four times before it worked.",
    "Site was completely down for me this afternoon, very frustrating.",
    "Got an error page every time I tried to pay, gave up for a while.",
    "App crashed twice during checkout, lost my cart both times.",
    "Couldn't complete my order for almost an hour, page wouldn't load.",
    "Payment kept timing out, not sure if I got charged multiple times.",
    "Website was extremely slow and eventually just stopped responding.",
    "Tried on mobile and desktop, both were broken most of the day.",
]

OVERSPEND_REVIEWS = [
    "I keep seeing the same ad from this store on every app I open.",
    "Feels like I'm being retargeted nonstop, saw the ad five times today.",
    "Clicked the ad out of curiosity more than actual interest.",
    "Ads are everywhere lately, finally clicked one out of annoyance.",
    "Not sure why I'm seeing so many ads for this store this week.",
]

AOV_DRIFT_REVIEWS = [
    "Used a coupon code, ended up paying less than usual.",
    "Went with the smaller/cheaper bundle this time instead of the full set.",
    "Only bought one item instead of my usual bigger order.",
    "Prices seem to have small discounts stacking lately, nice for my wallet.",
    "Skipped the add-ons this time, just got the basic item.",
    "Noticed more promo codes floating around recently, used one.",
]

SOURCES = ["review", "review", "review", "ticket"]  # mostly reviews, some tickets


def _random_reviews(pool, count):
    return [random.choice(pool) for _ in range(count)]


def generate_reviews():
    rows = []
    review_id = 0

    for day_offset in range(TOTAL_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)

        # Ambient baseline: most days get 0-3 ordinary reviews
        ambient_count = random.choice([0, 1, 1, 2, 2, 3])
        texts_today = _random_reviews(AMBIENT_REVIEWS, ambient_count)

        # Check if this day falls inside any anomaly window, add extra
        # volume + matching sentiment on top of the ambient baseline
        for event_name, event in ANOMALY_EVENTS.items():
            event_date = event["date"]
            window = event["window"]
            delta_days = (current_date - event_date).days

            if 0 <= delta_days < window:
                if event_name == "flash_sale":
                    texts_today += _random_reviews(FLASH_SALE_REVIEWS, random.randint(6, 10))
                elif event_name == "outage":
                    texts_today += _random_reviews(OUTAGE_REVIEWS, random.randint(6, 10))
                elif event_name == "overspend":
                    texts_today += _random_reviews(OVERSPEND_REVIEWS, random.randint(2, 4))
                elif event_name == "aov_drift_start":
                    texts_today += _random_reviews(AOV_DRIFT_REVIEWS, random.randint(1, 3))

        for text in texts_today:
            rows.append({
                "id": f"txt_{review_id:04d}",
                "date": current_date.strftime("%Y-%m-%d"),
                "text": text,
                "source": random.choice(SOURCES),
            })
            review_id += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_reviews()
    df.to_csv("synthetic_reviews.csv", index=False)
    print(f"Generated {len(df)} review/ticket rows across {TOTAL_DAYS} days.")
    print(f"Saved to synthetic_reviews.csv")
    print("\nAnomaly event windows used:")
    for name, event in ANOMALY_EVENTS.items():
        print(f"  {name}: {event['date'].strftime('%Y-%m-%d')} (+{event['window']} day window)")
