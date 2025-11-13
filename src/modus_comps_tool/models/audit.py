from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Base model for the audit trail to keep track of the steps and data associated with each step.
# pretty generic model, to be extended for different use cases and logics and methodologies. 
class AuditCalculationStep(BaseModel):
    description: str
    data: dict[str, Any] = Field(default_factory=dict)


# Every Audit Trail will be associated with a request id and a valuation date.
# We will build the audit trail step by step as we go through the valuation process. 
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

# Base model for each multiple analysis to keep track of the values and statistics associated with each multiple.
# This is used to store the multiple analysis for each multiple type (EV_REVENUE, EV_EBITDA, etc.) Easy to add new types of 
# multiples and placing the results in the same model.
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


# Final model for the valuation result to return to the client, which is translated into the API response schema in schemas.py
class ValuationResult(BaseModel):
    request_id: str
    valuation_summary: dict[str, Any]
    peer_analysis: dict[str, Any]
    multiple_analysis: dict[str, ValuationMultipleAnalysis]
    adjustments: dict[str, Any]
    audit_trail: AuditTrail
    metadata: dict[str, Any] = Field(default_factory=dict)

