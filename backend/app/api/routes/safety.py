from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, require_tenant
from app.db.session import get_db
from app.models.safety import Audit, CorrectiveAction, Document, EmployeeProfile, Hazard, Incident, Inspection
from app.models.user import User
from app.schemas.safety import ActionCreate, AuditCreate, EmployeeCreate, HazardCreate, IncidentCreate, InspectionCreate
from app.services.risk_ai import assess_risk, portfolio_insights
from app.services.storage import upload_document
from app.tasks.worker import generate_audit_pack, notify_high_risk


router = APIRouter(tags=["safety"])


@router.post("/incidents", dependencies=[Depends(require_permission("incident:write"))], status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant), user: User = Depends(get_current_user)):
    incident = Incident(tenant_id=tenant_id, reported_by_id=user.id, **payload.model_dump(exclude_none=True))
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    return db.scalars(select(Incident).where(Incident.tenant_id == tenant_id).order_by(Incident.created_at.desc())).all()


@router.post("/hazards", dependencies=[Depends(require_permission("hazard:write"))], status_code=201)
def create_hazard(payload: HazardCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    assessment = assess_risk(payload.title, payload.description, payload.likelihood, payload.severity)
    hazard = Hazard(
        tenant_id=tenant_id,
        **payload.model_dump(),
        category=assessment.category,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        controls=assessment.controls,
    )
    db.add(hazard)
    db.commit()
    db.refresh(hazard)
    if hazard.risk_level in {"high", "critical"}:
        notify_high_risk.delay(tenant_id, hazard.id)
    return {"hazard": hazard, "ai_insight": assessment.narrative}


@router.get("/hazards")
def list_hazards(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    return db.scalars(select(Hazard).where(Hazard.tenant_id == tenant_id).order_by(Hazard.created_at.desc())).all()


@router.post("/inspections", dependencies=[Depends(require_permission("inspection:write"))], status_code=201)
def create_inspection(payload: InspectionCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    total = max(len(payload.checklist), 1)
    passed = sum(1 for value in payload.responses.values() if value is True)
    inspection = Inspection(tenant_id=tenant_id, score=round((passed / total) * 100, 2), **payload.model_dump())
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("/inspections")
def list_inspections(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    return db.scalars(select(Inspection).where(Inspection.tenant_id == tenant_id).order_by(Inspection.created_at.desc())).all()


@router.post("/actions", dependencies=[Depends(require_permission("action:write"))], status_code=201)
def create_action(payload: ActionCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    action = CorrectiveAction(tenant_id=tenant_id, **payload.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@router.get("/actions")
def list_actions(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    return db.scalars(select(CorrectiveAction).where(CorrectiveAction.tenant_id == tenant_id).order_by(CorrectiveAction.created_at.desc())).all()


@router.post("/documents", dependencies=[Depends(require_permission("document:write"))], status_code=201)
async def create_document(title: str, document_type: str, file: UploadFile = File(...), db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    try:
        object_key, content_type = await upload_document(tenant_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    document = Document(tenant_id=tenant_id, title=title, document_type=document_type, object_key=object_key, content_type=content_type)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/employees", dependencies=[Depends(require_permission("employee:write"))], status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    employee = EmployeeProfile(tenant_id=tenant_id, **payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/audits", dependencies=[Depends(require_permission("audit:write"))], status_code=201)
def create_audit(payload: AuditCreate, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    audit = Audit(tenant_id=tenant_id, **payload.model_dump())
    db.add(audit)
    db.commit()
    db.refresh(audit)
    generate_audit_pack.delay(tenant_id, audit.id)
    return audit


@router.get("/dashboard", dependencies=[Depends(require_permission("analytics:read"))])
def dashboard(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    hazards = db.scalars(select(Hazard).where(Hazard.tenant_id == tenant_id)).all()
    open_actions = db.scalar(select(func.count()).select_from(CorrectiveAction).where(CorrectiveAction.tenant_id == tenant_id, CorrectiveAction.status != "closed"))
    records = [hazard.__dict__ for hazard in hazards if hazard.status != "closed"]
    return {
        "metrics": {
            "open_hazards": len(records),
            "open_actions": open_actions,
            "critical_hazards": sum(1 for hazard in hazards if hazard.risk_level == "critical"),
            "average_risk_score": round(sum(h.risk_score for h in hazards) / max(len(hazards), 1), 1),
        },
        "risk_insights": portfolio_insights(records),
        "hazards_by_level": {level: sum(1 for h in hazards if h.risk_level == level) for level in ["low", "medium", "high", "critical"]},
    }
