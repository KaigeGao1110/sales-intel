# 17 Company Validation Summary

**Date:** 2026-04-06 11:51
**Total Duration:** ~7.5 minutes (avg 26.5s/company)

## Per-Company Results

| # | Company | Type | Funding | News | Jobs | Signal |
|---|---------|------|---------|------|------|--------|
| 1 | Anthropic | PRIVATE | unknown | 5 | Unknown | STABLE |
| 2 | Apple | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 3 | Atlassian | PRIVATE | unknown | 5 | 2 | STABLE |
| 4 | Canva | PRIVATE | unknown | 5 | Unknown | STABLE |
| 5 | Databricks | PRIVATE | unknown | 5 | Unknown | STABLE |
| 6 | Figma | PRIVATE | unknown | 5 | Unknown | CONTRACTION |
| 7 | HubSpot | PRIVATE | unknown | 5 | Unknown | STABLE |
| 8 | Linear | PRIVATE | unknown | 5 | Unknown | STABLE |
| 9 | Notion | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 10 | OpenAI | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 11 | Salesforce | PRIVATE | unknown | 5 | 2 | EXPANSION |
| 12 | Shopify | PRIVATE | unknown | 5 | Unknown | STABLE |
| 13 | Slack | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 14 | Snowflake | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 15 | Stripe | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 16 | Twilio | PRIVATE | unknown | 5 | Unknown | EXPANSION |
| 17 | Vercel | PRIVATE | unknown | 4 | 1 | STABLE |

## Overall Success Rates

| Category | Success | Rate |
|----------|---------|------|
| **Funding** | 0/17 | 0% |
| **News** | 17/17 | 100% |
| **Jobs** | 3/17 | 18% |

- **Avg duration:** 26.5s/company
- **Total news articles:** 84 (avg 4.9/company)

## Job Signal Distribution

- STABLE: 8 companies
- EXPANSION: 8 companies
- CONTRACTION: 1 company (Figma)

## Critical Issues

### 1. Funding: 0% Success Rate — PUBLIC/PRIVATE CLASSIFICATION BROKEN
All 17 companies are classified as PRIVATE, including clearly public companies:
- Apple (AAPL) — public
- Salesforce (CRM) — public
- Snowflake (SNOW) — public
- HubSpot (HUBS) — public
- Atlassian (TEAM) — public
- Shopify (SHOP) — public
- Slack (WORK) — public
- Twilio (TWLO) — public

**Root cause:** The CLI does not pass ticker/company type to the funding scraper. Yahoo Finance is never queried because the system treats all companies as private. Even when tickers are provided via `--ticker`, the classification logic is bypassed or the funding scraper ignores it.

**Impact:** Funding data (total raised, stage, valuation, investors) is completely unavailable for all companies.

### 2. Jobs: 82% Unknown — LinkedIn Blocking
Only 3/17 companies returned job counts (Atlassian: 2, Salesforce: 2, Vercel: 1). The remaining 14 return "Unknown" because LinkedIn is blocking scrapers.

### 3. Cache Files Contain No Real Data
All 17 `cache/funding_*.json` files are 635-645 bytes with identical "unknown" structure. Yahoo Finance is not being called for any company.

## Recommendations

1. **Fix public/private classification** — Pass `is_public` and `ticker` from CLI args to the funding scraper. If ticker is provided and company is a known public entity, query Yahoo Finance.
2. **Add fallback for private company funding** — Use web search / news API to find funding rounds for private companies instead of relying solely on Yahoo Finance.
3. **Fix jobs scraper** — Either use a different job data source (Indeed, Greenhouse, Lever API) or implement better LinkedIn scraping bypass.
4. **Add validation assertions** — Automated tests should verify that known public companies return non-unknown funding data.
