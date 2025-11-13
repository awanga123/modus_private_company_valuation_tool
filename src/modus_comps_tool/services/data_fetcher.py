from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
import yfinance as yf

from ..config.settings import settings

logger = structlog.get_logger(__name__)


@dataclass
class CachedItem:
    path: Path
    fetched_at: datetime
    payload: dict[str, Any]

    @property
    def is_expired(self) -> bool:
        expires_at = self.fetched_at + timedelta(hours=settings.cache_ttl_hours)
        return datetime.now(timezone.utc) > expires_at


class CompanyDataFetcher:
    """Fetch financial data for public tickers using yfinance with two-tier caching.

    Cache Strategy:
    - In-memory cache: Fast lookups for frequently accessed tickers (shared across requests when used as singleton)
    - Disk cache: Persists data between service restarts (24-hour TTL by default)

    This class should be instantiated as a singleton to maximize cache efficiency across requests.
    """

    def __init__(self) -> None:
        self._cache: dict[str, CachedItem] = {}
        settings.absolute_cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, ticker: str) -> dict[str, Any]:
        """Return the latest known financial snapshot for ``ticker``.

        The method first consults the on-disk cache. When the cached copy is older
        than the configured TTL, fresh data is fetched from yfinance and the cache
        is updated. The payload contains the core metrics required for valuation
        plus the raw financial statements so we can trace every figure later in the audit trail.
        """
        ticker = ticker.upper()
        cached = self._read_cache(ticker)
        if cached and not cached.is_expired:
            logger.info("cache.hit", ticker=ticker, path=str(cached.path))
            return cached.payload

        logger.info("cache.miss", ticker=ticker)

        # if the cache is missed, fetch the data from yfinance directly and log the raw output
        # https://ranaroussi.github.io/yfinance/index.html for more information on the yfinance API
        company = yf.Ticker(ticker)

        info = company.info or {}
        balance_sheet = self._df_to_latest(company.balance_sheet)
        financials = self._df_to_latest(company.financials)

        # Log the raw yfinance output
        logger.info(
            "yfinance.raw_info",
            ticker=ticker,
            long_name=info.get("longName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            info_keys=list(info.keys()),
        )

        logger.info(
            "yfinance.raw_financials",
            ticker=ticker,
            total_revenue=financials.get("Total Revenue"),
            ebitda=financials.get("Ebitda"),
            operating_income=financials.get("Operating Income"),
            net_income=financials.get("Net Income"),
            financial_keys=list(financials.keys()),
        )

        logger.info(
            "yfinance.raw_balance_sheet",
            ticker=ticker,
            balance_sheet_keys=list(balance_sheet.keys()),
        )

        payload = {
            "ticker": ticker,
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "revenue": financials.get("Total Revenue"),
            "ebitda": financials.get("Ebitda") or financials.get("Operating Income"),
            "net_income": financials.get("Net Income"),
            "balance_sheet": balance_sheet,
            "financials": financials,
            "source_meta": {
                "info_keys": list(info.keys()),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        self._write_cache(ticker, payload)
        return payload

    def _read_cache(self, ticker: str) -> CachedItem | None:
        """Load a cached payload from memory (fastest) or disk if it exists."""
        # Check in-memory cache first (shared across requests when singleton)
        if ticker in self._cache and not self._cache[ticker].is_expired:
            return self._cache[ticker]

        # Fall back to disk cache if not in memory
        cache_path = settings.absolute_cache_dir / f"{ticker}.json"
        if not cache_path.exists():
            return None

        with cache_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Load into in-memory cache for faster subsequent access
        cached = CachedItem(
            path=cache_path,
            fetched_at=datetime.fromisoformat(data["source_meta"]["fetched_at"]),
            payload=data,
        )
        self._cache[ticker] = cached
        return cached

    def _write_cache(self, ticker: str, payload: dict[str, Any]) -> None:
        """Persist a payload to both disk and in-memory cache."""
        # Write to disk for persistence across restarts
        cache_path = settings.absolute_cache_dir / f"{ticker}.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        # Update in-memory cache for fast subsequent lookups
        cached = CachedItem(
            path=cache_path,
            fetched_at=datetime.fromisoformat(payload["source_meta"]["fetched_at"]),
            payload=payload,
        )
        self._cache[ticker] = cached

    @staticmethod
    def _df_to_latest(df: pd.DataFrame | None) -> dict[str, Any]:
        """Convert the first (most recent) column of a yfinance DataFrame into a dict."""
        if df is None or df.empty:
            return {}

        latest_col = df.columns[0]
        return {index: float(value) for index, value in df[latest_col].items() if pd.notna(value)}

