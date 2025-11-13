from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Basic model for each peer company to store the basic information about the peer company. 
# Matches closely with the yfinance data model.
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


# Main model for the peer group to store the list of peers and the selection method and criteria.
# This is used to store the peer group for each valuation request. Although currently, the selection method 
# is only industry based, it is easy to extend to other selection methods. 
class PeerGroup(BaseModel):
    peers: list[PeerCompany] = Field(default_factory=list)
    selection_method: str
    selection_criteria: dict[str, Any] = Field(default_factory=dict)
    excluded_tickers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

