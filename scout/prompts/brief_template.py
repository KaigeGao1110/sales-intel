"""Prompt templates for brief generation."""

from datetime import datetime

SYSTEM_PROMPT = """You are Scout, an expert sales intelligence analyst.
Your job is to analyze company research data and generate concise, actionable
sales briefs that help salespeople understand a prospect's situation and needs.

Focus on:
- Identifying real business problems from signals (not speculation)
- Connecting problems to likely solution categories
- Providing specific, natural conversation starters
- Being honest about confidence levels

Format: Always return clean Markdown. Be specific, not generic."""


def build_brief_prompt(company_name: str, research_data: dict) -> str:
    """Build the user prompt for brief generation.

    Args:
        company_name: Name of the company.
        research_data: Structured research dict from ResearchAgent.

    Returns:
        Formatted prompt string.
    """
    news = research_data.get("news", [])
    jobs = research_data.get("jobs_signal", {})
    funding = research_data.get("funding", {})
    reviews = research_data.get("reviews_signal", {})
    enrichment = research_data.get("enrichment", {})
    raw_signals = research_data.get("raw_signals", [])

    news_block = "\n".join(
        [f"- [{n.get('published_date', '')}] {n.get('title', '')}: {n.get('description', '')}"
         for n in news[:10]]
    ) or "No recent news found."

    jobs_block = f"""
- Hiring signal: {jobs.get('signal', 'unknown')}
- Total job postings detected: {jobs.get('total_postings', 'N/A')}
- Keywords: {', '.join(jobs.get('keywords', []))}
""".strip()

    funding_block = f"""
- Last round: {funding.get('last_round', 'Unknown')}
- Amount: {funding.get('amount', 'Unknown')}
- Date: {funding.get('date', 'Unknown')}
""".strip()

    reviews_block = f"""
- Sentiment: {reviews.get('sentiment', 'neutral')}
- Recent negative signals: {reviews.get('recent_negative', 0)}
""".strip()

    enrichment_block = ""
    if enrichment:
        enrichment_block = f"""
### Company Profile (from Clearbit)
- Industry: {enrichment.get('industry', 'Unknown')}
- Employees: {enrichment.get('employee_count', 'Unknown')}
- Location: {enrichment.get('location', 'Unknown')}
- Description: {enrichment.get('description', 'N/A')}
""".strip()

    signals_block = "\n".join(
        [f"- {s}" for s in raw_signals[:15]]
    ) or "No raw signals."

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""Generate a sales intelligence brief for: **{company_name}**
Research Date: {today}

## Raw Research Data

### Recent News
{news_block}

### Jobs & Hiring Signal
{jobs_block}

### Funding Data
{funding_block}

### Reviews & Sentiment
{reviews_block}

{enrichment_block}

### Additional Signals
{signals_block}

---

## Instructions

Using the research data above, generate a 1-page sales brief in this EXACT format:

```markdown
# Company Brief: {company_name}

## 1. Company Overview
[3 sentences: industry, size, location, what they do]

## 2. Current Challenges
**HIGH CONFIDENCE: [Challenge Name] (Score: X/10)**
- Evidence point 1
- Evidence point 2

**MEDIUM CONFIDENCE: [Challenge Name] (Score: X/10)**
- Evidence point 1

## 3. Recent Signals (Last 3-6 months)
- [Signal 1] - [what it means for sales]
- [Signal 2] - [what it means for sales]

## 4. Likely Solutions Needed
1. **[Solution Category]** - [specific features or capabilities]
2. **[Solution Category]** - [specific features or capabilities]

## 5. Conversation Starters
- "..."
- "..."
- "..."

## 6. Risk Factors
- [Why they might not buy]
- [Current vendor lock-in or timing issues]

---
Generated: {today} | Confidence: Based on [X] data sources
```

Use ONLY evidence from the research data. Do not invent facts.
If data is limited, say so in the confidence score.
Return only the markdown brief, no additional commentary."""

    return prompt


def build_rule_based_brief(company_name: str, research_data: dict) -> str:
    """Generate a simple brief without LLM when no API key is available.

    Args:
        company_name: Name of the company.
        research_data: Structured research dict.

    Returns:
        Markdown brief string.
    """
    from datetime import datetime

    news = research_data.get("news", [])
    jobs = research_data.get("jobs_signal", {})
    funding = research_data.get("funding", {})
    reviews = research_data.get("reviews_signal", {})
    enrichment = research_data.get("enrichment", {})
    today = datetime.now().strftime("%Y-%m-%d")

    # Build challenges from signals
    challenges = []
    job_signal = jobs.get("signal", "")
    if job_signal == "layoffs":
        challenges.append(
            "**HIGH CONFIDENCE: Cost Reduction Mode (Score: 9/10)**\n"
            "- Layoff signals detected in job/news data\n"
            "- Company likely prioritizing ROI and efficiency"
        )
    elif job_signal == "rapid_hiring":
        challenges.append(
            "**HIGH CONFIDENCE: Scaling Operations (Score: 8/10)**\n"
            "- Strong hiring signals detected\n"
            "- Company likely needs automation and onboarding tools"
        )

    if funding.get("last_round") not in ("Unknown", "", None):
        challenges.append(
            f"**MEDIUM CONFIDENCE: Growth Investment (Score: 6/10)**\n"
            f"- Recent funding: {funding.get('last_round')} {funding.get('amount', '')}\n"
            "- Budget likely available for new tools"
        )

    if reviews.get("recent_negative", 0) > 2:
        challenges.append(
            "**MEDIUM CONFIDENCE: Customer Experience Issues (Score: 6/10)**\n"
            "- Multiple negative review signals detected\n"
            "- May need CX improvement solutions"
        )

    challenges_block = "\n\n".join(challenges) if challenges else (
        "**LOW CONFIDENCE: Insufficient data for specific challenge identification**\n"
        "- Recommend gathering more information before outreach"
    )

    # Build signals
    signals = []
    for n in news[:5]:
        title = n.get("title", "")
        if title:
            signals.append(f"- {title}")
    if not signals:
        signals.append("- No recent news signals found")

    # Build conversation starters
    starters = [
        f'- "I noticed some recent activity at {company_name} — I\'d love to understand how your team is handling [relevant challenge]."',
        f'- "What\'s the biggest operational challenge your team is focused on right now?"',
        f'- "How are you currently approaching [solution category] — is that something you\'ve invested in recently?"',
    ]

    # Source count
    source_count = sum([
        1 if news else 0,
        1 if jobs else 0,
        1 if funding else 0,
        1 if enrichment else 0,
    ])

    industry = enrichment.get("industry", "technology")
    employees = enrichment.get("employee_count", "unknown size")
    location = enrichment.get("location", "unknown location")
    description = enrichment.get("description", f"{company_name} is a company in the {industry} sector.")

    brief = f"""# Company Brief: {company_name}

## 1. Company Overview
{description} Based in {location}, the company has approximately {employees} employees and operates in the {industry} sector. This brief is based on automated signal analysis.

## 2. Current Challenges
{challenges_block}

## 3. Recent Signals (Last 3-6 months)
{chr(10).join(signals)}

## 4. Likely Solutions Needed
1. **Operational Efficiency** - Automation tools, workflow optimization
2. **Data & Analytics** - Better visibility into performance metrics

## 5. Conversation Starters
{chr(10).join(starters)}

## 6. Risk Factors
- Limited public data may mean timing is uncertain
- Unknown current vendor relationships

---
Generated: {today} | Confidence: Based on {source_count} data source(s) | Mode: Rule-based (no LLM key)
"""
    return brief
