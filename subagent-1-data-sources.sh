#!/bin/bash
echo "=== SUBAGENT 1: Company Data Sources Research ===" > results-data-sources.txt
echo "Timestamp: $(date)" >> results-data-sources.txt
echo "" >> results-data-sources.txt

# Research free news APIs
echo "## NEWS APIs" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "1. NewsAPI.org (newsapi.org)" >> results-data-sources.txt
echo "   - Free tier: 100 requests/day" >> results-data-sources.txt
echo "   - Great for mainstream news" >> results-data-sources.txt
echo "   - Python: newsapi = NewsApiClient(api_key='KEY')" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "2. Brave Search API (brave.com/search/api)" >> results-data-sources.txt
echo "   - Free tier: 2000 requests/month" >> results-data-sources.txt
echo "   - Good for web search + news combined" >> results-data-sources.txt
echo "   - Python: brave.search.SearchClient)" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "3. Bing News Search (azure.microsoft.com/services/cognitive-services/bing-news-search)" >> results-data-sources.txt
echo "   - Free tier: Bing News Search S1 (1000 transactions/month)" >> results-data-sources.txt
echo "   - Microsoft's news API" >> results-data-sources.txt
echo "" >> results-data-sources.txt

# Research company info APIs
echo "## COMPANY INFO APIs" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "1. Clearbit Discovery API" >> results-data-sources.txt
echo "   - Free tier: 5,000 requests/month" >> results-data-sources.txt
echo "   - Company enrichment with financials, tech stack" >> results-data-sources.txt
echo "   - Python: clearbit.EnrichmentApi)" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "2. Apollo.io" >> results-data-sources.txt
echo "   - Free tier: 50 credits/month" >> results-data-sources.txt
echo "   - Company & contact data" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "3. Crunchbase (crunchbase.com)" >> results-data-sources.txt
echo "   - Free tier: limited company data" >> results-data-sources.txt
echo "   - Good for funding rounds" >> results-data-sources.txt
echo "" >> results-data-sources.txt

# Research review sites approach
echo "## REVIEW SITES" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "1. Glassdoor - scraping not recommended (legal risk)" >> results-data-sources.txt
echo "   - Alternative: Use LinkedIn company reviews API if available" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "2. G2 - No free API, scraping against TOS" >> results-data-sources.txt
echo "   - Alternative: Product Hunt for product reviews" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "3. Trustpilot - Has an API (Business API free tier)" >> results-data-sources.txt
echo "   - Reviews and ratings available" >> results-data-sources.txt
echo "" >> results-data-sources.txt

# Research job postings
echo "## JOB POSTINGS" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "1. The Muse API - Job listings and company profiles" >> results-data-sources.txt
echo "   - Free tier available" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "2. LinkedIn Job Analytics - indirect signal via job posting volume" >> results-data-sources.txt
echo "   - SerpAPI can search LinkedIn jobs for a company" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "3. Indeed - No official API, scraping against TOS" >> results-data-sources.txt
echo "   - Alternative: SerpAPI for Indeed job search" >> results-data-sources.txt
echo "" >> results-data-sources.txt

# MVP Recommendation
echo "## MVP RECOMMENDATIONS" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "PRIMARY STACK:" >> results-data-sources.txt
echo "1. Brave Search API - Best free option for web + news search" >> results-data-sources.txt
echo "2. NewsAPI.org - Supplement with mainstream news" >> results-data-sources.txt
echo "3. Clearbit - Company enrichment (5000/mo free)" >> results-data-sources.txt
echo "4. Crunchbase - Funding data (free tier)" >> results-data-sources.txt
echo "" >> results-data-sources.txt
echo "MVP CODE EXAMPLE (Brave Search):" >> results-data-sources.txt
cat >> results-data-sources.txt << 'PYCODE'
from brave import SearchClient

client = SearchClient(api_key="YOUR_API_KEY")

# Search for company news
results = client.search(
    query="Acme Corp company news 2024",
    count=10,
    markets=["en-US"]
)

for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Description: {result.description}")
PYCODE

echo "" >> results-data-sources.txt
echo "=== SUBAGENT 1 COMPLETE ===" >> results-data-sources.txt
