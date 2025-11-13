from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import structlog
import torch
from sentence_transformers import SentenceTransformer, util

from ..config.settings import settings
from ..models.company import PeerSelectionConfig, TargetCompany
from ..models.peer_group import PeerCompany, PeerGroup

logger = structlog.get_logger(__name__)


class PeerSelector:
    """Select comparable peers using automated industry mapping with optional manual overrides."""

    def __init__(self, peer_universe_path: Path | None = None) -> None:
        self._peer_universe_path = peer_universe_path or settings.absolute_peer_universe_path
        self._peer_universe = self._load_peer_universe()

        # We will use a semantic matching model to find the closest matching sector or industry from the peer universe,
        # if the given sector or industry is not found in the peer universe.

        # Load a lightweight SentenceTransformer model for semantic matching
        # Using all-MiniLM-L6-v2: fast, small (80MB), and effective
        logger.info("peer_selection.loading_model", model="all-MiniLM-L6-v2")
        self._model = SentenceTransformer("all-MiniLM-L6-v2")

        # Pre-compute embeddings for all sector names for fast matching
        self._sector_names = list(self._peer_universe.keys())
        if self._sector_names:
            logger.info("peer_selection.computing_embeddings", count=len(self._sector_names))
            self._sector_embeddings = self._model.encode(
                self._sector_names, convert_to_tensor=True
            )
        else:
            self._sector_embeddings = torch.tensor([])

    def select_peers(self, target: TargetCompany, config: PeerSelectionConfig) -> PeerGroup:
        """Return a ``PeerGroup`` with up to 10 peers: manual peers + sector-based peers from peer_universe."""
        # Start with manual peers
        manual = self._build_manual_peers(config.custom_tickers)
        # Copy the manual peers to a dictionary with the ticker as the key to build combined list of peers
        combined = {peer.ticker: peer for peer in manual}

        logger.info("peer_selection.manual_count", count=len(manual))

        # If we have fewer than 10 peers, fill the rest from peer_universe based on sector
        sector_match_info: dict = {}
        if len(combined) < 10:
            sector_peers, sector_match_info = self._select_by_sector(target)
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

        # Add fuzzy matching information to selection criteria if it was used
        if sector_match_info:
            selection_criteria["fuzzy_match_used"] = sector_match_info.get("fuzzy_match_used", False)
            selection_criteria["original_search_key"] = sector_match_info.get("original_search_key")
            selection_criteria["matched_sector_key"] = sector_match_info.get("matched_sector_key")
            if sector_match_info.get("similarity_score") is not None:
                selection_criteria["similarity_score"] = round(sector_match_info["similarity_score"], 3)

        return PeerGroup(
            peers=peers_list,
            selection_method=config.method,
            selection_criteria=selection_criteria,
        )

    def _select_by_sector(self, target: TargetCompany) -> tuple[list[PeerCompany], dict]:
        """Fetch peers from peer_universe based on the target company's sector.

        Returns:
            A tuple of (peer_list, match_info) where match_info contains:
                - fuzzy_match_used: bool indicating if semantic matching was used
                - original_search_key: the original sector/industry provided
                - matched_sector_key: the actual sector key used (after fuzzy matching if applicable)
                - similarity_score: float similarity score if fuzzy match was used (0-1 range)
        """
        match_info = {
            "fuzzy_match_used": False,
            "original_search_key": None,
            "matched_sector_key": None,
            "similarity_score": None,
        }

        # If there is no sector or industry then we cannot select any peers, so we return an empty list.
        # This is an intended design decision because if the user does not provide a sector or industry,
        # then there is no real basis to doing this comparitive analysis in the first place. We will make it clear
        # in the audit trail that no peers were selected and in the API that an industry or sector are required for
        # a proper valuation. I was thinking we could use a default sector or industry if one is not provided, but
        # then we would not be able to distinguish between a user who did not provide a sector or industry and a user who
        # provided a default sector or industry. Additionall, given the MCP server, the user can rely on the power of the LLM
        # to help them select the appropriate sector or industry, especially given that the sectors exposed in the MCP.
        if not target.sector and not target.industry:
            logger.warning("peer_selection.no_sector_or_industry", company=target.name)
            return [], match_info

        # Try sector first, fall back to industry
        search_key = target.sector or target.industry
        assert search_key is not None  # Already checked above
        match_info["original_search_key"] = search_key
        sector_peers = self._peer_universe.get(search_key, [])

        # If no exact match, try fuzzy matching
        if not sector_peers:
            closest_match, similarity = self._find_closest_sector_match(search_key)
            if closest_match:
                logger.info(
                    "peer_selection.fuzzy_match",
                    original=search_key,
                    matched=closest_match,
                )
                sector_peers = self._peer_universe.get(closest_match, [])
                # Update search_key to reflect the matched key for logging below
                search_key = closest_match
                match_info["fuzzy_match_used"] = True
                match_info["matched_sector_key"] = closest_match
                match_info["similarity_score"] = similarity
            else:
                logger.warning("peer_selection.no_matches", sector=search_key)
                return [], match_info
        else:
            # Exact match found
            match_info["matched_sector_key"] = search_key

        logger.info(
            "peer_selection.sector_based",
            sector=search_key,
            peer_count=len(sector_peers),
        )
        peers = [
            PeerCompany(
                ticker=item["ticker"],
                name=item.get("name"),
                industry=item.get("industry"),
                sector=item.get("sector"),
            )
            for item in sector_peers
        ]
        return peers, match_info

    def _find_closest_sector_match(self, search_key: str) -> tuple[str | None, float | None]:
        """Find the closest matching sector/industry key using semantic similarity.

        Uses SentenceTransformer to compute semantic similarity between the search key
        and all available sector names, returning the best match above a threshold.

        Args:
            search_key: The sector or industry name to match

        Returns:
            A tuple of (matched_key, similarity_score) where:
                - matched_key: The closest matching key from peer_universe, or None if no good match found
                - similarity_score: The cosine similarity score (0-1), or None if no match found
        """
        if not search_key or not self._sector_names:
            return None, None

        # Encode the search query
        query_embedding = self._model.encode(search_key, convert_to_tensor=True)

        # Compute cosine similarities between query and all sector embeddings
        similarities = util.cos_sim(query_embedding, self._sector_embeddings)[0]

        # Get the best match
        best_idx = int(similarities.argmax().item())
        best_similarity = float(similarities[best_idx].item())

        # Return match only if similarity is above threshold (0.5 = 50% similar)
        # This prevents matching completely unrelated terms
        if best_similarity >= 0.5:
            logger.debug(
                "peer_selection.semantic_match",
                search_key=search_key,
                matched_key=self._sector_names[best_idx],
                similarity=round(best_similarity, 3),
            )
            return self._sector_names[best_idx], best_similarity

        return None, None

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

