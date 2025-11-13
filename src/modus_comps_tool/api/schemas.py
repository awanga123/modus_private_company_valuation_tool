from __future__ import annotations

from pydantic import BaseModel

from ..models.audit import ValuationResult
from ..models.company import ValuationRequest


class ValuationRequestPayload(ValuationRequest):
    """API payload schema for launching a valuation."""


class ValuationSummaryResponse(BaseModel):
    """Lightweight response returned by POST /valuations."""

    request_id: str
    valuation_summary: dict
    peer_analysis: dict
    multiple_analysis: dict
    adjustments: dict
    audit_summary: list[str]
    metadata: dict

    @classmethod
    def from_domain(cls, result: ValuationResult) -> "ValuationSummaryResponse":
        return cls(
            request_id=result.request_id,
            valuation_summary=result.valuation_summary,
            peer_analysis=result.peer_analysis,
            multiple_analysis={key: value.model_dump() for key, value in result.multiple_analysis.items()},
            adjustments=result.adjustments,
            audit_summary=[step.description for step in result.audit_trail.calculation_steps],
            metadata=result.metadata,
        )


class ValuationResponse(BaseModel):
    """Detailed response wrapper returned by GET /valuations/{id}."""

    request_id: str
    valuation_summary: dict
    peer_analysis: dict
    multiple_analysis: dict
    adjustments: dict
    audit_trail: dict
    metadata: dict

    @classmethod
    def from_domain(cls, result: ValuationResult) -> "ValuationResponse":
        return cls.model_validate(result.model_dump())

