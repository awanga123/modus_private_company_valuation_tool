from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditCalculationStep(BaseModel):
    description: str
    data: dict[str, Any] = Field(default_factory=dict)


class AuditTrail(BaseModel):
    request_id: str
    valuation_date: datetime
    assumptions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    calculation_steps: list[AuditCalculationStep] = Field(default_factory=list)
    data_sources: dict[str, Any] = Field(default_factory=dict)


    def add_step(self, description: str, data: dict[str, Any] | None = None) -> None:
        """Helper method to easily add a calculation step to the audit trail."""
        self.calculation_steps.append(
            AuditCalculationStep(
                description=description,
                data=data or {},
            )
        )

class ValuationMultipleAnalysis(BaseModel):
    values: list[float] = Field(default_factory=list)
    mean: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    std_dev: float | None = None
    outliers_excluded: list[str] = Field(default_factory=list)
    target_metric: float | None = None
    implied_values: dict[str, float] = Field(default_factory=dict)


class ValuationResult(BaseModel):
    request_id: str
    valuation_summary: dict[str, Any]
    peer_analysis: dict[str, Any]
    multiple_analysis: dict[str, ValuationMultipleAnalysis]
    adjustments: dict[str, Any]
    audit_trail: AuditTrail
    metadata: dict[str, Any] = Field(default_factory=dict)

