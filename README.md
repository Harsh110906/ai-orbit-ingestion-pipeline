# AI Orbit Ingestion Pipeline

## 1. Project Objective
This is a production-oriented AI data ingestion pipeline designed to scrape, extract, normalize, and resolve 10 distinct modules: AI Tools, Companies, Models, Agents, MCP Servers, Robots, Devices, Research Papers, News, and Jobs. It prioritizes data provenance, structured schema enforcement, and resilient failure recovery.

## 2. Architecture
- **Crawling Layer**: `aiohttp` for async HTTP, integrated with exponential backoff and jitter for rate-limit protection.
- **Extraction Layer**: LLM fallback waterfall (OpenAI -> Gemini -> Groq -> DeepSeek) driven by Pydantic schemas via `instructor`.
- **Entity Resolution Layer**: Deterministic deduplication across Name, URL, Aliases, and Fuzzy thresholds.
- **Storage Layer**: Automated JSON and canonical CSV generation suitable for direct DB or Google Sheets ingestion.

See `docs/architecture.pdf` for the full 500k+ scaling strategy and pipeline diagrams.

## 3. Directory Structure
- `src/ai_orbit/crawling/`: Retry logic and HTTP semaphores
- `src/ai_orbit/discovery/`: Real adapters for GitHub, HuggingFace, RSS, Remotive
- `src/ai_orbit/llm/`: Chunking algorithms and Orchestrator waterfall
- `src/ai_orbit/validation/`: 10 strict Pydantic models mapping to PDF guidelines
- `src/ai_orbit/entity_resolution/`: Graph and exact/fuzzy deduplication
- `docs/`: Audit and architecture reports
- `tests/`: 8 Pytest suites spanning the pipeline logic

## 4. Installation
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -e .
```

## 5. Environment Variables
Copy `.env.example` to `.env` and fill in API keys:
- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`
- Note: If no keys are provided, the system intelligently defaults to a `_mock_fallback` mode allowing demonstration of the pipeline's control flow and extraction logic without cost.

## 6. Running Demo
```bash
python run.py --mode demo --module all
```

## 7. Running Individual Modules
```bash
python run.py --mode demo --module agents
python run.py --mode demo --module models
python run.py --mode demo --module news
# Available modules: all, tools, papers, companies, news, agents, mcp, devices, robots, models, jobs
```

## 8. Data Sources
The pipeline intentionally avoids fabricating data. If primary targets (e.g. OpenAI website) return 403 blocks, it logs it and defaults to legitimate public endpoints:
- **Models**: HuggingFace Public API
- **Papers**: arXiv Atom/RSS Feed
- **News**: TechCrunch and The Verge RSS (<24h freshness enforced)
- **Jobs**: Remotive API (<24h freshness enforced)
- **Agents/MCP/Devices/Robots/Companies/Tools**: GitHub Search API parsing raw Readmes.

## 9. Limitations
- Without Playwright (a headless browser implementation), high-profile sites like Perplexity and TAAFT block `aiohttp` via Cloudflare/Datadome (returning 403s). 
- To prevent pipeline failure, GitHub topics (`ai-agents`, `mcp-server`, etc.) are used to supplement data discovery.
- The free GitHub API has aggressive rate limits (10 req/min).

## 10. Testing
Run tests spanning normalization, chunking, deduplication, schema validation, and freshness logic:
```bash
python -m pytest tests/ -v
```

## 11. Exact Current Record Counts (Demo Mode)
- Papers: 10
- Companies: 5
- Tools: 5
- Agents: 5
- MCP: 5
- Models: 5
- Robots: 5
- Devices: 5
- News: ~5-15 (Depending on live RSS 24h freshness)
- Jobs: ~0-10 (Depending on live Remotive 24h freshness)
