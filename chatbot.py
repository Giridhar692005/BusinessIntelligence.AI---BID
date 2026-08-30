import os
import json
import requests
from google import genai

from root_cause import full_root_cause_report
from action_engine import generate_actions, rank_actions, get_historical_scores
from text_retrieval import get_supporting_evidence
from database import get_connection

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
MAX_TOOL_ITERATIONS = 5


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_anomaly_report",
            "description": "Get the deterministic statistical root-cause report for a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get ranked business actions for a KPI using historical analyst feedback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kpi": {"type": "string"},
                },
                "required": ["kpi"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_evidence",
            "description": "Search customer reviews and support tickets related to a date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_feedback_history",
            "description": "Get historical analyst feedback and outcomes for a KPI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kpi": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["kpi"],
            },
        },
    },
]


def _run_tool(name: str, arguments: dict, kpi_df, reviews_df) -> dict:
    try:
        if name == "get_anomaly_report":
            return full_root_cause_report(
                kpi_df,
                arguments["date"],
                kpi_columns=[c for c in kpi_df.columns if c != "date"],
                window=14,
                threshold=2.5,
            )

        if name == "get_recommendations":
            kpi = arguments["kpi"].strip().lower()
            actions = generate_actions(kpi)
            historical_scores = get_historical_scores(kpi)
            return {
                "recommendations": rank_actions(
                    actions,
                    historical_scores=historical_scores
                )
            }

        if name == "search_evidence":
            fake_report = {"anomaly_date": arguments["date"]}
            return get_supporting_evidence(
                fake_report,
                reviews_df,
                date_window_days=3,
                top_k=5,
            )

        if name == "get_feedback_history":
            kpi = arguments["kpi"].strip().lower()
            limit = arguments.get("limit", 10)

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT action_id, recommended_action, analyst_rating,
                       outcome, created_at
                FROM business_decisions
                WHERE kpi = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (kpi, limit),
            )

            columns = [d[0] for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cursor.close()
            connection.close()

            for row in rows:
                if row.get("created_at"):
                    row["created_at"] = row["created_at"].isoformat()

            return {"feedback_history": rows}

        return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": str(e)}


SYSTEM_PROMPT = """
You are a practical Business Intelligence assistant.

You have access to deterministic business-analysis tools.

IMPORTANT:
- Never invent KPI values, anomaly results, dates, recommendations, or historical feedback.
- When a question requires business data, use the appropriate tool first.
- Python and the database are the quantitative source of truth.
- Explain results in clear, natural language.
- Keep answers concise but useful.
- When recommending an action, explain what should actually be done and why.
- When the user asks about a PDF, use the PDF document context supplied by Gemini.
- Do not claim information exists in a PDF unless it is actually present in the document.
- Distinguish clearly between information from the business dataset and information from the uploaded document.
"""


def chat(user_message, history, kpi_df, reviews_df, api_key=None, pdf_file=None):
    """
    Handles normal KPI/business questions through Groq tools.

    If pdf_file is supplied, Gemini is used to answer questions about
    the uploaded PDF. The existing CSV/business-data chatbot remains
    unchanged for non-PDF questions.
    """

    if pdf_file is not None:
        return chat_with_pdf(
            user_message=user_message,
            history=history,
            pdf_file=pdf_file,
        )

    api_key = api_key or os.environ.get("GROQ_API_KEY")

    if not api_key:
        return {
            "reply": "GROQ_API_KEY is not set.",
            "history": history,
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    for _ in range(MAX_TOOL_ITERATIONS):

        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 700,
                "reasoning_effort": "low",
                "messages": messages,
                "tools": TOOLS,
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]

        tool_calls = message.get("tool_calls")

        if not tool_calls:
            reply = message.get("content", "").strip()

            updated_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]

            return {
                "reply": reply,
                "history": updated_history,
            }

        messages.append(message)

        for call in tool_calls:

            name = call["function"]["name"]

            try:
                arguments = json.loads(
                    call["function"]["arguments"]
                )
            except json.JSONDecodeError:
                arguments = {}

            result = _run_tool(
                name,
                arguments,
                kpi_df,
                reviews_df,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(
                        result,
                        default=str,
                    ),
                }
            )

    fallback = (
        "I couldn't complete that analysis. "
        "Please narrow the question and try again."
    )

    return {
        "reply": fallback,
        "history": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": fallback},
        ],
    }


def upload_pdf_to_gemini(pdf_file):
    """
    Upload a PDF to Gemini's Files API.

    pdf_file can be:
      - a local file path
      - a file-like object
    """

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in .env"
        )

    client = genai.Client(
        api_key=api_key
    )

    uploaded = client.files.upload(
        file=pdf_file,
        config={
            "mime_type": "application/pdf"
        },
    )

    return {
        "name": uploaded.name,
        "uri": uploaded.uri,
        "mime_type": uploaded.mime_type,
    }


def ask_pdf_gemini(
    pdf_reference,
    question,
):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in .env"
        )

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
You are answering a user's question about an uploaded business PDF.

Question:
{question}

Instructions:
- Answer only from information present in the PDF.
- Pay attention to tables, charts, diagrams, headings, and footnotes.
- Explain numbers accurately.
- If the PDF does not contain enough information to answer, say so.
- Do not invent missing information.
- Write clearly for a business user.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {
                "file_data": {
                    "file_uri": pdf_reference["uri"],
                    "mime_type": "application/pdf",
                }
            },
            prompt,
        ],
    )

    return response.text.strip()


def chat_with_pdf(
    user_message,
    history,
    pdf_file,
):
    try:
        pdf_reference = upload_pdf_to_gemini(
            pdf_file
        )

        reply = ask_pdf_gemini(
            pdf_reference,
            user_message,
        )

        return {
            "reply": reply,
            "history": history + [
                {
                    "role": "user",
                    "content": user_message,
                },
                {
                    "role": "assistant",
                    "content": reply,
                },
            ],
        }

    except Exception as e:

        return {
            "reply": f"Unable to analyze the PDF: {str(e)}",
            "history": history,
        }