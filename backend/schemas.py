from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import date, datetime


# ── Auth ──────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name:        str
    email:       str
    password:    str
    phone:       Optional[str] = None
    dob:         Optional[date] = None
    blood_group: Optional[str] = None
    gender:      Optional[str] = None

class LoginRequest(BaseModel):
    email:    str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    name:         str
    email:        str

class UserOut(BaseModel):
    id:          int
    name:        str
    email:       str
    phone:       Optional[str]
    dob:         Optional[date]
    blood_group: Optional[str]
    gender:      Optional[str]
    plan:        str
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Records ───────────────────────────────────────────────────
class RecordCreate(BaseModel):
    record_type:   str
    title:         str
    doctor_name:   Optional[str] = None
    hospital_name: Optional[str] = None
    record_date:   Optional[date] = None
    source:        Optional[str] = "manual"

class RecordOut(BaseModel):
    id:             int
    user_id:        int
    record_type:    str
    title:          str
    doctor_name:    Optional[str]
    hospital_name:  Optional[str]
    file_url:       Optional[str]
    raw_text:       Optional[str]
    extracted_data: Optional[Any]
    source:         str
    status:         str
    record_date:    Optional[date]
    created_at:     datetime

    class Config:
        from_attributes = True


# ── Metrics ───────────────────────────────────────────────────
class MetricCreate(BaseModel):
    metric_name: str
    value:       float
    unit:        Optional[str] = None
    record_id:   Optional[int] = None

class MetricOut(BaseModel):
    id:          int
    user_id:     int
    record_id:   Optional[int]
    metric_name: str
    value:       float
    unit:        Optional[str]
    status:      Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


# ── Alerts ────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id:            int
    user_id:       int
    alert_type:    str
    message:       str
    source_metric: Optional[str]
    is_read:       bool
    created_at:    datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_records:    int
    pending_followups: int
    health_score:     int
    active_alerts:    int
    recent_records:   List[RecordOut]
    recent_alerts:    List[AlertOut]
    latest_metrics:   List[MetricOut]

class AnalysisOut(BaseModel):
    id: int
    user_id: int
    overall_summary: Optional[str]
    current_risks: Optional[List[str]]
    repeated_findings: Optional[List[str]]
    missing_data: Optional[List[str]]
    updated_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    record: RecordOut
    analysis: str
    metrics: List[Any]