"""Unit tests for StatsEngine service."""

import pytest
import numpy as np

from src.modus_comps_tool.services.stats_engine import StatsEngine, StatisticalSummary


class TestStatsEngine:
    """Test the StatsEngine service for statistical calculations."""

    @pytest.fixture
    def stats_engine(self):
        """Create a StatsEngine instance for testing."""
        return StatsEngine()

    def test_summarize_with_normal_data(self, stats_engine):
        """Test statistical summary with normal data."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = stats_engine.summarize(data)

        assert result.mean == 30.0
        assert result.median == 30.0
        assert result.min == 10.0
        assert result.max == 50.0
        assert result.std_dev == pytest.approx(14.142, abs=0.01)
        assert result.values == data
        assert len(result.outliers) == 0

    def test_summarize_with_empty_list(self, stats_engine):
        """Test statistical summary with empty data."""
        data = []

        result = stats_engine.summarize(data)

        assert result.mean is None
        assert result.median is None
        assert result.min is None
        assert result.max is None
        assert result.std_dev is None
        assert result.values == []
        assert result.outliers == []

    def test_summarize_with_none_values(self, stats_engine):
        """Test that None values are filtered out."""
        data = [10.0, None, 20.0, None, 30.0]

        result = stats_engine.summarize(data)

        assert result.values == [10.0, 20.0, 30.0]
        assert result.mean == 20.0
        assert result.median == 20.0

    def test_summarize_with_outliers(self, stats_engine):
        """Test outlier detection with clear outliers."""
        # Data with clear outliers (z-score > 2)
        data = [10.0, 11.0, 12.0, 13.0, 14.0, 100.0]  # 100 is an outlier

        result = stats_engine.summarize(data)

        assert len(result.outliers) > 0
        assert 100.0 in result.outliers
        assert len(result.outlier_indices) > 0

    def test_summarize_with_single_value(self, stats_engine):
        """Test with a single value."""
        data = [42.0]

        result = stats_engine.summarize(data)

        assert result.mean == 42.0
        assert result.median == 42.0
        assert result.min == 42.0
        assert result.max == 42.0
        assert result.std_dev == 0.0
        # No outliers with single value
        assert len(result.outliers) == 0

    def test_detect_outlier_indices_with_small_dataset(self, stats_engine):
        """Test that outlier detection doesn't fail with < 3 values."""
        array = np.array([10.0, 20.0])

        indices = stats_engine._detect_outlier_indices(array)

        # Should return empty list for small datasets
        assert indices == []

    def test_detect_outlier_indices_with_zero_std(self, stats_engine):
        """Test outlier detection when all values are the same (std dev = 0)."""
        array = np.array([10.0, 10.0, 10.0, 10.0])

        indices = stats_engine._detect_outlier_indices(array)

        # Should return empty list when standard deviation is zero
        assert indices == []

    def test_custom_z_score_threshold(self):
        """Test that z-score threshold can be customized."""
        engine = StatsEngine()
        engine.z_score_threshold = 1.5  # More sensitive to outliers

        # Data where values are moderate outliers (z-score ~1.8)
        data = [10.0, 11.0, 12.0, 13.0, 14.0, 25.0]

        result = engine.summarize(data)

        # With lower threshold, should detect more outliers
        assert len(result.outliers) > 0

    def test_summarize_with_negative_values(self, stats_engine):
        """Test statistical summary with negative values."""
        data = [-50.0, -25.0, 0.0, 25.0, 50.0]

        result = stats_engine.summarize(data)

        assert result.mean == 0.0
        assert result.median == 0.0
        assert result.min == -50.0
        assert result.max == 50.0

    def test_summarize_preserves_original_values(self, stats_engine):
        """Test that the original values list is preserved correctly."""
        data = [5.5, 10.2, 15.7, 20.1]

        result = stats_engine.summarize(data)

        assert result.values == data
        assert all(isinstance(v, float) for v in result.values)
