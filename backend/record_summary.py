import re

def generate_record_summary(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return "No readable text could be extracted from this record."

    text = re.sub(r"\s+", " ", raw_text).strip()

    lines = re.split(r"(?<=[.:])\s+|\n", text)
    lines = [line.strip() for line in lines if line.strip()]

    important_parts = []
    for line in lines:
        if len(line) > 5:
            important_parts.append(line)
        if len(important_parts) == 5:
            break

    if not important_parts:
        return text[:400]

    summary = " ".join(important_parts)
    return summary[:600]