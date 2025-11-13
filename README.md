# Modus Comps Tool

Auditable comparable-company valuation pipeline built for the Modus take-home assessment. The service accepts minimal private-company inputs, selects comparable public peers, fetches market/financial data via `yfinance`, calculates EV/Revenue and EV/EBITDA multiples, and produces a documented audit trail. An MCP server is bundled so LLM tools can drive valuations directly.

---

## 1. Project Overview
- **FastAPI HTTP service** (`src/modus_comps_tool/api/app.py`)
- **Valuation engine** (`services/valuation_service.py`) covering peer selection, financial data fetch, multiple/statistics calculation, DLOM, and audit persistence
- **Peer universe** (`data/peer_universe.json`) listing sectors → ticker metadata
- **Audit storage** (`audit_trails/`) plus cached ticker payloads (`cache/raw/`)
- **MCP server** (`src/modus_comps_tool/mcp_server.py`) exposing valuation tools for MCP clients
- **Sample payloads** (`test_inputs/`) for manual or automated testing

---

## 2. Setup
```bash
cd /Users/alexanderwang/Projects/modus_take_home
uv sync
```
`uv` installs all runtime + dev dependencies (FastAPI, pydantic, structlog, yfinance, fastmcp, pytest, etc.) into `.venv/`.

---

## 3. Run the FastAPI Service
```bash
cd /Users/alexanderwang/Projects/modus_take_home
PYTHONPATH=src uv run uvicorn modus_comps_tool.api.app:app --reload --host 127.0.0.1 --port 8000
```

- `app.get("/health")`: Liveness check returning `{ "status": "ok" }`.
- `app.get("/peer-sectors")`: Lists available sector keys from `peer_universe.json` for caller discovery. 
- `app.post("/valuations")`: Accepts `ValuationRequestPayload`, runs the valuation workflow, and returns summary plus human-readable audit narrative.
- `app.get("/valuations/{request_id}")`: Loads stored `ValuationResult` files to deliver the full detailed audit trail.

- Health: `curl http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs#/default/`

### Example request
```bash
curl -X POST "http://127.0.0.1:8000/valuations" \
  -H "Content-Type: application/json" \
  -d '{
        "target_company": {
          "name": "Stripe",
          "revenue": 5100000000,
          "sector": "Financial Technology",
          "industry": "Financial Technology"
        },
        "peer_selection": {
          "method": "industry_based",
          "custom_tickers": ["MSFT", "NVDA"]
        },
        "valuation_config": {
          "multiples": ["EV_REVENUE", "EV_EBITDA"],
          "statistics": ["median", "mean"],
          "apply_dlom": false
        }
      }'
```

Response includes a `request_id`, valuation summary, peer analysis, multiple analysis, adjustments, a human-readable audit summary, and metadata. Retrieve the full stored audit with `GET /valuations/{request_id}`.

All a successful valuation call needs is the target company, the revenue, and a sector. the other fields can be all left blank and default values will be chosen. 
---

## 4. Run the MCP Server
```bash
cd /Users/alexanderwang/Projects/modus_take_home
PYTHONPATH=src uv run python -m modus_comps_tool.mcp_server
```

Claude Desktop configuration:
```json
{
  "servers": 
    {
        "modus-comps": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/alexanderwang/Projects/modus_take_home",
                "run",
                "python",
                "-m",
                "modus_comps_tool.mcp_server"
            ],
            "env": {
                "PYTHONPATH": "/Users/alexanderwang/Projects/modus_take_home/src"
            }
        }
    }
}
```

### Tools exposed
- `list_peer_sectors()` → available sector names from the peer universe
- `create_valuation(name, revenue, sector?, industry?, custom_tickers?, apply_dlom?, dlom_percentage?)`
- `get_valuation(request_id)` → full stored valuation (audit + summary)

Once you have claude desktop running and the mcp connected, you can just try asking claude -> "hey for a company named Stripe that makes 5 billion in revenue a year, how much is it worth?" 

Demo Video -> https://drive.google.com/file/d/1tFOtDAMJayg7iayf8N6DhE3HiIBhqShK/view?usp=sharing

---

## 5. Project Structure
```
src/modus_comps_tool/
├── api/                 # FastAPI app & schemas
├── config/              # Environment-aware settings
├── data/                # Peer universe JSON
├── mcp_server.py        # FastMCP entrypoint
├── models/              # Pydantic models (request, peers, audit, multiples)
└── services/            # Peer selection, data fetch, multiples, stats, valuation
```

Artifacts:
- Cached ticker data → `cache/raw/*.json`
- Audit results → `audit_trails/{request_id}.json`

---

## 6. Valuation Logic
1. **Peer pool**: Combine up to 10 peers – prioritize caller-supplied tickers, then fill remaining slots by sector/industry from `peer_universe.json`. If no sector or industry are provided, then no peers will be found and the valuation will return none. If the sector or industry provided are variation of one of the possible sectors, a semantic matching will attempt to match the input sector to a key in the peer universe. If there is a match, the valuation will continue, else no valuation will happen as no peers will be found. 
2. **Fetch data**: For each peer, pull latest market cap, enterprise value, revenue, EBITDA, and related metrics via `yfinance` (cached on disk).
3. **Raw multiples**: Compute EV/Revenue and EV/EBITDA per peer (guarding against missing or negative denominators).
4. **Outlier screen**: Build arrays of multiples, calculate z-scores, and discard peers whose multiples exceed |z| > 2 (≈ two standard deviations from mean). Small samples automatically keep all peers.
5. **Aggregate stats**: On the filtered set, produce mean and median for each multiple type (plus min/max/std dev) using `StatsEngine`.
6. **Apply to target**: Multiply the target company’s revenue and EBITDA by the filtered mean and median multiples to produce implied enterprise values.
7. **Adjustments**: If configured, apply Discount for Lack of Marketability (DLOM) with the supplied percentage.
8. **Audit trail**: Persist raw inputs, filtered peers, statistics, implied values, adjustments, and plain-language narration to `audit_trails/{request_id}.json`.

Every number in the summary is traceable back to the peer metrics stored in the audit file.

| Step | Description | Implemented in |
| --- | --- | --- |
| 1. Peer pool assembly | Manual tickers + sector matches (limit 10) using revenue filters | `services/peer_selector.py`, `models/company.PeerFilters` |
| 2. Data fetch | Cached yfinance pulls for each peer’s market cap, EV, revenue, EBITDA, net income | `services/data_fetcher.py` |
| 3. Multiple calculation | EV/Revenue, EV/EBITDA, with numerator/denominator metadata | `services/multiple_calculator.py` |
| 4. Outlier detection | z-score screening (|z| > 2) to drop statistical outliers | `services/stats_engine.py` |
| 5. Statistical aggregates | Mean/median/min/max/std dev after outlier removal | `services/stats_engine.py`, `services/valuation_service.py::_analyze_multiples` |
| 6. Apply multiples | Multiply filtered stats by target revenue/EBITDA for implied EVs | `services/valuation_service.py::_summarize_results` |
| 7. DLOM adjustments | Optional discount for lack of marketability (percentage-based) | `services/valuation_service.py::_summarize_results` |
| 8. Audit persistence | Store calculation steps, metadata, narrative | `services/valuation_service.py::_build_audit_trail`, `models/audit.py` |

**Note that the audit trail is built up throughout the steps above as to keep track of what is going on sequentially**

---

## 7. Logging & Observability
- Structured logging via `structlog` (`utils/logging.py`)
- Events include cache hits/misses, peer selection notes, raw `yfinance` payloads, z-score filtering, implied valuation math, and audit persistence.
- For LLM usage, banner printing is disabled and FastMCP logging can be silenced by setting `FASTMCP_LOG_ENABLED=0`.

---

## 8. Testing & Tooling
  
- Run all unit tests:

  `uv run pytest tests/unit/ -v`

- Run with coverage report:

  `uv run pytest tests/unit/ --cov=src/modus_comps_tool/services --cov-report=term-missing`

- Run specific test file:

  `uv run pytest tests/unit/test_stats_engine.py -v`
  `uv run pytest tests/unit/test_multiple_calculator.py -v`
  `uv run pytest tests/unit/test_peer_selector.py -v`

- Run a specific test:

  `uv run pytest tests/unit/test_stats_engine.py::TestStatsEngine::test_summarize_with_normal_data -v`

- Suggested commands:
  - `uv run ruff check`
  - `uv run mypy`
- Clear cached financials by removing `cache/raw/*.json`.

---

## 9. Known Limitations
- Peer universe is finite; unfamiliar sectors yield empty peer sets.
- `yfinance` occasionally omits EBITDA or enterprise value; audit notes capture gaps.
- Valuation outputs are illustrative and not market-calibrated.
- MCP transport uses stdio; ensure no other stdout output is interleaved by your MCP client.

---

## 10. License
Prepared as part of the Modus take-home assessment. Use and share responsibly.