# routes/metrics.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.MetricOut])
def get_metrics(
    current_user: models.User = Depends(get_current_user),
    db: Session               = Depends(get_db)
):
    return (
        db.query(models.HealthMetric)
          .filter_by(user_id=current_user.id)
          .order_by(models.HealthMetric.recorded_at.desc())
          .all()
    )

@router.post("/", response_model=schemas.MetricOut, status_code=201)
def add_metric(
    payload: schemas.MetricCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from routes.routes_records import classify_metric
    status = classify_metric(payload.metric_name, payload.value)

    metric = models.HealthMetric(
        user_id=current_user.id,
        record_id=payload.record_id,
        metric_name=payload.metric_name,
        value=payload.value,
        unit=payload.unit,
        status=status,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)

    if status in ("high", "low", "critical"):
        level = "critical" if status == "critical" else "warning"
        message = f"{payload.metric_name} is {status} at {payload.value} {payload.unit or ''}."
        alert = models.Alert(
            user_id=current_user.id,
            alert_type=level,
            message=message,
            source_metric=payload.metric_name,
        )
        db.add(alert)
        db.commit()

    return metric

@router.get("/trend/{metric_name}")
def get_trend(
    metric_name:  str,
    current_user: models.User = Depends(get_current_user),
    db: Session               = Depends(get_db)
):
    rows = (
        db.query(models.HealthMetric)
          .filter_by(user_id=current_user.id, metric_name=metric_name)
          .order_by(models.HealthMetric.recorded_at.asc())
          .limit(12).all()
    )
    return [{"date": r.recorded_at, "value": r.value, "unit": r.unit} for r in rows]
