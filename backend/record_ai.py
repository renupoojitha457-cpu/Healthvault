import os
from typing import Optional, List

from pydantic import BaseModel, Field
from google import genai


class MedicineItem(BaseModel):
    name: str = ""
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class MetricItem(BaseModel):
    name: str = ""
    value: Optional[float] = None
    unit: Optional[str] = None


class RecordAIResult(BaseModel):
    doctor: Optional[str] = None
    hospital: Optional[str] = None
    diagnosis: List[str] = Field(default_factory=list)
    medicines: List[MedicineItem] = Field(default_factory=list)
    metrics: List[MetricItem] = Field(default_factory=list)
    summary: str = "No summary generated."


def extract_and_summarize_record(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        return {
            "doctor": None,
            "hospital": None,
            "diagnosis": [],
            "medicines": [],
            "metrics": [],
            "summary": "No readable text could be extracted from this record."
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "doctor": None,
            "hospital": None,
            "diagnosis": [],
            "medicines": [],
            "metrics": [],
            "summary": "AI summary unavailable because GEMINI_API_KEY is not set."
        }

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a medical document extraction assistant.

Read the OCR text from a medical record and return structured information.

Rules:
- Extract only what is clearly present.
- Do not invent values.
- Keep summary short, clear, and patient-friendly.
- If something is missing, leave it empty or null.

OCR TEXT:
{raw_text}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": RecordAIResult,
                "temperature": 0.2,
            },
        )

        data = response.parsed
        if data is None:
            return {
                "doctor": None,
                "hospital": None,
                "diagnosis": [],
                "medicines": [],
                "metrics": [],
                "summary": "AI could not parse this record."
            }

        return data.model_dump()

    except Exception as e:
        print("AI extraction/summary error:", e)
        return {
            "doctor": None,
            "hospital": None,
            "diagnosis": [],
            "medicines": [],
            "metrics": [],
            "summary": "AI summary is temporarily unavailable."
        }