import os
import time
from google import genai

def generate_health_ai_summary(user_profile: dict, metrics: list[dict], records: list[dict]) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an AI healthcare assistant for a student project.
Do not diagnose disease with certainty.
Do not replace a doctor.
Give a clear, helpful health analysis.

Return in this exact format:

SUMMARY:
- ...

CURRENT RISKS:
- ...
- ...

REPEATED PATTERNS:
- ...
- ...

MISSING DATA:
- ...
- ...

RECOMMENDATIONS:
- ...
- ...

Do not repeat the raw patient profile dictionary in the final answer.

PATIENT PROFILE:
{user_profile}

HEALTH METRICS:
{metrics}

MEDICAL RECORDS:
{records}
"""

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite-preview-09-2025",
    ]

    last_error = None

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if getattr(response, "text", None):
                    return response.text

                raise ValueError(f"{model_name} returned empty response")

            except Exception as e:
                last_error = e
                # small backoff for temporary 503/high-demand issues
                time.sleep(2 * (attempt + 1))

    raise ValueError(f"Gemini failed after retries: {last_error}")