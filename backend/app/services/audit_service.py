from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent


async def log_event(
    db: AsyncSession,
    action: str,
    actor_user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event
