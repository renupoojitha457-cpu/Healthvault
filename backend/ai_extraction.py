import re

def extract_data(text):
    result = {
        "doctor": None,
        "metrics": []
    }

    if not text:
        return result

    doc_match = re.search(r"(Dr\.?\s+[A-Za-z]+)", text)
    if doc_match:
        result["doctor"] = doc_match.group(1)

    pattern = r"([A-Za-z ]+)\s*[:\-]?\s*(\d+\.?\d*)\s*([a-zA-Z/%]+)"
    matches = re.findall(pattern, text)

    for m in matches:
        name = m[0].strip()
        value = float(m[1])
        unit = m[2]

        result["metrics"].append({
            "name": name,
            "value": value,
            "unit": unit
        })

    return result