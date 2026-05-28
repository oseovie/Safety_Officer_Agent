from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import IncidentSeverity, RecordStatus, RiskLevel


class TenantScoped:
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)


class Incident(TenantScoped, Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(180), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default=IncidentSeverity.NEAR_MISS.value)
    status: Mapped[str] = mapped_column(String(40), default=RecordStatus.OPEN.value)
    reported_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Hazard(TenantScoped, Base):
    __tablename__ = "hazards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="other")
    likelihood: Mapped[int] = mapped_column(Integer, default=3)
    severity: Mapped[int] = mapped_column(Integer, default=3)
    risk_score: Mapped[int] = mapped_column(Integer, default=9)
    risk_level: Mapped[str] = mapped_column(String(40), default=RiskLevel.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(40), default=RecordStatus.OPEN.value)
    controls: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Inspection(TenantScoped, Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    site: Mapped[str] = mapped_column(String(180), nullable=False)
    checklist: Mapped[list] = mapped_column(JSON, default=list)
    responses: Mapped[dict] = mapped_column(JSON, default=dict)
    offline_sync_id: Mapped[str | None] = mapped_column(String(80), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default=RecordStatus.OPEN.value)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CorrectiveAction(TenantScoped, Base):
    __tablename__ = "corrective_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(40), default=RiskLevel.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(40), default=RecordStatus.OPEN.value)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Document(TenantScoped, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmployeeProfile(TenantScoped, Base):
    __tablename__ = "employee_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    employee_number: Mapped[str] = mapped_column(String(80), index=True)
    trade: Mapped[str] = mapped_column(String(120), default="")
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    medical_clearances: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Audit(TenantScoped, Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    framework: Mapped[str] = mapped_column(String(120), default="ISO 45001")
    scope: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default=RecordStatus.OPEN.value)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(TenantScoped, Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    channel: Mapped[str] = mapped_column(String(40), default="in_app")
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
