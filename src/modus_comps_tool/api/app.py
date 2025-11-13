from __future__ import annotations

import json
from fastapi import Depends, FastAPI, HTTPException

from ..config.settings import settings
from ..services.data_fetcher import CompanyDataFetcher
from ..services.valuation_service import ValuationService
from ..utils.logging import configure_logging
from .schemas import ValuationRequestPayload, ValuationResponse, ValuationSummaryResponse

# FastAPI app setup
configure_logging(settings.log_level)
app = FastAPI(
    title="Modus Comparable Company Valuation API",
    version="0.1.0",
    description="Generate auditable valuations for private illiquidcompanies using comparable public peers with a focus on revenue and ebitda multiples.",
)

# Singleton instance for Data Fetcher shared across all requests to maintain in-memory cache
_data_fetcher = CompanyDataFetcher()


def get_valuation_service() -> ValuationService:
    """Provide a service instance with shared data fetcher for cache efficiency."""
    return ValuationService(data_fetcher=_data_fetcher)


@app.get("/peer-sectors")
async def list_peer_sectors() -> dict[str, list[str]]:
    """Return the sector keys available in the peer universe to make it easier for the user to select the appropriate sector."""
    path = settings.absolute_peer_universe_path
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    sectors = sorted(data.keys())
    return {"sectors": sectors}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health endpoint used by monitors and smoke tests to check if the API is running."""
    return {"status": "ok"}


@app.post("/valuations", response_model=ValuationSummaryResponse, status_code=201)
async def create_valuation(
    payload: ValuationRequestPayload,
    service: ValuationService = Depends(get_valuation_service),
) -> ValuationSummaryResponse:
    """Run the valuation workflow and return the summary of the valuation analysis."""
    result = service.valuate(payload)
    return ValuationSummaryResponse.from_domain(result)


@app.get("/valuations/{request_id}", response_model=ValuationResponse)
async def get_valuation(
    request_id: str,
    service: ValuationService = Depends(get_valuation_service),
) -> ValuationResponse:
    """Retrieve a previously generated valuation run's audit trail to get the full details of the valuation analysis."""
    result = service.load_result(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return ValuationResponse.from_domain(result)

