"""Service for persisting and loading valuation audit trails."""

from __future__ import annotations

import json

import structlog

from ..config.settings import settings
from ..models.audit import ValuationResult

logger = structlog.get_logger(__name__)


class AuditPersistence:
    """Handles persistence and retrieval of valuation audit trails."""

    def persist(self, result: ValuationResult) -> None:
        """Save a valuation result to disk as JSON."""
        settings.absolute_audit_trail_dir.mkdir(parents=True, exist_ok=True)
        path = settings.absolute_audit_trail_dir / f"{result.request_id}.json"
        payload = result.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        logger.info("audit.persisted", request_id=result.request_id, path=str(path))

    def load(self, request_id: str) -> ValuationResult | None:
        """Load a previously generated valuation result from disk."""
        path = settings.absolute_audit_trail_dir / f"{request_id}.json"
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        return ValuationResult.model_validate(data)
