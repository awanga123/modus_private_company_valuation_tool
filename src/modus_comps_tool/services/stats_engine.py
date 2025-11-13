from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StatisticalSummary:
    values: list[float]
    mean: float | None
    median: float | None
    std_dev: float | None
    min: float | None
    max: float | None
    outliers: list[float]
    outlier_indices: list[int]


class StatsEngine:
    """Compute descriptive statistics and handle outlier detection."""

    def __init__(self) -> None:
        self.z_score_threshold = 2.0

    def summarize(self, series: Iterable[float]) -> StatisticalSummary:
        """Return descriptive statistics and detected outliers for the provided series."""
        values = [value for value in series if value is not None]
        if not values:
            return StatisticalSummary([], None, None, None, None, None, [], [])

        array = np.array(values, dtype=float)

        mean = float(np.mean(array))
        median = float(np.median(array))
        std_dev = float(np.std(array, ddof=0))
        minimum = float(np.min(array))
        maximum = float(np.max(array))

        outlier_indices = self._detect_outlier_indices(array)
        outliers = [float(array[idx]) for idx in outlier_indices]

        return StatisticalSummary(
            values=values,
            mean=mean,
            median=median,
            std_dev=std_dev,
            min=minimum,
            max=maximum,
            outliers=outliers,
            outlier_indices=outlier_indices,
        )

    def _detect_outlier_indices(self, array: np.ndarray) -> list[int]:
        """Identify outlier indices using a simple z-score threshold."""
        if array.size < 3 or np.std(array) == 0:
            return []

        z_scores = np.abs((array - np.mean(array)) / np.std(array))
        indices = np.where(z_scores > self.z_score_threshold)[0]
        if indices.size:
            logger.info("stats.outliers_detected", count=int(indices.size))
        return indices.tolist()

