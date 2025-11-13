# Test Suite Documentation

This directory contains unit tests for the main business logic in the `modus_comps_tool` services.

## Test Coverage

### Services Tested

1. **StatsEngine** (`test_stats_engine.py`) - 13 tests
   - Statistical calculations (mean, median, std dev)
   - Outlier detection using z-scores
   - Edge cases (empty data, None values, single values)

2. **MultipleCalculator** (`test_multiple_calculator.py`) - 17 tests
   - EV/Revenue multiple calculations
   - EV/EBITDA multiple calculations
   - Division by zero and None handling
   - Negative EBITDA handling
   - Edge cases for all calculations

3. **PeerSelector** (`test_peer_selector.py`) - 13 tests
   - Peer selection with exact sector matches
   - Fuzzy/semantic matching fallback
   - Manual ticker handling
   - Peer group size limits (10 max)
   - Selection criteria tracking
   - Duplicate handling

**Total: 40 unit tests** covering major branches and business logic.

## Running Tests

### Run All Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Specific Test File
```bash
pytest tests/unit/test_stats_engine.py -v
pytest tests/unit/test_multiple_calculator.py -v
pytest tests/unit/test_peer_selector.py -v
```

### Run Specific Test
```bash
pytest tests/unit/test_stats_engine.py::TestStatsEngine::test_summarize_with_normal_data -v
```

### Run with Coverage Report
```bash
pytest tests/unit/ --cov=src/modus_comps_tool/services --cov-report=term-missing
```

### Run Tests in Parallel (faster)
```bash
pytest tests/unit/ -n auto
```

## Test Structure

```
tests/
├── __init__.py                     # Test package marker
├── conftest.py                     # Shared fixtures and configuration
├── unit/                           # Unit tests directory
│   ├── __init__.py
│   ├── test_stats_engine.py       # StatsEngine tests
│   ├── test_multiple_calculator.py # MultipleCalculator tests
│   └── test_peer_selector.py      # PeerSelector tests
├── integration/                    # Integration tests (empty)
└── fixtures/                       # Test fixtures (empty)
```

## Key Testing Patterns

### Fixtures
- Tests use pytest fixtures for setup and teardown
- Mock dependencies (especially SentenceTransformer model) to speed up tests
- Temporary files for testing file I/O operations

### Mocking
- `peer_selector.py` tests mock the SentenceTransformer to avoid loading the model
- Mock peer_universe.json data for isolated testing

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<what_it_tests>_<scenario>`

## What's Tested

✅ **Main business logic branches**
✅ **Edge cases** (None, zero, empty, negative values)
✅ **Error handling** paths
✅ **Data validation** logic
✅ **Major workflows** in each service

## What's NOT Tested

❌ Integration tests (API endpoints, database operations)
❌ End-to-end workflows
❌ External API calls (yfinance, etc.)
❌ File I/O with real files (mocked instead)

## Dependencies

All test dependencies are included in the `dev` dependency group in `pyproject.toml`:
- pytest
- pytest-cov (coverage reporting)
- pytest-mock (mocking utilities)
- pytest-asyncio (async test support)

## CI/CD Integration

These tests can be easily integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Unit Tests
  run: pytest tests/unit/ -v --cov
```

## Notes

- Tests are designed to run fast (< 3 seconds total)
- No external dependencies required (all mocked)
- Tests are isolated and can run in any order
- SentenceTransformer model is mocked to avoid 3-4 second load time per test
