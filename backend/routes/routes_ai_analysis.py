from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth_utils import get_current_user
from ai_analysis import generate_health_ai_summary
import models

router = APIRouter()


@router.post("/generate")
def generate_ai_analysis(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        metrics = (
            db.query(models.HealthMetric)
            .filter(models.HealthMetric.user_id == current_user.id)
            .order_by(models.HealthMetric.recorded_at.desc())
            .all()
        )

        records = (
            db.query(models.MedicalRecord)
            .filter(models.MedicalRecord.user_id == current_user.id)
            .order_by(models.MedicalRecord.created_at.desc())
            .all()
        )

        user_profile = {
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
            "dob": str(current_user.dob) if current_user.dob else None,
            "blood_group": current_user.blood_group,
            "gender": current_user.gender,
            "plan": current_user.plan,
        }

        metrics_data = [
            {
                "metric_name": m.metric_name,
                "value": m.value,
                "unit": m.unit,
                "status": m.status,
                "recorded_at": str(m.recorded_at),
            }
            for m in metrics
        ]

        records_data = [
            {
                "title": r.title,
                "record_type": r.record_type,
                "doctor_name": r.doctor_name,
                "hospital_name": r.hospital_name,
                "status": r.status,
                "record_date": str(r.record_date) if r.record_date else None,
                "created_at": str(r.created_at),
                "extracted_data": r.extracted_data,
                "raw_text": (r.raw_text[:1000] if r.raw_text else None),
            }
            for r in records
        ]

        analysis = generate_health_ai_summary(
            user_profile=user_profile,
            metrics=metrics_data,
            records=records_data,
        )

        return {"analysis": analysis}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")