"""Unit tests for PeerSelector service."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import torch

from src.modus_comps_tool.services.peer_selector import PeerSelector
from src.modus_comps_tool.models.company import TargetCompany, PeerSelectionConfig


@pytest.fixture
def mock_peer_universe_data():
    """Sample peer universe data for testing."""
    return {
        "Biotechnology": [
            {"ticker": "ALNY", "name": "Alnylam Pharmaceuticals", "sector": "Biotechnology"},
            {"ticker": "BIIB", "name": "Biogen", "sector": "Biotechnology"},
            {"ticker": "VRTX", "name": "Vertex Pharmaceuticals", "sector": "Biotechnology"},
        ],
        "Financial Technology": [
            {"ticker": "SQ", "name": "Block Inc", "sector": "Financial Technology"},
            {"ticker": "PYPL", "name": "PayPal", "sector": "Financial Technology"},
        ],
        "AI & Machine Learning": [
            {"ticker": "NVDA", "name": "NVIDIA", "sector": "AI & Machine Learning"},
            {"ticker": "AI", "name": "C3.ai", "sector": "AI & Machine Learning"},
        ],
    }


@pytest.fixture
def mock_peer_universe_file(tmp_path, mock_peer_universe_data):
    """Create a temporary peer_universe.json file."""
    universe_file = tmp_path / "peer_universe.json"
    with open(universe_file, "w") as f:
        json.dump(mock_peer_universe_data, f)
    return universe_file


@pytest.fixture
def mock_sentence_transformer():
    """Mock the SentenceTransformer model to avoid loading it in tests."""
    with patch('src.modus_comps_tool.services.peer_selector.SentenceTransformer') as mock_model:
        # Create mock model instance
        model_instance = MagicMock()

        # Mock encode to return simple tensor
        def mock_encode(text, convert_to_tensor=False):
            # Return a simple tensor for testing
            if isinstance(text, list):
                return torch.randn(len(text), 384)
            return torch.randn(384)

        model_instance.encode = Mock(side_effect=mock_encode)
        mock_model.return_value = model_instance

        yield mock_model


@pytest.fixture
def peer_selector(mock_peer_universe_file, mock_sentence_transformer):
    """Create a PeerSelector instance with mocked dependencies."""
    return PeerSelector(peer_universe_path=mock_peer_universe_file)


class TestPeerSelector:
    """Test the PeerSelector service."""

    def test_select_peers_with_exact_sector_match(self, peer_selector):
        """Test peer selection with exact sector match."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Biotech",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        config = PeerSelectionConfig(method="sector", custom_tickers=[])

        result = peer_selector.select_peers(target, config)

        assert len(result.peers) == 3
        assert result.selection_method == "sector"
        assert any(peer.ticker == "ALNY" for peer in result.peers)
        assert any(peer.ticker == "BIIB" for peer in result.peers)
        assert result.selection_criteria["fuzzy_match_used"] is False
        assert result.selection_criteria["matched_sector_key"] == "Biotechnology"

    def test_select_peers_with_industry_fallback(self, peer_selector):
        """Test peer selection falls back to industry when sector is None."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector=None,
            industry="Biotechnology",
        )
        config = PeerSelectionConfig(method="sector", custom_tickers=[])

        result = peer_selector.select_peers(target, config)

        assert len(result.peers) == 3
        assert result.selection_criteria["original_search_key"] == "Biotechnology"

    def test_select_peers_with_no_sector_or_industry(self, peer_selector):
        """Test peer selection returns empty when no sector or industry provided."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector=None,
            industry=None,
        )
        config = PeerSelectionConfig(method="sector", custom_tickers=[])

        result = peer_selector.select_peers(target, config)

        assert len(result.peers) == 0

    def test_select_peers_with_manual_tickers(self, peer_selector):
        """Test peer selection with manual custom tickers."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        config = PeerSelectionConfig(
            method="sector",
            custom_tickers=["MSFT", "GOOGL", "AAPL"],
        )

        result = peer_selector.select_peers(target, config)

        # Should have 3 manual + up to 7 from sector (total 10 max)
        assert len(result.peers) <= 10
        # Manual tickers should be included
        manual_tickers = [peer.ticker for peer in result.peers if peer.ticker in ["MSFT", "GOOGL", "AAPL"]]
        assert len(manual_tickers) == 3

    def test_select_peers_caps_at_10_peers(self, peer_selector):
        """Test that peer selection is capped at 10 peers."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        config = PeerSelectionConfig(
            method="sector",
            custom_tickers=["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"],
        )

        result = peer_selector.select_peers(target, config)

        # Should be capped at 10 total
        assert len(result.peers) == 10

    def test_select_by_sector_returns_match_info(self, peer_selector):
        """Test that _select_by_sector returns match info."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )

        peers, match_info = peer_selector._select_by_sector(target)

        assert isinstance(peers, list)
        assert isinstance(match_info, dict)
        assert "fuzzy_match_used" in match_info
        assert "original_search_key" in match_info
        assert "matched_sector_key" in match_info

    def test_select_by_sector_with_no_match(self, peer_selector):
        """Test _select_by_sector when no match is found."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="NonExistentSector",
        )

        # Mock the fuzzy match to return None
        with patch.object(peer_selector, '_find_closest_sector_match', return_value=(None, None)):
            peers, match_info = peer_selector._select_by_sector(target)

            assert len(peers) == 0
            assert match_info["fuzzy_match_used"] is False
            assert match_info["matched_sector_key"] is None

    def test_find_closest_sector_match_returns_tuple(self, peer_selector):
        """Test that _find_closest_sector_match returns (key, score) tuple."""
        # This will use the mocked model's behavior
        result = peer_selector._find_closest_sector_match("biotech")

        assert isinstance(result, tuple)
        assert len(result) == 2
        # First element should be string or None
        assert result[0] is None or isinstance(result[0], str)
        # Second element should be float or None
        assert result[1] is None or isinstance(result[1], float)

    def test_selection_criteria_includes_fuzzy_match_info(self, peer_selector):
        """Test that selection criteria includes fuzzy matching information."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        config = PeerSelectionConfig(method="sector", custom_tickers=[])

        result = peer_selector.select_peers(target, config)

        criteria = result.selection_criteria
        assert "fuzzy_match_used" in criteria
        assert "original_search_key" in criteria
        assert "matched_sector_key" in criteria
        # For exact match, similarity_score should not be present
        if not criteria["fuzzy_match_used"]:
            assert "similarity_score" not in criteria or criteria.get("similarity_score") is None

    def test_build_manual_peers(self, peer_selector):
        """Test _build_manual_peers creates PeerCompany instances."""
        tickers = ["AAPL", "MSFT", "googl"]  # mixed case

        peers = peer_selector._build_manual_peers(tickers)

        assert len(peers) == 3
        assert all(peer.ticker.isupper() for peer in peers)
        assert peers[0].ticker == "AAPL"
        assert peers[1].ticker == "MSFT"
        assert peers[2].ticker == "GOOGL"

    def test_load_peer_universe_with_missing_file(self, tmp_path, mock_sentence_transformer):
        """Test that missing peer_universe.json is handled gracefully."""
        missing_file = tmp_path / "nonexistent.json"

        selector = PeerSelector(peer_universe_path=missing_file)

        assert selector._peer_universe == {}

    def test_peer_group_selection_criteria_structure(self, peer_selector):
        """Test that PeerGroup selection_criteria has expected structure."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        config = PeerSelectionConfig(method="sector", custom_tickers=["MSFT"])

        result = peer_selector.select_peers(target, config)

        criteria = result.selection_criteria
        assert "method" in criteria
        assert "applied_filters" in criteria
        assert "sector" in criteria
        assert "industry" in criteria
        assert "max_peers" in criteria
        assert criteria["max_peers"] == 10

    def test_manual_peers_no_duplicates_with_sector_peers(self, peer_selector):
        """Test that manual peers don't duplicate sector peers."""
        target = TargetCompany(
            ticker="TEST",
            name="Test Company",
            revenue=1_000_000.0,
            sector="Biotechnology",
        )
        # ALNY is in the Biotechnology sector in our mock data
        config = PeerSelectionConfig(method="sector", custom_tickers=["ALNY"])

        result = peer_selector.select_peers(target, config)

        # Count how many times ALNY appears
        alny_count = sum(1 for peer in result.peers if peer.ticker == "ALNY")
        assert alny_count == 1, "ALNY should only appear once"
