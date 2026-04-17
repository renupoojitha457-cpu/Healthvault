from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models, auth_utils, schemas

router = APIRouter()


def generate_patient_analysis(user: models.User, db: Session):
    metrics = db.query(models.HealthMetric).filter(models.HealthMetric.user_id == user.id).all()
    records = db.query(models.MedicalRecord).filter(models.MedicalRecord.user_id == user.id).all()

    current_risks = []
    repeated_findings = []
    missing_data = []

    hemoglobin_values = []
    ldl_values = []
    sugar_values = []
    bp_values = []

    for m in metrics:
        name = m.metric_name.lower()

        if "hemoglobin" in name or "hb" == name.strip():
            hemoglobin_values.append(m.value)

        if "ldl" in name or "cholesterol" in name:
            ldl_values.append(m.value)

        if "glucose" in name or "sugar" in name or "hba1c" in name:
            sugar_values.append(m.value)

        if "blood pressure" in name or "bp" == name.strip():
            bp_values.append(m.value)

    # Rule-based findings
    if len([x for x in hemoglobin_values if x < 12]) >= 2:
        current_risks.append("Anemia Risk")
        repeated_findings.append("Low hemoglobin found in multiple reports")

    if len([x for x in ldl_values if x > 130]) >= 2:
        current_risks.append("Cholesterol Risk")
        repeated_findings.append("LDL / cholesterol repeatedly elevated")

    if len([x for x in sugar_values if x > 126]) >= 2:
        current_risks.append("Diabetes Risk")
        repeated_findings.append("Blood sugar trend is repeatedly high")

    if len(records) == 0:
        missing_data.append("No medical records uploaded yet")

    if not user.phone:
        missing_data.append("Phone number missing")

    if not user.dob:
        missing_data.append("Date of birth missing")

    if not user.blood_group:
        missing_data.append("Blood group missing")

    if not user.gender:
        missing_data.append("Gender missing")

    if len(metrics) == 0:
        missing_data.append("No health metrics available for analysis")

    if repeated_findings:
        overall_summary = " ; ".join(repeated_findings)
    elif len(records) > 0:
        overall_summary = "Records available, but no strong repeated abnormal trend detected yet."
    else:
        overall_summary = "Upload records to generate health analysis."

    return {
        "overall_summary": overall_summary,
        "current_risks": current_risks,
        "repeated_findings": repeated_findings,
        "missing_data": missing_data,
    }


@router.post("/generate", response_model=schemas.AnalysisOut)
def generate_analysis(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db)
):
    data = generate_patient_analysis(current_user, db)

    analysis = db.query(models.PatientAnalysis).filter(
        models.PatientAnalysis.user_id == current_user.id
    ).first()

    if analysis:
        analysis.overall_summary = data["overall_summary"]
        analysis.current_risks = data["current_risks"]
        analysis.repeated_findings = data["repeated_findings"]
        analysis.missing_data = data["missing_data"]
    else:
        analysis = models.PatientAnalysis(
            user_id=current_user.id,
            overall_summary=data["overall_summary"],
            current_risks=data["current_risks"],
            repeated_findings=data["repeated_findings"],
            missing_data=data["missing_data"],
        )
        db.add(analysis)

    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/", response_model=schemas.AnalysisOut)
def get_analysis(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(models.PatientAnalysis).filter(
        models.PatientAnalysis.user_id == current_user.id
    ).first()

    if not analysis:
        data = generate_patient_analysis(current_user, db)
        analysis = models.PatientAnalysis(
            user_id=current_user.id,
            overall_summary=data["overall_summary"],
            current_risks=data["current_risks"],
            repeated_findings=data["repeated_findings"],
            missing_data=data["missing_data"],
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    return analysis