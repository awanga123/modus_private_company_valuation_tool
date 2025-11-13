from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
import structlog

from ..models.peer_group import PeerCompany
from ..models.valuation_multiple import ValuationMultiple

logger = structlog.get_logger(__name__)


@dataclass
class MultipleResult:
    ticker: str
    multiple: ValuationMultiple
    value: float | None
    numerator: float | None
    denominator: float | None
    rationale: str


class MultipleCalculator:

    # Initialize the multiple calculators for the supported multiples EV_REVENUE and EV_EBITDA
    # These calculators are a dictionary of the types of multiples and the related functions to calculate them.
    # If the multiple is not supported, the calculator will return None 
    # and if the denominator is 0 or None, the calculator will return None to avoid errors.
    def __init__(self) -> None:
        self._calculators: dict[ValuationMultiple, Callable[[PeerCompany], MultipleResult]] = {
            ValuationMultiple.EV_REVENUE: self._ev_to_revenue,
            ValuationMultiple.EV_EBITDA: self._ev_to_ebitda,
        }

    def calculate(self, peer: PeerCompany, multiples: Iterable[ValuationMultiple]) -> list[MultipleResult]:
        """Evaluate each requested multiple for the supplied peer company."""
        results: list[MultipleResult] = []
        for multiple in multiples:
            calculator = self._calculators.get(multiple)
            if not calculator:
                logger.warning("multiples.unsupported", multiple=multiple)
                continue
            results.append(calculator(peer))
        return results

    #helper function to safely divide two numbers and return None if the denominator is 0 or None to avoid errors
    @staticmethod
    def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
        """Guard against divide-by-zero and ``None`` operands."""
        if numerator is None or denominator in (None, 0):
            return None
        if denominator == 0:
            return None
        return float(numerator) / float(denominator)

    def _ev_to_revenue(self, peer: PeerCompany) -> MultipleResult:
        """Enterprise value to revenue ratio."""
        numerator = peer.enterprise_value
        denominator = peer.revenue
        value = self._safe_divide(numerator, denominator)
        return MultipleResult(
            ticker=peer.ticker,
            multiple=ValuationMultiple.EV_REVENUE,
            value=value,
            numerator=numerator,
            denominator=denominator,
            rationale="enterprise_value / revenue" if value is not None else "insufficient data",
        )

    def _ev_to_ebitda(self, peer: PeerCompany) -> MultipleResult:
        """Enterprise value to EBITDA ratio with negative EBITDA handling."""
        if peer.ebitda is not None and peer.ebitda <= 0:
            return MultipleResult(
                ticker=peer.ticker,
                multiple=ValuationMultiple.EV_EBITDA,
                value=None,
                numerator=peer.enterprise_value,
                denominator=peer.ebitda,
                rationale="negative or zero EBITDA",
            )
        numerator = peer.enterprise_value
        denominator = peer.ebitda
        value = self._safe_divide(numerator, denominator)
        return MultipleResult(
            ticker=peer.ticker,
            multiple=ValuationMultiple.EV_EBITDA,
            value=value,
            numerator=numerator,
            denominator=denominator,
            rationale="enterprise_value / ebitda" if value is not None else "insufficient data",
        )

