import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def write_audit_log(
    db: Session,
    actor_id: str,
    action: str,
    subject_type: str,
    subject_id: str,
    before: dict | None = None,
    after: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """统一审计日志写入。不自行 commit，由调用方在 db.commit() 前调用。"""
    details = {
        "before": before,
        "after": after,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        entry = AuditLog(
            user_id=actor_id,
            action=action,
            resource_type=subject_type,
            resource_id=subject_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
