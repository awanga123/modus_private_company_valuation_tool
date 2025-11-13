from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PeerCompany(BaseModel):
    ticker: str
    name: str | None = None
    industry: str | None = None
    sector: str | None = None
    subsector: str | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    ev_to_revenue: float | None = Field(default=None, description="Enterprise value divided by revenue")
    ev_to_ebitda: float | None = None
    data_timestamp: datetime | None = None
    raw_source: dict[str, Any] | None = Field(default=None, exclude=True)


class PeerGroup(BaseModel):
    peers: list[PeerCompany] = Field(default_factory=list)
    selection_method: str
    selection_criteria: dict[str, Any] = Field(default_factory=dict)
    excluded_tickers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

