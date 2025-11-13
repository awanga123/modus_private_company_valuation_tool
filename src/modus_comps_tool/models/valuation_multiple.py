from __future__ import annotations

from enum import Enum


class ValuationMultiple(str, Enum):
    EV_REVENUE = "EV_REVENUE"
    EV_EBITDA = "EV_EBITDA"


DEFAULT_MULTIPLES: tuple[ValuationMultiple, ...] = (
    ValuationMultiple.EV_REVENUE,
    ValuationMultiple.EV_EBITDA,
)

