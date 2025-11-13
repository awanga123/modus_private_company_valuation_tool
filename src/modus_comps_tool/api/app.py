from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from ..config.settings import settings
from ..services.data_fetcher import CompanyDataFetcher
from ..services.valuation_service import ValuationService
from ..utils.logging import configure_logging
from .schemas import ValuationRequestPayload, ValuationResponse, ValuationSummaryResponse


configure_logging(settings.log_level)
app = FastAPI(
    title="Modus Comparable Company Valuation API",
    version="0.1.0",
    description="Generate auditable valuations for private illiquidcompanies using comparable public peers with a focus on revenue and ebitda multiples.",
)

# Singleton instances shared across all requests to maintain in-memory cache
_data_fetcher = CompanyDataFetcher()


def get_valuation_service() -> ValuationService:
    """Provide a service instance with shared data fetcher for cache efficiency."""
    return ValuationService(data_fetcher=_data_fetcher)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health endpoint used by monitors and smoke tests."""
    return {"status": "ok"}


@app.post("/valuations", response_model=ValuationSummaryResponse, status_code=201)
async def create_valuation(
    payload: ValuationRequestPayload,
    service: ValuationService = Depends(get_valuation_service),
) -> ValuationSummaryResponse:
    """Run the valuation workflow and return the summary of the audit trail."""
    result = service.valuate(payload)
    return ValuationSummaryResponse.from_domain(result)


@app.get("/valuations/{request_id}", response_model=ValuationResponse)
async def get_valuation(
    request_id: str,
    service: ValuationService = Depends(get_valuation_service),
) -> ValuationResponse:
    """Retrieve a previously generated valuation run by its request id."""
    result = service.load_result(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return ValuationResponse.from_domain(result)

