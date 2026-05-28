from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str
    description: str
    location: str
    severity: str = "near_miss"
    occurred_at: datetime | None = None


class HazardCreate(BaseModel):
    title: str
    description: str
    location: str
    category: str = "other"
    likelihood: int = Field(default=3, ge=1, le=5)
    severity: int = Field(default=3, ge=1, le=5)


class InspectionCreate(BaseModel):
    name: str
    site: str
    checklist: list[dict[str, Any]]
    responses: dict[str, Any] = {}
    offline_sync_id: str | None = None
    due_at: datetime | None = None


class ActionCreate(BaseModel):
    source_type: str
    source_id: str
    title: str
    owner_id: str | None = None
    priority: str = "medium"
    due_at: datetime | None = None


class EmployeeCreate(BaseModel):
    employee_number: str
    trade: str = ""
    certifications: list[dict[str, Any]] = []
    medical_clearances: list[dict[str, Any]] = []


class AuditCreate(BaseModel):
    title: str
    framework: str = "ISO 45001"
    scope: str = ""
    scheduled_at: datetime | None = None


class SafetyRecord(BaseModel):
    id: str
    model_config = {"from_attributes": True}
