from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission, require_tenant
from app.db.session import get_db
from app.models.safety import Hazard
from app.services.reports import build_excel_report, build_pdf_report


router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_permission("analytics:read"))])


@router.get("/risk-register.pdf")
def risk_pdf(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    hazards = db.scalars(select(Hazard).where(Hazard.tenant_id == tenant_id)).all()
    rows = [hazard.__dict__ for hazard in hazards]
    return Response(
        build_pdf_report("Safety Risk Register", rows),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="risk-register.pdf"'},
    )


@router.get("/risk-register.xlsx")
def risk_excel(db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)):
    hazards = db.scalars(select(Hazard).where(Hazard.tenant_id == tenant_id)).all()
    rows = [hazard.__dict__ for hazard in hazards]
    return Response(
        build_excel_report(rows),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="risk-register.xlsx"'},
    )
