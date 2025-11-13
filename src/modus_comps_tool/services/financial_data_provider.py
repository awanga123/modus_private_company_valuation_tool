"""Abstraction for financial data providers to fetch company information, financials, and balance sheet data.
Can use another API provider in the future if needed."""

from __future__ import annotations

import time
from typing import Any, Protocol

import pandas as pd
import structlog

from ..config.settings import settings

logger = structlog.get_logger(__name__)


class IFinancialDataProvider(Protocol):
    """Interface for financial data providers (yfinance, Bloomberg, etc.)."""

    def fetch_company_info(self, ticker: str) -> dict[str, Any]:
        """Fetch company information (name, sector, industry, market metrics)."""
        ...

    def fetch_financials(self, ticker: str) -> dict[str, float]:
        """Fetch income statement data (revenue, EBITDA, net income, etc.)."""
        ...

    def fetch_balance_sheet(self, ticker: str) -> dict[str, float]:
        """Fetch balance sheet data (assets, liabilities, etc.)."""
        ...


class YFinanceProvider:
    """yfinance implementation of IFinancialDataProvider with retry logic and timeout handling."""

    def __init__(self) -> None:
        import yfinance as yf
        self.yf = yf

    def _retry_with_backoff(self, func, ticker: str, operation: str):
        """Retry an operation with exponential backoff."""
        for attempt in range(settings.api_retry_attempts):
            try:
                return func()
            except (ConnectionError, TimeoutError) as exc:
                if attempt < settings.api_retry_attempts - 1:
                    wait_time = settings.api_retry_backoff_factor * (2 ** attempt)
                    logger.warning(
                        "api.retry",
                        ticker=ticker,
                        operation=operation,
                        attempt=attempt + 1,
                        wait_time=wait_time,
                        error=type(exc).__name__,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("api.retry_exhausted", ticker=ticker, operation=operation)
                    raise

    def fetch_company_info(self, ticker: str) -> dict[str, Any]:
        """Fetch company information using yfinance with retry logic."""
        def _fetch():
            company = self.yf.Ticker(ticker)
            return company.info or {}
        return self._retry_with_backoff(_fetch, ticker, "fetch_company_info")

    def fetch_financials(self, ticker: str) -> dict[str, float]:
        """Fetch income statement data using yfinance with retry logic."""
        def _fetch():
            company = self.yf.Ticker(ticker)
            return self._df_to_latest(company.financials)
        return self._retry_with_backoff(_fetch, ticker, "fetch_financials")

    def fetch_balance_sheet(self, ticker: str) -> dict[str, float]:
        """Fetch balance sheet data using yfinance with retry logic."""
        def _fetch():
            company = self.yf.Ticker(ticker)
            return self._df_to_latest(company.balance_sheet)
        return self._retry_with_backoff(_fetch, ticker, "fetch_balance_sheet")

    @staticmethod
    def _df_to_latest(df: pd.DataFrame | None) -> dict[str, float]:
        """Convert the first (most recent) column of a yfinance DataFrame into a dict."""
        if df is None or df.empty:
            return {}
        latest_col = df.columns[0]
        return {index: float(value) for index, value in df[latest_col].items() if pd.notna(value)}
