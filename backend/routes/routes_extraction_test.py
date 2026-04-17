from fastapi import APIRouter
from pydantic import BaseModel
from ai_extraction import extract_data
router = APIRouter()


class TextInput(BaseModel):
    raw_text: str


@router.post("/extract")
def test_extract(payload: TextInput):
    data = extract_medical_data_from_text(payload.raw_text)
    return data