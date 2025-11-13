# Modus Comps Tool

## Overview

- Problem: Auditors need to estimate the fair value of private venture capital portfolios that are composed of companies that lack market prices and often have sparse, non-standardized financial data. The goal of this project is to create a structured, auditable workflow that helps auditors easily and efficiently produce consistent, well-documented valuations using available data sources. Unlike public companies with readily available market prices, private companies require a systematic approach to arrive at defensible fair value estimates.
- Methodology: Comparable-company (Comps) valuations for private firms.
- Approach: Combine automated sector-based peer company selection with optional manual tickers, hydrate publically traded peers via `yfinance`, compute EV/Revenue and EV/EBITDA multiples for each peer, filter outliers (|z| > 2), obtain the mean and median multiples for both EV/Revenue and EV/EBITDA and multiply by the given company's revenue and EBITDA. During each step, assemble a step-by-step audit trail saved to disk.
- Outcome: FastAPI API and MCP server expose both the valuation summary and retrievable audit details for auditors.

## Detailed Approach

1. **Peer pool**: Combine up to 10 peers – prioritize caller-supplied tickers, then fill remaining slots by sector/industry from `peer_universe.json`. If no sector or industry are provided, then no peers will be found and the valuation will return none. If the sector or industry provided are variation of one of the possible sectors, a semantic matching will attempt to match the input sector to a key in the peer universe. If there is a match, the valuation will continue, else no valuation will happen as no peers will be found. 
2. **Fetch data**: For each peer, pull latest market cap, enterprise value (which can be different than market cap so we will use this in multiple calculations), revenue, EBITDA, and related metrics via `yfinance` (cached on disk).
3. **Raw multiples**: Compute EV/Revenue and EV/EBITDA per peer (guarding against missing or negative denominators).
4. **Outlier screen**: Build arrays of multiples, calculate z-scores, and discard peers whose multiples exceed |z| > 2 (≈ two standard deviations from mean). Small samples automatically keep all peers.
5. **Aggregate stats**: On the filtered set, produce mean and median for each multiple type (plus min/max/std dev) using `StatsEngine`.
6. **Apply to target**: Multiply the target company’s revenue and EBITDA by the filtered mean and median multiples to produce implied enterprise values.
7. **Adjustments**: If configured, apply Discount for Lack of Marketability (DLOM) with the supplied percentage.
8. **Audit trail**: Persist raw inputs, filtered peers, statistics, implied values, adjustments, and plain-language narration to `audit_trails/{request_id}.json`.

## Key Design Decisions & Tradeoffs
- **MCP + Multiple APIs**: By allowing the end user to have access to multiple API's that not only allow an evaluation to be performed but also saved so that the audit trail can be recovered later allows the auditor greater flexibility over how they use this tool. Additionally, the MCP allows the auditor to ask in plain text these evaluation questions without having to understand how to call an API. This does add complexity and can be added steps to set up for the user. However, by still exposing the underlying functionality through an API, more tech savy users can still use the same service as well. 
- **`yfinance` data source**: This dataset requires no API keys and is widely available and easy to cache. Was chosen for its ease of use and implementation. However the accuracy depends on Yahoo Finance updates so there are definitely cases of missing data. Furthermore, relying on just one API would cause a large dependecy issue if for some reason yahoo finance ever went down as well. 
- **EV/Revenue and EV/EBITDA as main multiples**: I chose to use these two calculation methods for the comparisons between companies as they are the standard ones done throughout the industry. However, some of these numbers are very dependent on the specific company and can be over inflated which I discovered through testing so I decided to remove the outliers if the multiple was over two standard deviations from the other peers. This way we can get a more wholistic view of the peers rather than a single peer affecting the valution tremendously. 
- **`peer_universe.json`**: This central peer dataset was scraped using LLMs and personal google searching. It is by no means complete and the total sectors could be substantially wider as well as more in depth. However, the time and energy it would take to create such a dataset was not possible given the time limit. An LLM based approach could have been possible as well where given a company name, an LLM could be the one suggest all the relevant publically traded companies to compare it; however, I believe in auditing, a deterministic result is prefered in most cases as that produces the most auditable trail. This is why I avoided going down that route, but also added the MCP functionality so the flexibility and power of an LLM could still be used to help find peers. 
- **Disk-backed JSON caching**: Chose to cache the audit trails on disk in order because it is simple, transparent, and auditable. However, it does lack the scaling benefits of distributed cache and also depending if this service is running in a stateless solution or on someones local machine, there could be added complexities with how the files are stored and retrieved.
- **Audit trail first**: I decided to create the audit trail as the valuation took place every step. This allows for future steps to be easily added or removed rather than building an audit trail at the end of a valuation. Storing this audit trail does create a relatively large json (1000 lines) that is stored on disk, but I believe the storage tradeoff to be worth the clear and easily traceable audit trail that is produced. 
- **Semantic sector matching**: I wanted to account for cases where auditors may mistype or not know the exact sector of a private company, so in those cases I decided to use basic semantic matching to determine if their input is close to one of the known sectors in our dataset. This can occasionally mislabel the sector of a company, but because these valuations can be done again and all of the peers are illustrated in the audit trail.  

## Setup
```bash
git clone git@github.com:awanga123/modus_private_company_valuation_tool.git
cd modus_private_company_valuation_tool
uv sync
```

### Run FastAPI
```bash
PYTHONPATH=src uv run uvicorn modus_comps_tool.api.app:app --reload --host 127.0.0.1 --port 8000
```

### Example Valuation Request
```bash
curl -X POST "http://127.0.0.1:8000/valuations" \
  -H "Content-Type: application/json" \
  -d '{
        "target_company": {"name": "Stripe", "revenue": 5100000000, "sector": "Financial Technology"},
        "peer_selection": {"method": "industry_based", "custom_tickers": ["MSFT", "NVDA"]},
        "valuation_config": {"multiples": ["EV_REVENUE", "EV_EBITDA"], "statistics": ["median", "mean"]}
      }'
```
Result includes a `request_id` for fetching the full audit via `GET /valuations/{request_id}`.

### Run the MCP Server
```bash
cd modus_private_company_valuation_tool
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
                "/Users/alexanderwang/Projects/modus_private_company_valuation_tool", // replace with your own source path where you run the mcp
                "run",
                "python",
                "-m",
                "modus_comps_tool.mcp_server"
            ],
            "env": {
                "PYTHONPATH": "/Users/alexanderwang/Projects/modus_private_company_valuation_tool/src" // make sure to include this as well with the /src 
            }
        }
    }
}
```

## Potential Improvements
- Improve the peer_universe.json dataset to have a much more wholistic view of all the publically traded companies and sectors out there, this would greately improve the accuracy of the model. This could be done through web scraping with the help of LLMs to tag and label the companies scraped. 
- Introduce multiple data providers with reconciliation to reduce reliance on a single API. Additionally I would make these calls run in a batch so that they are not called sequentially to speed up this data fetching process.
- Add additional multiple types and statistics. Currently it is hard coded to just EV/Revenue and EV/EBITDA where you could also inclue PE ratio and a bunch of other financial benchmarks to value the company. 
- Better testing both unit and integration wise
- Create a simple browser UI for interactive peer selection and audit browsing.
- Use a real databse to store the information regarding the peers as well as the caching system for stored audits, so that they can be saved for longer than 24 hours. 

## Workflow and Demo

Demo Video -> https://drive.google.com/file/d/1tFOtDAMJayg7iayf8N6DhE3HiIBhqShK/view?usp=sharing

- A simple flow goes: **Request → Peer Selector → Data Fetcher → Multiple Calculator → Stats Engine → DLOM Adjuster → Audit Persistence → Response**.
