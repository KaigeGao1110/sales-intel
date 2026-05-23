# Scout Tool Selection Guide

> Based on third-party benchmarks and official documentation, compiled 2026-04-06.
> Sources: AIMMultiple Agentic Search Benchmark, Firecrawl Best Web Search APIs 2026,
> NewsData.io News API Comparison, BrightData Job APIs, Brave Search API docs.

---

## 1. General Web Search APIs

### AIMMultiple Benchmark (100 queries, 4000 results, LLM judge)

| Rank | Tool | Agent Score | Mean Relevant | Quality | Latency |
|------|------|:-----------:|:-------------:|:-------:|:-------:|
| 1 | **Brave Search** | **14.89** | 3.84 | 3.88 | 669ms |
| 2 | Firecrawl | 14.58 | 4.30 | 3.39 | 1,335ms |
| 3 | Exa | ~14.5 | - | - | ~1.2s |
| 4 | Parallel Search Pro | ~14.4 | - | - | 13,600ms |
| 5 | **Tavily** | **~13.9** | - | - | ~800ms |
| 6 | Serper | - | - | - | - |

**Key finding:** Brave consistently outperforms Tavily by ~1 point. Top 4 APIs are statistically tied.
Latency varies 20× (669ms Brave vs 13.6s Parallel Pro). Sub-second matters for agent workflows.

### Best Use Cases by Tool

| Tool | Best For | Avoid |
|------|----------|-------|
| **Brave Search** | General search, factual queries, speed-critical agents | Deep content extraction |
| **Tavily** | AI agent integration (LangChain/LlamaIndex built-in), RAG | Budget-sensitive (acquired by Nebius Feb 2026, pricing uncertain) |
| **Exa** | Semantic search, research-heavy tasks, RAG | Simple fact lookup |
| **Firecrawl** | Full page content extraction, dynamic sites | Fast SERP-only results |
| **WebSearchAPI.ai** | Google-powered RAG-ready results, structured extraction | Free tier limited (100/mo) |
| **Serper** | Affordable Google SERP access | Advanced features |

### Pricing (per 1K queries)

| Tool | Free Tier | Paid |
|------|-----------|------|
| Brave Search | 2,000/mo (non-commercial) | $5/1K |
| Tavily | 1,000/mo | ~$40/1K |
| Exa | 1,000/mo | $28/1K |
| Firecrawl | 500/mo | $30/1K |
| Serper | 2,500/mo | $50/1K |

---

## 2. News-Specific APIs

| Tool | Sources | Free Tier | Best For |
|------|---------|-----------|----------|
| **Google News RSS** | 50K+ (global) | **Unlimited, free** | Broad coverage, quick filtering, real-time |
| NewsData.io | 87K+ sources, 206 countries | 200/day | Global coverage, sentiment analysis |
| NewsAPI.org | 150K+ sources, 5yr history | 100/day (dev), no commercial | Historical data, simple integration |
| GNews API | 60K+ sources, 22 languages | 100/day | Simple REST API, historical access |
| MediaStack | 7K+ sources | 100/day | Budget news monitoring |
| Perigon | AI-powered, 1M articles/day | Limited trial | Enterprise-scale, trend analysis |

### Google News RSS — Why It's Our Primary
- **Free and unlimited** — no API key, no rate limit concerns for our scale
- **Real-time** — articles appear within minutes of publication
- **Filterable** — by keyword, language, region, time range
- **Unofficial but stable** — Google has not shut it down despite lack of docs
- **Limitation** — no structured metadata (sentiment, category classification) beyond what's in the feed

### When NOT to Use Google News RSS
- Need historical data beyond what RSS provides
- Need sentiment analysis built-in → use NewsData.io or Perigon
- Need structured JSON responses → use GNews API or NewsAPI.org

---

## 3. Financial / Funding Data

| Tool | Data Type | Cost | Best For | Notes |
|------|-----------|------|----------|-------|
| **Yahoo Finance (unofficial)** | Market data, fundamentals | **Free** | Public company financials | ⚠️ Unofficial API, endpoints change, rate limiting, may block heavy use |
| **Alpha Vantage** | Stocks, forex, crypto | Free: 25/day; Premium: $50/mo | Programmatic stock data | Reliable free tier but very limited |
| **Tiingo** | EOD/real-time stocks, crypto | Free: 1,000/day; Premium: $15/mo | IEX-based stock data | Good free tier, institutional-grade data |
| **Finnhub** | Stocks, forex, crypto, news | Free: 60/min | Real-time market data | Generous free tier |
| **Crunchbase (via search)** | Funding rounds, valuations | **Free (search)** | Private company funding | No free API; must scrape/search |
| **Clearbit → HubSpot Breeze** | Company data, technographics | Acquired, standalone sunset Apr 2025 | B2B enrichment | No longer available standalone |

### Yahoo Finance — Use With Caution
- **Pros:** Free, comprehensive (market cap, revenue, employees, sector, financial ratios)
- **Cons:** Unofficial API that breaks frequently, Yahoo changes endpoints without notice, rate limiting/blacklisting with heavy use
- **Recommendation:** Use for prototyping and low-volume lookups. For production, plan to switch to Tiingo or Finnhub.

### For Private Company Funding
No reliable free API exists. Options:
1. **Web search** with date filtering — best free option
2. **Crunchbase search** — manual lookups, no API on free tier
3. **Growjo API** — free, focused on fast-growing companies

---

## 4. Job Market Data

| Tool | Sources | Cost | Best For | Notes |
|------|---------|------|----------|-------|
| **JobSpy (Python lib)** | LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter | **Free (open source)** | Multi-source job aggregation | ⚠️ Scraping-based, may break; supports `hours_old` filter |
| **BrightData Job Scraper** | LinkedIn, Indeed, Glassdoor | $1.50/1K records | Enterprise-scale scraping | Managed proxy infrastructure |
| **TheirStack** | LinkedIn, Indeed, Glassdoor + 325K ATS | Paid | Most comprehensive coverage | Combines many sources |
| **LinkedIn Official API** | LinkedIn only | Free (limited) | Official, compliant access | Very restricted; requires LinkedIn partnership |
| **Indeed RSS** | Indeed only | **Free** | Quick Indeed job counts | Simple but limited to one source |
| **Apify LinkedIn Scraper** | LinkedIn | From $49/month | Managed scraping | Turnkey solution |

### JobSpy — Why It's Our Primary
- **Free and open source** (`pip install python-jobspy`)
- **Multi-source**: LinkedIn + Indeed + Glassdoor + Google + ZipRecruiter in one call
- **Time filtering**: `hours_old=72` parameter for recent postings
- **Company-level search**: `site_name=["linkedin"]`, `location`, `search_term`
- **Limitation**: Scraping-based, LinkedIn anti-bot may block; need proxies for heavy use

### When NOT to Use JobSpy
- Need historical trends → use TheirStack or official APIs
- Need guaranteed reliability → use BrightData or Apify (paid)
- High volume (>100 searches/day) → scraping will get blocked

---

## 5. Scout Tool Registry (Recommended Configuration)

Based on the benchmarks above, here's the recommended tool configuration:

```python
TOOL_REGISTRY = {
    # === NEWS ===
    "news": {
        "primary": "google_news_rss",       # Free, unlimited, real-time
        "fallback": ["brave_search", "tavily"],
        "force": False,
        "best_for": "Broad news coverage, time-filtered results",
        "avoid_for": "Historical analysis, sentiment analysis"
    },

    # === FUNDING ===
    "funding_public": {
        "primary": "yahoo_finance",          # Free, comprehensive for public co.
        "fallback": ["alpha_vantage", "tiingo"],
        "force": True,                       # Don't guess public company data
        "best_for": "Market cap, revenue, employees, sector",
        "avoid_for": "Heavy production use (unofficial API)",
        "production_upgrade": "Tiingo ($15/mo) or Finnhub"
    },

    "funding_private": {
        "primary": "brave_search",           # Best search accuracy per benchmark
        "fallback": ["tavily"],
        "force": False,
        "best_for": "Funding rounds, valuations for private co.",
        "avoid_for": "Real-time data (search results may be cached)"
    },

    # === JOBS ===
    "jobs": {
        "primary": "jobspy",                 # Free, multi-source, time-filtered
        "fallback": ["indeed_rss", "brave_search"],
        "force": False,
        "best_for": "Job counts, recent postings, department breakdown",
        "avoid_for": "High-volume (>100/day), historical trends",
        "production_upgrade": "BrightData ($1.50/1K) or TheirStack"
    },

    # === GENERAL SEARCH ===
    "general_search": {
        "primary": "brave_search",           # #1 in AIMMultiple benchmark, fastest
        "fallback": ["tavily"],
        "force": False,
        "best_for": "Factual queries, company research, speed-critical tasks",
        "avoid_for": "Deep content extraction (use web_fetch instead)"
    }
}
```

---

## 6. OpenClaw Agent Tool Mapping

For the OpenClaw-based Scout cron, the agent has access to these built-in tools:

| OpenClaw Tool | Equivalent To | Scout Use Case |
|---------------|--------------|----------------|
| `web_search` | Brave Search API | General search, funding (private co.), news fallback |
| `web_fetch` | Direct HTTP fetch | Google News RSS parsing, page content extraction |
| `exec` | Shell commands | Running JobSpy, curl to APIs |

### Recommended Agent Prompt Pattern

```
For NEWS: always use web_fetch with Google News RSS URL first.
  Fallback: web_search with freshness="week" and date_after params.
  Never skip the RSS step.

For PUBLIC COMPANY DATA: use exec to run funding.py (which calls Yahoo Finance).
  Fallback: web_search for the ticker symbol if not in TICKER_MAP.

For PRIVATE COMPANY FUNDING: use web_search with date_after="2025-01-01".
  Cross-reference at least 2 sources before recording.

For JOBS: use exec to run jobs.py (which uses JobSpy).
  Fallback: web_search "{company} jobs careers site:linkedin.com" with freshness="month".

For GENERAL RESEARCH: use web_search (Brave Search API) as default.
  Add web_fetch to read specific pages when search results are insufficient.
```

---

*Last updated: 2026-04-06. Re-evaluate quarterly as APIs change pricing/features.*
