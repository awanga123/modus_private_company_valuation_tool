from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveFloat, field_validator

from ..config.settings import settings


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
    revenue_range: tuple[float, float] | None = Field(
        default_factory=lambda: (settings.default_revenue_range_min, settings.default_revenue_range_max),
        description="Min and max annual revenue range for peer filtering",
    )
    exclude_negative_ebitda: bool = True
    saas_only: bool = False
    focus_fashion_only: bool = False

    @field_validator("revenue_range")
    @classmethod
    def validate_revenue_range(cls, v: tuple[float, float] | None) -> tuple[float, float] | None:
        """Ensure min revenue is less than max revenue."""
        if v is not None:
            min_val, max_val = v
            if min_val < 0 or max_val < 0:
                raise ValueError("Revenue range values must be non-negative")
            if min_val >= max_val:
                raise ValueError(f"Min revenue ({min_val:,.0f}) must be less than max revenue ({max_val:,.0f})")
        return v


class PeerSelectionConfig(BaseModel):
    method: str = Field(default="industry_based")
    custom_tickers: list[str] = Field(default_factory=list)
    filters: PeerFilters = Field(default_factory=PeerFilters)


class ValuationConfig(BaseModel):
    multiples: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=lambda: ["median"])
    apply_dlom: bool = False
    dlom_percentage: float = Field(
        default_factory=lambda: settings.default_dlom_percentage,
        description="Discount for lack of marketability, applied if apply_dlom is True",
    )


class ValuationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_company: TargetCompany
    peer_selection: PeerSelectionConfig | None = Field(default=None, description="Optional peer selection config, defaults will be used if not provided")
    valuation_config: ValuationConfig | None = Field(default=None, description="Optional valuation config, defaults will be used if not provided")

