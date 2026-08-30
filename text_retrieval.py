"""
text_retrieval.py
------------------
Finds unstructured customer-text evidence (reviews/tickets) relevant to
a given KPI anomaly date.

Design choice worth explaining to judges: this is deliberately NOT a
generic "search everything by similarity" RAG setup. A pure semantic
search could surface something that reads similarly but happened three
months ago, which would be a misleading "cause." Instead this does:

    1. DATE FILTER FIRST -- only look at text from within N days of the
       anomaly date. This is the primary signal.
    2. SIMILARITY SECOND -- within that date window, rank by how well
       each chunk matches a query built from the anomaly itself (e.g.
       "why did conversion rate drop sharply").

No vector database is used -- at this scale (a few hundred chunks) numpy
cosine similarity is exact and instant, so a database like Pinecone/FAISS
would be unnecessary infrastructure for a hackathon demo, exactly like
the numeric anomaly detector avoids one.

Embeddings run locally via sentence-transformers -- free, no API key,
no extra rate limits, and keeps this independent of the Groq narrative
LLM call.
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, good enough for short review text
_model = None  # lazy-loaded so importing this file doesn't immediately load the model


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def load_reviews(csv_path: str = "synthetic_reviews.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _cosine_similarity(query_vec: np.ndarray, chunk_vecs: np.ndarray) -> np.ndarray:
    """
    query_vec: shape (embedding_dim,)
    chunk_vecs: shape (num_chunks, embedding_dim)
    Returns similarity score per chunk, shape (num_chunks,)
    """
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    chunk_norms = chunk_vecs / (np.linalg.norm(chunk_vecs, axis=1, keepdims=True) + 1e-10)
    return chunk_norms @ query_norm


def _build_query_from_report(report: dict) -> str:
    """
    Turns the structured root-cause report into a short natural-language
    query, so we search for text that talks about the SAME kind of change
    the statistics already found (e.g. "conversion rate dropped sharply").
    """
    primary_driver = report.get("drivers", {}).get("primary_driver", "revenue")
    pct_change = report.get("drivers", {}).get("primary_driver_pct_change", 0)
    direction = "dropped" if pct_change < 0 else "increased"
    return f"customers talking about why {primary_driver} {direction} sharply"


def get_supporting_evidence(
    report: dict,
    reviews_df: pd.DataFrame,
    date_window_days: int = 3,
    top_k: int = 5,
) -> dict:
    """
    Main entry point. Given a root-cause report and the loaded reviews
    dataframe, returns the top_k most relevant review/ticket texts from
    within date_window_days of the anomaly date.

    Returns a dict shaped for easy use in the LLM narrative prompt.
    """
    anomaly_date = pd.to_datetime(report["anomaly_date"])

    # Step 1: date filter first
    window_start = anomaly_date - pd.Timedelta(days=date_window_days)
    window_end = anomaly_date + pd.Timedelta(days=date_window_days)
    nearby = reviews_df[
        (reviews_df["date"] >= window_start) & (reviews_df["date"] <= window_end)
    ].copy()

    if len(nearby) == 0:
        return {
            "anomaly_date": report["anomaly_date"],
            "evidence": [],
            "note": f"No customer text found within {date_window_days} days of this anomaly.",
        }

    # Step 2: similarity ranking within that window
    model = _get_model()
    query = _build_query_from_report(report)
    query_vec = model.encode(query)
    chunk_vecs = model.encode(nearby["text"].tolist())

    scores = _cosine_similarity(query_vec, chunk_vecs)
    nearby["similarity"] = scores
    nearby = nearby.sort_values("similarity", ascending=False).head(top_k)

    evidence = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "text": row["text"],
            "source": row["source"],
            "similarity": round(float(row["similarity"]), 3),
        }
        for _, row in nearby.iterrows()
    ]

    return {
        "anomaly_date": report["anomaly_date"],
        "query_used": query,
        "date_window_days": date_window_days,
        "evidence": evidence,
    }
