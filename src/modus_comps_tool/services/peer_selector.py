from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import structlog

from ..config.settings import settings
from ..models.company import PeerSelectionConfig, TargetCompany
from ..models.peer_group import PeerCompany, PeerGroup

logger = structlog.get_logger(__name__)


class PeerSelector:
    """Select comparable peers using automated industry mapping with optional manual overrides."""

    def __init__(self, peer_universe_path: Path | None = None) -> None:
        self._peer_universe_path = peer_universe_path or settings.absolute_peer_universe_path
        self._peer_universe = self._load_peer_universe()

    def select_peers(self, target: TargetCompany, config: PeerSelectionConfig) -> PeerGroup:
        """Return a ``PeerGroup`` with up to 10 peers: manual peers + sector-based peers from peer_universe."""
        # Start with manual peers
        manual = self._build_manual_peers(config.custom_tickers)
        # Copy the manual peers to a dictionary with the ticker as the key to build combined list of peers
        combined = {peer.ticker: peer for peer in manual}

        logger.info("peer_selection.manual_count", count=len(manual))

        # If we have fewer than 10 peers, fill the rest from peer_universe based on sector
        if len(combined) < 10:
            sector_peers = self._select_by_sector(target)
            for peer in sector_peers:
                if peer.ticker not in combined and len(combined) < 10:
                    combined[peer.ticker] = peer

        # Take only the first 10 peers if we have more than 10 (even if they are all manual peers) 
        peers_list = list(combined.values())[:10]

        logger.info(
            "peer_selection.final_count",
            total=len(peers_list),
            manual=len(manual),
            from_universe=len(peers_list) - len(manual),
        )

        selection_criteria = {
            "method": config.method,
            "applied_filters": config.filters.model_dump(),
            "sector": target.sector,
            "industry": target.industry,
            "max_peers": 10,
        }

        return PeerGroup(
            peers=peers_list,
            selection_method=config.method,
            selection_criteria=selection_criteria,
        )

    def _select_by_sector(self, target: TargetCompany) -> list[PeerCompany]:
        """Fetch peers from peer_universe based on the target company's sector."""
        if not target.sector and not target.industry:
            logger.warning("peer_selection.no_sector_or_industry", company=target.name)
            return []

        # Try sector first, fall back to industry
        search_key = target.sector or target.industry
        sector_peers = self._peer_universe.get(search_key, [])

        if not sector_peers:
            logger.warning("peer_selection.no_matches", sector=search_key)
            return []

        logger.info(
            "peer_selection.sector_based",
            sector=search_key,
            peer_count=len(sector_peers),
        )
        return [
            PeerCompany(
                ticker=item["ticker"],
                name=item.get("name"),
                industry=item.get("industry"),
                sector=item.get("sector"),
            )
            for item in sector_peers
        ]

    def _build_manual_peers(self, tickers: Iterable[str]) -> list[PeerCompany]:
        """Build ``PeerCompany`` stubs for manually supplied tickers."""
        peers = []
        for ticker in tickers:
            normalized = ticker.upper()
            peers.append(PeerCompany(ticker=normalized))
            logger.info("peer_selection.manual_added", ticker=normalized)
        return peers

    def _load_peer_universe(self) -> dict[str, list[dict[str, str]]]:
        """Read the peer universe JSON file into memory."""
        if not self._peer_universe_path.exists():
            logger.error("peer_selection.universe_missing", path=str(self._peer_universe_path))
            return {}

        with self._peer_universe_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        return data

