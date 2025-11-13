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

