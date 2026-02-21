"""Audit logging for sensitive operations."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from aim.config.settings import get_settings
from aim.data_layer.database import Database

_LAST_PURGE_AT: datetime | None = None
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|token|secret|authorization|api[_-]?key|email|cpf|phone)",
    re.IGNORECASE,
)


def ensure_audit_schema(db: Database) -> None:
    """Create audit table and indexes if missing."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER,
            event_type VARCHAR(80) NOT NULL,
            severity VARCHAR(20) DEFAULT 'INFO',
            message TEXT NOT NULL,
            ip_address VARCHAR(80),
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON audit_events(tenant_id, created_at DESC)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_user_created ON audit_events(user_id, created_at DESC)"
    )


def purge_old_audit_events(db: Database, *, force: bool = False) -> int:
    """Delete old audit records according to retention policy."""
    global _LAST_PURGE_AT
    settings = get_settings()
    interval = max(1, int(settings.audit_purge_interval_minutes))
    retention_days = max(1, int(settings.audit_retention_days))

    now = datetime.utcnow()
    if (
        not force
        and _LAST_PURGE_AT is not None
        and now - _LAST_PURGE_AT < timedelta(minutes=interval)
    ):
        return 0

    ensure_audit_schema(db)
    with db.transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM audit_events WHERE datetime(created_at) < datetime('now', ?)",
            (f"-{retention_days} day",),
        )
        deleted = int(cursor.rowcount or 0)
    _LAST_PURGE_AT = now
    return deleted


def log_audit_event(
    db: Database,
    *,
    tenant_id: int,
    user_id: Optional[int],
    event_type: str,
    message: str,
    severity: str = "INFO",
    ip_address: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Persist an audit event. This should never break main flow."""
    try:
        ensure_audit_schema(db)
        masked_metadata = _mask_metadata(metadata) if metadata else None
        db.insert(
            "audit_events",
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "event_type": event_type,
                "severity": severity,
                "message": message,
                "ip_address": _mask_ip_address(ip_address),
                "metadata": json.dumps(masked_metadata, ensure_ascii=False) if masked_metadata else None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
    except Exception:
        # Audit failure must not block business flow.
        pass


def _mask_ip_address(ip_address: Optional[str]) -> Optional[str]:
    if not ip_address:
        return None
    if ":" in ip_address:
        parts = ip_address.split(":")
        if len(parts) > 2:
            return ":".join(parts[:4]) + "::"
        return ip_address
    parts = ip_address.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3] + ["x"])
    return ip_address


def _mask_email(value: str) -> str:
    if "@" not in value:
        return "***"
    local, domain = value.split("@", 1)
    visible = local[:2] if len(local) >= 2 else local[:1]
    return f"{visible}***@{domain}"


def _mask_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if "@" in text and "." in text.split("@")[-1]:
        return _mask_email(text)
    if len(text) <= 4:
        return "***"
    return text[:2] + "***"


def _mask_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in metadata.items():
        if _SENSITIVE_KEY_PATTERN.search(key):
            masked[key] = _mask_value(value)
            continue
        if isinstance(value, dict):
            masked[key] = _mask_metadata(value)
        elif isinstance(value, list):
            masked[key] = [
                _mask_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    return masked
