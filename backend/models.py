from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    dob           = Column(Date, nullable=True)
    blood_group   = Column(String(5), nullable=True)
    phone         = Column(String(15), nullable=True)
    gender        = Column(String(10), nullable=True)
    plan          = Column(String(20), default="free")
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

    records = relationship("MedicalRecord", back_populates="user", cascade="all, delete")
    metrics = relationship("HealthMetric",  back_populates="user", cascade="all, delete")
    alerts  = relationship("Alert",         back_populates="user", cascade="all, delete")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_type    = Column(String(30), nullable=False)   # prescription|lab|imaging|consultation
    title          = Column(String(200), nullable=False)
    doctor_name    = Column(String(100), nullable=True)
    hospital_name  = Column(String(150), nullable=True)
    file_url       = Column(String(500), nullable=True)   # local path or S3 URL
    raw_text       = Column(Text, nullable=True)          # full OCR text
    extracted_data = Column(JSON, nullable=True)          # structured NLP output
    source         = Column(String(30), default="manual") # manual|ocr|email
    status         = Column(String(20), default="pending") # pending|processed|review
    record_date    = Column(Date, nullable=True)
    created_at     = Column(DateTime, default=datetime.datetime.utcnow)

    user    = relationship("User", back_populates="records")
    metrics = relationship("HealthMetric", back_populates="record")


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_id   = Column(Integer, ForeignKey("medical_records.id"), nullable=True)
    metric_name = Column(String(100), nullable=False)
    value       = Column(Float, nullable=False)
    unit        = Column(String(30), nullable=True)
    status      = Column(String(20), nullable=True)   # normal|low|high|critical
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    user   = relationship("User",          back_populates="metrics")
    record = relationship("MedicalRecord", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_type    = Column(String(20), nullable=False)   # critical|warning|info
    message       = Column(Text, nullable=False)
    source_metric = Column(String(100), nullable=True)
    is_read       = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="alerts")

class PatientAnalysis(Base):
    __tablename__ = "patient_analysis"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    overall_summary   = Column(Text, nullable=True)
    current_risks     = Column(JSON, nullable=True)      # ["anemia", "cholesterol"]
    repeated_findings = Column(JSON, nullable=True)      # ["Low hemoglobin in multiple reports"]
    missing_data      = Column(JSON, nullable=True)      # ["blood group", "recent sugar report"]
    updated_at        = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
