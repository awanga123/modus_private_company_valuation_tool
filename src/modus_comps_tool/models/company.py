from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveFloat


class TargetCompany(BaseModel):
    name: str
    revenue: PositiveFloat = Field(description="Annual revenue in USD")
    ticker: str | None = Field(default=None, description="Ticker if public, else null")
    ebitda: float | None = Field(default=None, description="EBITDA in USD, may be negative")
    net_income: float | None = Field(default=None, description="Net income in USD, may be negative")
    industry: str | None = None
    sector: str | None = None
    sic_code: str | None = Field(default=None, max_length=10)
    founded_year: NonNegativeInt | None = None
    business_model: str | None = None


class PeerFilters(BaseModel):
    revenue_range: tuple[float, float] | None = (200_000_000, 2_000_000_000) # $100M - $2B in revenue for default range if not specificed 
    exclude_negative_ebitda: bool = True
    saas_only: bool = False 
    focus_fashion_only: bool = False


class PeerSelectionConfig(BaseModel):
    method: str = Field(default="industry_based")
    custom_tickers: list[str] = Field(default_factory=list)
    filters: PeerFilters = Field(default_factory=PeerFilters)


class ValuationConfig(BaseModel):
    multiples: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=lambda: ["median"])
    apply_dlom: bool = False
    dlom_percentage: float = 0.10 # 10% default discount for lack of marketability if not specified if apply_dlom is true


class ValuationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_company: TargetCompany
    peer_selection: PeerSelectionConfig | None = Field(default=None, description="Optional peer selection config, defaults will be used if not provided")
    valuation_config: ValuationConfig | None = Field(default=None, description="Optional valuation config, defaults will be used if not provided")

