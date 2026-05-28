from app.core.celery_app import celery_app


@celery_app.task
def notify_high_risk(tenant_id: str, hazard_id: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "hazard_id": hazard_id, "status": "queued"}


@celery_app.task
def generate_audit_pack(tenant_id: str, audit_id: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "audit_id": audit_id, "status": "audit_pack_requested"}


@celery_app.task
def send_due_action_reminders() -> dict[str, str]:
    return {"status": "reminders_scanned"}
