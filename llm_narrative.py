"""
llm_narrative.py
----------------

LLM inference layer for Business AI.

IMPORTANT DESIGN:

This file contains the reusable LLM execution logic.

Business-specific configuration is loaded from:

    business_config.py

Prompt templates are loaded from:

    prompts.py

The existing public interface is preserved so existing
main.py / frontend code does not need to change.
"""


# =========================================================
# IMPORTS
# =========================================================

import os
import json
import requests

from dotenv import load_dotenv

from business_config import BUSINESS_CONFIG

from prompts import (
    build_narrative_system_prompt,
    build_narrative_user_prompt,
    build_business_factor_system_prompt,
    build_action_system_prompt
)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)


GROQ_MODEL = os.environ.get(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


# =========================================================
# PERSONAS
# =========================================================
#
# IMPORTANT:
#
# main.py currently imports PERSONAS.
#
# Therefore we expose it here for compatibility.
#
# But the actual data comes from business_config.py.
# =========================================================

PERSONAS = {

    persona["id"]: {

        "display_name":
            persona.get(
                "display_name",
                persona["id"]
            ),

        "focus":
            persona.get(
                "focus",
                []
            )

    }

    for persona in BUSINESS_CONFIG.get(
        "personas",
        []
    )
}


# =========================================================
# PERSONA LOOKUP
# =========================================================

def get_persona(
    persona_key: str
):
    """
    Find a configured persona.

    The persona itself is business configuration,
    not hard-coded LLM logic.
    """

    return PERSONAS.get(
        persona_key
    )


# =========================================================
# EVIDENCE FORMATTING
# =========================================================

def _format_evidence(
    evidence: dict
) -> str:

    if not evidence:

        return ""


    evidence_items = evidence.get(
        "evidence"
    )


    if not evidence_items:

        return ""


    lines = [

        "\nHere is supporting customer/text evidence "
        "retrieved around the anomaly date:\n"
    ]


    for item in evidence_items:

        item_date = item.get(
            "date",
            "unknown"
        )

        source = item.get(
            "source",
            "unknown"
        )

        text = item.get(
            "text",
            ""
        )


        lines.append(
            f"- ({item_date}, {source}): \"{text}\""
        )


    return (
        "\n".join(lines)
        +
        "\n"
    )


# =========================================================
# USER PROMPT
# =========================================================

def _build_user_prompt(
    report: dict,
    evidence: dict = None
) -> str:

    return build_narrative_user_prompt(
        report,
        evidence
    )


# =========================================================
# MESSAGE BUILDER
# =========================================================

def build_messages(
    report: dict,
    persona_key: str,
    evidence: dict = None
) -> list:

    if persona_key not in PERSONAS:

        raise ValueError(
            f"Unknown persona '{persona_key}'. "
            f"Options: {list(PERSONAS)}"
        )


    return [

        {
            "role": "user",

            "content":
                _build_user_prompt(
                    report,
                    evidence
                )
        }
    ]


# =========================================================
# NARRATIVE GENERATION
# =========================================================

def generate_narrative(
    report: dict,
    persona_key: str,
    api_key: str = None,
    evidence: dict = None
) -> dict:

    """
    Existing public function preserved.

    Returns the same general structure as before:

        {
            "persona": ...,
            "persona_display_name": ...,
            "narrative": "...",
            "abstained": ...,
            "evidence_used": ...
        }
    """

    api_key = (api_key or os.environ.get("GROQ_API_KEY"))
    print("LLM ACTION API KEY FOUND:", bool(api_key))

    if not api_key:

        return {

            "persona":
                persona_key,

            "error":
                "No Groq API key found. "
                "Set GROQ_API_KEY or pass api_key explicitly."
        }


    persona = get_persona(
        persona_key
    )


    if persona is None:

        return {

            "persona":
                persona_key,

            "error":
                f"Unknown persona '{persona_key}'. "
                f"Options: {list(PERSONAS)}"
        }


    # -----------------------------------------------------
    # Build prompts
    # -----------------------------------------------------

    system_prompt = (
        build_narrative_system_prompt(
            BUSINESS_CONFIG,
            persona
        )
    )


    messages = [

        {
            "role":
                "system",

            "content":
                system_prompt
        },

        *build_messages(
            report,
            persona_key,
            evidence
        )
    ]


    # -----------------------------------------------------
    # Call Groq
    # -----------------------------------------------------

    try:

        response = requests.post(

            GROQ_API_URL,

            headers={

                "Authorization":
                    f"Bearer {api_key}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    GROQ_MODEL,

                "max_tokens":
                    700,

                "reasoning_effort":
                    "low",

                "messages":
                    messages
            },

            timeout=30
        )


        response.raise_for_status()


        data = response.json()


        narrative_text = (

            data["choices"]
            [0]["message"]
            ["content"]
            .strip()
        )


        if not narrative_text:

            return {

                "persona":
                    persona_key,

                "persona_display_name":
                    persona["display_name"],

                "error":
                    "Groq returned an empty response."
            }


        return {

            "persona":
                persona_key,

            "persona_display_name":
                persona["display_name"],

            "narrative":
                narrative_text,

            "abstained":
                report.get(
                    "confidence",
                    {}
                ).get(
                    "should_abstain",
                    False
                ),

            "evidence_used":
                bool(
                    evidence
                    and evidence.get(
                        "evidence"
                    )
                )
        }


    except requests.exceptions.RequestException as e:

        return {

            "persona":
                persona_key,

            "persona_display_name":
                persona["display_name"],

            "error":
                f"Groq API call failed: {str(e)}"
        }


# =========================================================
# BUSINESS FACTOR EXTRACTION
# =========================================================

def extract_business_factors(
    report: dict,
    api_key: str = None,
    evidence: dict = None
) -> dict:

    """
    Existing public function preserved.

    Extracts structured business information from the
    statistical report and retrieved evidence.
    """

    api_key = (
        api_key
        or os.environ.get(
            "GROQ_API_KEY"
        )
    )


    if not api_key:

        return {
            "error":
                "No Groq API key found."
        }


    context = {

        "statistical_report":
            report,

        "retrieved_evidence":
            evidence
    }


    system_prompt = (
        build_business_factor_system_prompt()
    )


    user_prompt = f"""

Analyze this business situation:

{json.dumps(
    context,
    indent=2,
    default=str
)}

Return EXACTLY this structure:

{{
    "drivers": [
        {{
            "factor": "string",
            "direction": "positive | negative | neutral",
            "importance": 0.0,
            "evidence": "string"
        }}
    ],

    "risks": [
        {{
            "risk": "string",
            "severity": 0.0,
            "evidence": "string"
        }}
    ],

    "opportunities": [
        {{
            "opportunity": "string",
            "potential": 0.0,
            "evidence": "string"
        }}
    ],

    "constraints": [
        {{
            "constraint": "string",
            "severity": 0.0,
            "evidence": "string"
        }}
    ],

    "customer_sentiment": {{
        "direction": "positive | negative | mixed | unknown",
        "confidence": 0.0,
        "evidence": "string"
    }},

    "market_factors": [
        {{
            "factor": "string",
            "relevance": 0.0,
            "evidence": "string"
        }}
    ],

    "seasonality": {{
        "relevance": 0.0,
        "reason": "string"
    }},

    "candidate_actions": [
        {{
            "action": "string",
            "reason": "string",
            "expected_lever": "string",
            "risk": "string"
        }}
    ],

    "overall_confidence": 0.0
}}

All numeric scores must be between 0 and 1.

Return ONLY the JSON object.
"""


    messages = [

        {
            "role":
                "system",

            "content":
                system_prompt
        },

        {
            "role":
                "user",

            "content":
                user_prompt
        }
    ]


    try:

        response = requests.post(

            GROQ_API_URL,

            headers={

                "Authorization":
                    f"Bearer {api_key}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    GROQ_MODEL,

                "max_tokens":
                    1200,

                "reasoning_effort":
                    "low",

                "messages":
                    messages,

                "response_format": {
                    "type":
                        "json_object"
                }
            },

            timeout=30
        )


        response.raise_for_status()


        data = response.json()


        raw_content = (

            data["choices"]
            [0]["message"]
            ["content"]
            .strip()
        )


        if not raw_content:

            return {

                "error":
                    "LLM returned an empty response."
            }


        try:

            factors = json.loads(
                raw_content
            )


        except json.JSONDecodeError:

            return {

                "error":
                    "LLM returned invalid JSON.",

                "raw_response":
                    raw_content
            }


        return factors


    except requests.exceptions.RequestException as e:

        return {

            "error":
                f"Groq API call failed: {str(e)}"
        }


    except Exception as e:

        return {

            "error":
                f"Business factor extraction failed: {str(e)}"
        }


# =========================================================
# LLM ACTION GENERATION
# =========================================================

def generate_llm_actions(report: dict, evidence: dict = None, narrative: str = None, api_key: str = None) -> list:

    """
    Existing public function preserved.

    Generates context-specific candidate actions.

    These actions can later be merged with actions from
    the configurable action catalog.
    """

    api_key = (
        api_key
        or os.environ.get(
            "GROQ_API_KEY"
        )
    )

    if not api_key:

        return []


    should_abstain = (

        report
        .get(
            "confidence",
            {}
        )
        .get(
            "should_abstain",
            False
        )
    )


    if should_abstain:

        return []


    system_prompt = (
        build_action_system_prompt()
    )

    narrative_block = ""

    if narrative:
       narrative_block = f"""
       LLM BUSINESS ANALYSIS:
       {narrative}
    Use this analysis together with the statistical report.
    The action must directly address the situation described above.
    """
    user_prompt = f"""
    {narrative_block}
Statistical report and supporting evidence:
{json.dumps(
    {
        "report":
            report,

        "evidence":
            evidence
    },

    indent=2,

    default=str
)}


Return EXACTLY this structure:

[
    {{
        "action":
            "string - specific, concrete action",

        "lever":
            "string - short business lever name",

        "owner":
            "string - team or role who would own this",

        "expected_impact":
            "string",

        "monitor":
            "string - metric(s) to watch"
    }}
]

Return 2 to 3 actions.

Return ONLY the JSON array.
"""


    messages = [

        {
            "role":
                "system",

            "content":
                system_prompt
        },

        {
            "role":
                "user",

            "content":
                user_prompt
        }
    ]


    try:

        response = requests.post(

            GROQ_API_URL,

            headers={

                "Authorization":
                    f"Bearer {api_key}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    GROQ_MODEL,

                "max_tokens":
                    700,

                "reasoning_effort":
                    "low",

                "messages":
                    messages
            },

            timeout=30
        )


        response.raise_for_status()


        data = response.json()


        raw_content = (

            data["choices"]
            [0]["message"]
            ["content"]
            .strip()
        )


        # -------------------------------------------------
        # Remove optional markdown fences
        # -------------------------------------------------

        if raw_content.startswith(
            "```"
        ):

            raw_content = (
                raw_content
                .strip("`")
            )


            if raw_content.startswith(
                "json\n"
            ):

                raw_content = (
                    raw_content[5:]
                )


        actions = json.loads(
            raw_content
        )


        if not isinstance(
            actions,
            list
        ):

            return []


        required_keys = {

            "action",

            "lever",

            "owner",

            "expected_impact",

            "monitor"
        }


        valid_actions = []


        for action in actions:

            if not isinstance(
                action,
                dict
            ):

                continue


            if not required_keys.issubset(
                action.keys()
            ):

                continue


            valid_actions.append(
                action
            )


        return valid_actions
    

    except requests.exceptions.RequestException as e:
       print("LLM ACTION REQUEST ERROR:", e)
       return []

    except json.JSONDecodeError as e:
        print("LLM ACTION JSON ERROR:", e)
        print("RAW RESPONSE:", raw_content if "raw_content" in locals() else "No response")
        return []

    except Exception as e:
       print("LLM ACTION ERROR:", type(e).__name__, e)
       return []



# =========================================================
# ALL PERSONAS
# =========================================================

def generate_all_narratives(
    report: dict,
    api_key: str = None,
    evidence: dict = None
) -> dict:

    """
    Generates narratives for every persona configured
    in business_config.py.

    Existing main.py interface is preserved.
    """

    results = {}


    for persona_key in PERSONAS:

        results[persona_key] = (
            generate_narrative(

                report,

                persona_key,

                api_key=api_key,

                evidence=evidence
            )
        )


    return results


# =========================================================
# SIMPLE TEST
# =========================================================

if __name__ == "__main__":

    test_report = {

        "drivers": {

            "primary_driver":
                "orders",

            "primary_driver_pct_change":
                28.88
        },

        "confidence": {

            "score":
                0.60,

            "should_abstain":
                False
        }
    }


    print(
        json.dumps(
            PERSONAS,
            indent=2
        )
    )


    result = extract_business_factors(

        test_report,

        evidence=None
    )


    print(
        json.dumps(
            result,

            indent=2
        )
    )