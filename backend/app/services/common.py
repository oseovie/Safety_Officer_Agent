from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


def save_model(db: Session, model: ModelT, *, flush: bool = False) -> ModelT:
    """Persist a SQLAlchemy model with one consistent path for create flows."""
    db.add(model)
    if flush:
        db.flush()
        return model
    db.commit()
    db.refresh(model)
    return model


def list_tenant_models(db: Session, model_cls: type[ModelT], tenant_id: str, *, order_by=None) -> list[ModelT]:
    """List tenant-scoped records with the existing ordering pattern in one place."""
    query = select(model_cls).where(model_cls.tenant_id == tenant_id)
    if order_by is not None:
        query = query.order_by(order_by)
    return db.scalars(query).all()
