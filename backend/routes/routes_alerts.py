# routes/alerts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AlertOut])
def get_alerts(
    current_user: models.User = Depends(get_current_user),
    db: Session               = Depends(get_db)
):
    return (
        db.query(models.Alert)
          .filter_by(user_id=current_user.id)
          .order_by(models.Alert.created_at.desc())
          .all()
    )

@router.put("/{alert_id}/read")
def mark_read(
    alert_id:     int,
    current_user: models.User = Depends(get_current_user),
    db: Session               = Depends(get_db)
):
    alert = db.query(models.Alert).filter_by(
        id=alert_id, user_id=current_user.id
    ).first()
    if alert:
        alert.is_read = True
        db.commit()
    return {"status": "ok"}

@router.delete("/{alert_id}")
def delete_alert(
    alert_id:     int,
    current_user: models.User = Depends(get_current_user),
    db: Session               = Depends(get_db)
):
    alert = db.query(models.Alert).filter_by(
        id=alert_id, user_id=current_user.id
    ).first()
    if alert:
        db.delete(alert)
        db.commit()
    return {"status": "deleted"}
