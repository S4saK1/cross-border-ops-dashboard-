from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit import AuditLog
from app.core.deps import require_admin
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str = Query(None),
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    logger.info(f"Audit logs queried by {current_user.id}, count={total}")
    return {
        "items": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "action": i.action,
                "resource_type": i.resource_type,
                "resource_id": i.resource_id,
                "details": i.details,
                "ip_address": i.ip_address,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
