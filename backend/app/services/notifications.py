from sqlalchemy.orm import Session

from app.models.safety import Notification
from app.services.common import save_model


def queue_notification(db: Session, tenant_id: str, recipient: str, subject: str, body: str) -> Notification:
    notification = Notification(tenant_id=tenant_id, recipient=recipient, subject=subject, body=body)
    return save_model(db, notification)
