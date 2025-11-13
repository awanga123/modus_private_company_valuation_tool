"""Unit tests for MultipleCalculator service."""

import pytest

from src.modus_comps_tool.services.multiple_calculator import MultipleCalculator, MultipleResult
from src.modus_comps_tool.models.peer_group import PeerCompany
from src.modus_comps_tool.models.valuation_multiple import ValuationMultiple


class TestMultipleCalculator:
    """Test the MultipleCalculator service for financial multiple calculations."""

    @pytest.fixture
    def calculator(self):
        """Create a MultipleCalculator instance for testing."""
        return MultipleCalculator()

    @pytest.fixture
    def sample_peer(self):
        """Create a sample peer company with complete data."""
        return PeerCompany(
            ticker="AAPL",
            name="Apple Inc.",
            enterprise_value=2_000_000_000.0,
            revenue=400_000_000.0,
            ebitda=100_000_000.0,
        )

    def test_calculate_ev_to_revenue_success(self, calculator, sample_peer):
        """Test successful EV/Revenue calculation."""
        results = calculator.calculate(sample_peer, [ValuationMultiple.EV_REVENUE])

        assert len(results) == 1
        result = results[0]
        assert result.ticker == "AAPL"
        assert result.multiple == ValuationMultiple.EV_REVENUE
        assert result.value == 5.0  # 2B / 400M
        assert result.numerator == 2_000_000_000.0
        assert result.denominator == 400_000_000.0
        assert "enterprise_value / revenue" in result.rationale

    def test_calculate_ev_to_ebitda_success(self, calculator, sample_peer):
        """Test successful EV/EBITDA calculation."""
        results = calculator.calculate(sample_peer, [ValuationMultiple.EV_EBITDA])

        assert len(results) == 1
        result = results[0]
        assert result.ticker == "AAPL"
        assert result.multiple == ValuationMultiple.EV_EBITDA
        assert result.value == 20.0  # 2B / 100M
        assert result.numerator == 2_000_000_000.0
        assert result.denominator == 100_000_000.0
        assert "enterprise_value / ebitda" in result.rationale

    def test_calculate_multiple_multiples(self, calculator, sample_peer):
        """Test calculating multiple multiples at once."""
        multiples = [ValuationMultiple.EV_REVENUE, ValuationMultiple.EV_EBITDA]
        results = calculator.calculate(sample_peer, multiples)

        assert len(results) == 2
        assert results[0].multiple == ValuationMultiple.EV_REVENUE
        assert results[1].multiple == ValuationMultiple.EV_EBITDA
        assert results[0].value is not None
        assert results[1].value is not None

    def test_ev_to_revenue_with_none_revenue(self, calculator):
        """Test EV/Revenue calculation when revenue is None."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=1_000_000.0,
            revenue=None,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_REVENUE])

        result = results[0]
        assert result.value is None
        assert result.numerator == 1_000_000.0
        assert result.denominator is None
        assert "insufficient data" in result.rationale

    def test_ev_to_revenue_with_zero_revenue(self, calculator):
        """Test EV/Revenue calculation when revenue is zero."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=1_000_000.0,
            revenue=0.0,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_REVENUE])

        result = results[0]
        assert result.value is None
        assert "insufficient data" in result.rationale

    def test_ev_to_ebitda_with_negative_ebitda(self, calculator):
        """Test EV/EBITDA calculation when EBITDA is negative."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=1_000_000.0,
            ebitda=-50_000.0,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_EBITDA])

        result = results[0]
        assert result.value is None
        assert result.numerator == 1_000_000.0
        assert result.denominator == -50_000.0
        assert "negative or zero EBITDA" in result.rationale

    def test_ev_to_ebitda_with_zero_ebitda(self, calculator):
        """Test EV/EBITDA calculation when EBITDA is zero."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=1_000_000.0,
            ebitda=0.0,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_EBITDA])

        result = results[0]
        assert result.value is None
        assert "negative or zero EBITDA" in result.rationale

    def test_ev_to_ebitda_with_none_ebitda(self, calculator):
        """Test EV/EBITDA calculation when EBITDA is None."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=1_000_000.0,
            ebitda=None,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_EBITDA])

        result = results[0]
        assert result.value is None
        assert "insufficient data" in result.rationale

    def test_ev_to_revenue_with_none_enterprise_value(self, calculator):
        """Test EV/Revenue when enterprise value is None."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=None,
            revenue=1_000_000.0,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_REVENUE])

        result = results[0]
        assert result.value is None
        assert result.numerator is None
        assert "insufficient data" in result.rationale

    def test_safe_divide_with_valid_inputs(self, calculator):
        """Test _safe_divide with valid inputs."""
        result = calculator._safe_divide(100.0, 20.0)

        assert result == 5.0

    def test_safe_divide_with_none_numerator(self, calculator):
        """Test _safe_divide with None numerator."""
        result = calculator._safe_divide(None, 20.0)

        assert result is None

    def test_safe_divide_with_none_denominator(self, calculator):
        """Test _safe_divide with None denominator."""
        result = calculator._safe_divide(100.0, None)

        assert result is None

    def test_safe_divide_with_zero_denominator(self, calculator):
        """Test _safe_divide with zero denominator."""
        result = calculator._safe_divide(100.0, 0.0)

        assert result is None

    def test_safe_divide_with_both_none(self, calculator):
        """Test _safe_divide with both inputs as None."""
        result = calculator._safe_divide(None, None)

        assert result is None

    def test_calculate_with_empty_multiples_list(self, calculator, sample_peer):
        """Test calculating with an empty multiples list."""
        results = calculator.calculate(sample_peer, [])

        assert results == []

    def test_result_structure(self, calculator, sample_peer):
        """Test that MultipleResult has the expected structure."""
        results = calculator.calculate(sample_peer, [ValuationMultiple.EV_REVENUE])

        result = results[0]
        assert isinstance(result, MultipleResult)
        assert hasattr(result, 'ticker')
        assert hasattr(result, 'multiple')
        assert hasattr(result, 'value')
        assert hasattr(result, 'numerator')
        assert hasattr(result, 'denominator')
        assert hasattr(result, 'rationale')

    def test_ev_to_ebitda_with_positive_ebitda(self, calculator):
        """Test EV/EBITDA with positive EBITDA (normal case)."""
        peer = PeerCompany(
            ticker="TEST",
            enterprise_value=500_000.0,
            ebitda=50_000.0,
        )

        results = calculator.calculate(peer, [ValuationMultiple.EV_EBITDA])

        result = results[0]
        assert result.value == 10.0
        assert "enterprise_value / ebitda" in result.rationale
