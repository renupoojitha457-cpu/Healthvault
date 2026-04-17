from ocr_utils import run_ocr
from record_ai import extract_and_summarize_record
from ocr_utils import run_ocr
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ocr_utils import run_ocr
from record_summary import generate_record_summary
from typing import List, Optional
from database import get_db
from auth_utils import get_current_user
from record_summary import generate_record_summary   
import models, schemas
import os, re, datetime



try:
    import pytesseract
    from PIL import Image
    import io as _io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import fitz
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
router = APIRouter()

# ── OCR ────────────────────────────────────────────────────────

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    image = image.convert("L")  # grayscale

    # enlarge image for better OCR
    w, h = image.size
    image = image.resize((w * 2, h * 2))

    # increase contrast
    image = ImageEnhance.Contrast(image).enhance(2.0)

    # sharpen text
    image = image.filter(ImageFilter.SHARPEN)

    # auto contrast
    image = ImageOps.autocontrast(image)

    # thresholding: make text darker and background cleaner
    image = image.point(lambda x: 0 if x < 150 else 255, "1")

    return image
def extract_text_from_pil_image(image: Image.Image) -> str:
    processed = preprocess_image_for_ocr(image)

    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 11",
        "--oem 3 --psm 4"
    ]

    texts = []
    for config in configs:
        try:
            text = pytesseract.image_to_string(processed, config=config).strip()
            if text:
                texts.append(text)
        except Exception as e:
            print(f"[OCR CONFIG ERROR] {config}: {e}")

    if not texts:
        return ""

    # return the longest extracted text
    return max(texts, key=len)

def run_ocr(file_bytes: bytes, filename: str) -> str:
    if not OCR_AVAILABLE:
        return ""

    try:
        # PDF handling
        if filename.lower().endswith(".pdf") and PDF_AVAILABLE:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            all_text = []

            for page_num in range(len(doc)):
                page = doc[page_num]

                # First try direct PDF text extraction
                page_text = page.get_text().strip()
                if len(page_text) > 20:
                    all_text.append(page_text)
                    continue

                # If not enough text, render page as image and OCR it
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                image = Image.open(_io.BytesIO(img_bytes))
                text = extract_text_from_pil_image(image)

                if text:
                    all_text.append(text)

            return "\n".join(all_text).strip()

        # Image handling
        image = Image.open(_io.BytesIO(file_bytes))
        return extract_text_from_pil_image(image)

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return ""
    
def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # common OCR cleanup
    text = text.replace("|", "I")
    text = text.replace("O.", "0.")
    text = text.replace("mg / dL", "mg/dL")
    text = text.replace("g / dL", "g/dL")

    return text.strip()

METRIC_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9\s\(\)\/%+-]{1,40}?)\s*[:\-]?\s*(\d+\.?\d*)\s*(mg/dL|g/dL|%|mIU/L|uIU/mL|ng/mL|pg/mL|mmHg|K/uL|IU/L|U/L|mmol/L)?\b",
    re.IGNORECASE
)

def extract_data(raw_text: str) -> dict:
    raw_text = clean_text(raw_text)
    if not raw_text:
        return {"metrics": [], "drugs": [], "doctor": None, "date": None}
    metrics, seen = [], set()
    for m in METRIC_RE.finditer(raw_text):
        name = m.group(1).strip()
        if name.lower() not in seen and len(name) > 1:
            seen.add(name.lower())
            metrics.append({"name": name, "value": float(m.group(2)), "unit": m.group(3)})
    doctor = re.search(r"Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", raw_text)
    date   = re.search(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b", raw_text)
    drugs  = re.findall(r"\b([A-Z][a-z]+(?:mycin|cillin|prazole|sartan|statin|olol|pril|pine|mab|nib|vir))\b", raw_text)
    return {"doctor": doctor.group(0) if doctor else None, "date": date.group(0) if date else None,
            "drugs": list(set(drugs)), "metrics": metrics}

NORMAL_RANGES = {
    "ldl": {"low": 0, "high": 100}, "ldl cholesterol": {"low": 0, "high": 100},
    "blood glucose": {"low": 70, "high": 99}, "glucose": {"low": 70, "high": 99},
    "hba1c": {"low": 0, "high": 5.6}, "haemoglobin": {"low": 12, "high": 17.5},
    "hemoglobin": {"low": 12, "high": 17.5}, "vitamin d": {"low": 30, "high": 100},
    "vitamin b12": {"low": 200, "high": 900}, "tsh": {"low": 0.4, "high": 4.0},
    "creatinine": {"low": 0.5, "high": 1.2}, "wbc": {"low": 4.5, "high": 11},
    "platelet": {"low": 150, "high": 400}, "triglycerides": {"low": 0, "high": 150},
    "cholesterol": {"low": 0, "high": 200},
}

def classify_metric(name: str, value: float) -> str:
    key = name.lower()
    for k, r in NORMAL_RANGES.items():
        if k in key:
            if value < r["low"]:  return "low"
            if value > r["high"]: return "high"
            return "normal"
    return "unknown"

def rec_dict(r):
    return {"id": r.id, "user_id": r.user_id, "record_type": r.record_type, "title": r.title,
            "doctor_name": r.doctor_name, "hospital_name": r.hospital_name,
            "file_url": r.file_url, "raw_text": None, "extracted_data": r.extracted_data,
            "source": r.source, "status": r.status,
            "record_date": r.record_date.isoformat() if r.record_date else None,
            "created_at": r.created_at.isoformat()}

def alert_dict(a):
    return {"id": a.id, "user_id": a.user_id, "alert_type": a.alert_type,
            "message": a.message, "source_metric": a.source_metric,
            "is_read": a.is_read, "created_at": a.created_at.isoformat()}

def metric_dict(m):
    return {"id": m.id, "user_id": m.user_id, "record_id": m.record_id,
            "metric_name": m.metric_name, "value": m.value, "unit": m.unit,
            "status": m.status, "recorded_at": m.recorded_at.isoformat()}

# ══ ROUTES — specific paths BEFORE /{record_id} ═══════════════

@router.get("/dashboard/stats")
def dashboard_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    uid     = current_user.id
    total   = db.query(models.MedicalRecord).filter_by(user_id=uid).count()
    pending = db.query(models.MedicalRecord).filter_by(user_id=uid, status="pending").count()
    unread  = db.query(models.Alert).filter_by(user_id=uid, is_read=False).count()
    recent_records  = db.query(models.MedicalRecord).filter_by(user_id=uid).order_by(models.MedicalRecord.created_at.desc()).limit(5).all()
    recent_alerts   = db.query(models.Alert).filter_by(user_id=uid).order_by(models.Alert.created_at.desc()).limit(3).all()
    latest_metrics  = db.query(models.HealthMetric).filter_by(user_id=uid).order_by(models.HealthMetric.recorded_at.desc()).limit(6).all()
    normal_count    = sum(1 for m in latest_metrics if m.status == "normal")
    health_score    = int(50 + (normal_count / (len(latest_metrics) or 1)) * 50)
    return {"total_records": total, "pending_followups": pending, "health_score": health_score,
            "active_alerts": unread, "recent_records": [rec_dict(r) for r in recent_records],
            "recent_alerts": [alert_dict(a) for a in recent_alerts],
            "latest_metrics": [metric_dict(m) for m in latest_metrics]}

@router.post("/upload", response_model=schemas.RecordOut)
async def upload_record(
    file: UploadFile = File(...), record_type: str = Form("lab"),
    title: str = Form("Uploaded Record"), doctor_name: Optional[str] = Form(None),
    hospital_name: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_bytes = await file.read()
    safe_name  = f"{current_user.id}_{datetime.datetime.utcnow().timestamp()}_{file.filename}"
    file_path  = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    raw_text = run_ocr(file_bytes, file.filename)
    extracted = extract_and_summarize_record(raw_text)

    #raw_text   = run_ocr(file_bytes, file.filename)
    #extracted  = extract_data(raw_text)
    #analysis = generate_analysis(extracted.get("metrics", []))
    #summary = generate_record_summary(raw_text)

    #if not extracted:
     #   extracted = {}
    #extracted["summary"] = summary
    final_title = title if title != "Uploaded Record" else (extracted.get("doctor") or file.filename)
    record = models.MedicalRecord(
        user_id=current_user.id, record_type=record_type, title=final_title,
        doctor_name=doctor_name or extracted.get("doctor"), hospital_name=hospital_name,
        file_url=f"/uploads/{safe_name}", raw_text=raw_text, extracted_data=extracted,
        source="ocr", status="processed" if raw_text else "pending")
    db.add(record); db.commit(); db.refresh(record)
    for m in extracted.get("metrics", []):
        status = classify_metric(m["name"], m["value"])
        db.add(models.HealthMetric(user_id=current_user.id, record_id=record.id,
            metric_name=m["name"], value=m["value"], unit=m["unit"], status=status))
        if status in ("high", "low"):
            db.add(models.Alert(user_id=current_user.id, alert_type="warning",
                message=f"{m['name']} is {status} at {m['value']} {m['unit']}. Please consult your doctor.",
                source_metric=m["name"]))
            
    for m in extracted.get("metrics", []):
        if m.get("name") is None or m.get("value") is None:
            continue

        status = classify_metric(m["name"], m["value"])
        db.add(models.HealthMetric(
            user_id=current_user.id,
            record_id=record.id,
            metric_name=m["name"],
            value=m["value"],
            unit=m.get("unit"),
            status=status
        ))
    db.commit()
    return {
    "id": record.id,
    "user_id": record.user_id,
    "record_type": record.record_type,
    "title": record.title,
    "doctor_name": record.doctor_name,
    "hospital_name": record.hospital_name,
    "file_url": record.file_url,
    "raw_text": record.raw_text,
    "extracted_data": record.extracted_data,
    "source": record.source,
    "status": record.status,
    "record_date": record.record_date,
    "created_at": record.created_at
    }




@router.get("/", response_model=List[schemas.RecordOut])
def get_records(record_type: Optional[str] = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.MedicalRecord).filter(models.MedicalRecord.user_id == current_user.id)
    if record_type:
        q = q.filter(models.MedicalRecord.record_type == record_type)
    return q.order_by(models.MedicalRecord.created_at.desc()).all()

@router.post("/", response_model=schemas.RecordOut, status_code=201)
def create_record(payload: schemas.RecordCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = models.MedicalRecord(user_id=current_user.id, record_type=payload.record_type,
        title=payload.title, doctor_name=payload.doctor_name, hospital_name=payload.hospital_name,
        record_date=payload.record_date, source=payload.source or "manual", status="processed")
    db.add(record); db.commit(); db.refresh(record)
    return record

@router.get("/{record_id}", response_model=schemas.RecordOut)
def get_record(record_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.id == record_id, models.MedicalRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.id == record_id, models.MedicalRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.file_url:
        local = record.file_url.lstrip("/")
        if os.path.exists(local):
            os.remove(local)
    db.delete(record); db.commit()

def generate_analysis(metrics):
    if not metrics:
        return "No medical metrics detected."

    messages = []

    for m in metrics:
        status = classify_metric(m["name"], m["value"])

        if status == "high":
            messages.append(f"{m['name']} is high.")
        elif status == "low":
            messages.append(f"{m['name']} is low.")
        elif status == "normal":
            messages.append(f"{m['name']} is normal.")

    return " ".join(messages)
