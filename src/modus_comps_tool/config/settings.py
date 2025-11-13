from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-level configuration loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    environment: Literal["local", "test", "production"] = "local"
    cache_ttl_hours: int = 24
    cache_dir: Path = Path("cache/raw")
    audit_trail_dir: Path = Path("audit_trails")
    peer_universe_path: Path = Path("src/modus_comps_tool/data/peer_universe.json")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Default valuation configuration
    default_revenue_range_min: int = 200_000_000  # $200M
    default_revenue_range_max: int = 2_000_000_000  # $2B
    default_dlom_percentage: float = 0.10  # 10% discount for lack of marketability

    # API timeout and retry configuration
    api_timeout_seconds: int = 30  # Timeout for external API calls
    api_retry_attempts: int = 3  # Number of retry attempts for failed API calls
    api_retry_backoff_factor: float = 0.5  # Exponential backoff multiplier

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def absolute_cache_dir(self) -> Path:
        return self.project_root / self.cache_dir

    @property
    def absolute_audit_trail_dir(self) -> Path:
        return self.project_root / self.audit_trail_dir

    @property
    def absolute_peer_universe_path(self) -> Path:
        return self.project_root / self.peer_universe_path


settings = AppSettings()

