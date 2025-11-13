from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional

import structlog
from fastmcp import FastMCP

from .config.settings import settings
from .models.company import (
    PeerSelectionConfig,
    TargetCompany,
    ValuationConfig,
    ValuationRequest,
)
from .models.valuation_multiple import DEFAULT_MULTIPLES
from .services.valuation_service import ValuationService

# Configure logging for MCP server: write to stderr to keep stdout clean for JSON-RPC
# MCP protocol requires clean JSON-RPC output on stdout
logging.basicConfig(
    stream=sys.stderr,
    format="%(message)s",
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def _build_service() -> ValuationService:
    """Create a valuation service instance."""
    return ValuationService()


def _load_peer_universe() -> dict[str, Any]:
    """Load the peer universe JSON file."""
    path = settings.absolute_peer_universe_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


app = FastMCP(
    name="modus-comps-mcp",
    instructions=(
        "Provides comparable company valuations and sector metadata from the Modus "
        "Comps tool. Use the create_valuation tool to run a new valuation or "
        "get_valuation to retrieve a stored audit trail."
    ),
)


@app.tool(
    name="create_valuation",
    description=(
        "Run a comparable company valuation for a private company. "
        "Requires company name and revenue; sector and industry help with peer selection."
    ),
)
def create_valuation(
    name: str,
    revenue: float,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    custom_tickers: Optional[List[str]] = None,
    apply_dlom: bool = False,
    dlom_percentage: float = 0.0,
) -> dict[str, Any]:
    """
    Create a new valuation using the Modus comps pipeline.

    Args:
        name: Name of the private company.
        revenue: Latest annual revenue in USD.
        sector: Optional sector to guide peer selection.
        industry: Optional industry to guide peer selection.
        custom_tickers: Optional list of specific public peers to include.
        apply_dlom: Whether to apply a discount for lack of marketability.
        dlom_percentage: Percentage for the DLOM adjustment when enabled.
    """
    service = _build_service()

    valuation_request = ValuationRequest(
        target_company=TargetCompany(
            name=name,
            ticker=None,
            revenue=revenue,
            ebitda=None,
            net_income=None,
            industry=industry,
            sector=sector,
        ),
        peer_selection=PeerSelectionConfig(
            method="industry_based",
            custom_tickers=custom_tickers or [],
        ),
        valuation_config=ValuationConfig(
            multiples=[multiple.value for multiple in DEFAULT_MULTIPLES],
            statistics=["median", "mean"],
            apply_dlom=apply_dlom,
            dlom_percentage=dlom_percentage,
        ),
    )

    result = service.valuate(valuation_request)

    return {
        "request_id": result.request_id,
        "valuation_summary": result.valuation_summary,
        "peer_analysis": result.peer_analysis,
        "multiple_analysis": {
            key: analysis.model_dump()
            for key, analysis in result.multiple_analysis.items()
        },
        "adjustments": result.adjustments,
        "audit_summary": result.audit_trail.model_dump(),
        "metadata": result.metadata,
    }


@app.tool(
    name="get_valuation",
    description="Retrieve a previously generated valuation by request ID.",
)
def get_valuation(request_id: str) -> dict[str, Any]:
    """Fetch a stored valuation result and audit trail."""
    service = _build_service()
    result = service.load_result(request_id)
    if result is None:
        return {
            "request_id": request_id,
            "status": "not_found",
            "message": "No valuation stored for the provided request_id.",
        }

    return result.model_dump()


@app.tool(
    name="list_peer_sectors",
    description="List the available sector names from the peer universe.",
)
def list_peer_sectors() -> dict[str, Any]:
    """Return the sector keys present in peer_universe.json."""
    data = _load_peer_universe()
    sectors = sorted(data.keys())
    return {"sectors": sectors}


if __name__ == "__main__":
    app.run(show_banner=False)

