#!/usr/bin/env python3
"""
Meeting Prep Report Generator for Scout.

Takes funding + news + jobs output and generates:
- Meeting prep brief (Slack/Telegram friendly)
- Sections: Overview, Latest Developments (max 5), Job Signals, Talking Points
- Every claim has source link + confidence level (HIGH/MEDIUM/LOW)
"""

from datetime import datetime
from typing import Optional

from scrapers.funding import get_funding_info
from scrapers.news import get_recent_news, format_news_brief
from scrapers.jobs import get_job_signals, format_jobs_brief


def generate_report(
    company_name: str,
    domain: Optional[str] = None,
    ticker: Optional[str] = None,
    company_type: str = "auto",
    output_format: str = "brief"
) -> dict:
    """
    Generate a complete company intelligence report.

    Args:
        company_name: Company name
        domain: Company domain
        ticker: Stock ticker if public
        company_type: "public", "private", or "auto"
        output_format: "brief", "json", or "full"

    Returns:
        Dict with report sections:
        - overview, latest_developments, job_signals, talking_points
        - metadata (company, generated_at, confidence)
    """
    # Gather all data
    funding = get_funding_info(company_name, domain, ticker, company_type)
    news = get_recent_news(company_name, domain, days=7)
    jobs = get_job_signals(company_name, domain)

    # Build overview
    overview = _build_overview(company_name, funding)

    # Build latest developments (max 5)
    latest = _build_latest_developments(news, funding)

    # Build talking points
    talking_points = _build_talking_points(funding, news, jobs)

    # Build job signals section
    job_section = _build_job_section(jobs)

    report = {
        "metadata": {
            "company": company_name,
            "domain": funding.get("domain", domain or "unknown"),
            "ticker": funding.get("ticker") or ticker,
            "type": funding.get("company_type", company_type),
            "generated_at": datetime.now().isoformat(),
            "confidence": _calculate_overall_confidence(funding, news, jobs),
        },
        "overview": overview,
        "latest_developments": latest,
        "job_signals": job_section,
        "talking_points": talking_points,
        "raw_data": {
            "funding": funding,
            "news": news,
            "jobs": jobs,
        }
    }

    return report


def _build_overview(company_name: str, funding: dict) -> str:
    """Build overview section."""
    lines = [f"## {company_name} Overview\n"]

    # Company type and basic info
    company_type = funding.get("company_type", "unknown")
    lines.append(f"**Type:** {company_type.upper() if company_type != 'unknown' else 'Unknown'}")

    if funding.get("is_public"):
        market_cap = funding.get("market_cap", "unknown")
        price = funding.get("price")
        week_range = funding.get("52_week_range", "unknown")
        lines.append(f"**Market Cap:** {market_cap}")
        if price:
            lines.append(f"**Stock Price:** ${price}")
        lines.append(f"**52-Week Range:** {week_range}")
    else:
        total_raised = funding.get("total_raised", "unknown")
        stage = funding.get("stage", "unknown")
        valuation = funding.get("valuation", "unknown")
        lines.append(f"**Total Raised:** {total_raised}")
        lines.append(f"**Stage:** {stage}")
        if valuation != "unknown":
            lines.append(f"**Valuation:** {valuation}")

    # Basic company info
    sector = funding.get("sector", "unknown")
    industry = funding.get("industry", "unknown")
    employees = funding.get("employees", "unknown")
    if sector != "unknown":
        lines.append(f"**Sector:** {sector}")
    if industry != "unknown":
        lines.append(f"**Industry:** {industry}")
    if employees != "unknown" and employees != 0:
        lines.append(f"**Employees:** {employees:,}" if isinstance(employees, int) else f"**Employees:** {employees}")

    # Source attribution
    source = funding.get("source", "unknown")
    confidence = funding.get("confidence", "LOW")
    lines.append(f"\n_Source: {source} | Confidence: {confidence}_")

    return "\n".join(lines)


def _build_latest_developments(news: list, funding: dict, max_items: int = 5) -> list[dict]:
    """Build latest developments section from news."""
    developments = []

    # Add news items (prioritize TIER1)
    tier1_news = [n for n in news if n.get("tier_label") == "TIER1"]
    other_news = [n for n in news if n.get("tier_label") != "TIER1"]
    sorted_news = tier1_news + other_news

    for item in sorted_news[:max_items]:
        if "error" in item:
            continue
        developments.append({
            "type": "news",
            "title": item.get("title", ""),
            "source": item.get("source", "unknown"),
            "tier": item.get("tier_label", "TIER3"),
            "date": item.get("date", "unknown"),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "confidence": "HIGH" if item.get("tier_label") == "TIER1" else "MEDIUM",
        })

    # Add funding event if recent
    last_round = funding.get("last_round")
    last_round_amount = funding.get("last_round_amount")
    if last_round and last_round != "unknown" and last_round_amount and last_round_amount != "unknown":
        developments.append({
            "type": "funding",
            "title": f"{last_round} Round",
            "detail": last_round_amount,
            "source": funding.get("source", "unknown"),
            "confidence": funding.get("confidence", "MEDIUM"),
        })

    return developments[:max_items]


def _build_job_section(jobs: dict) -> str:
    """Build job signals section."""
    lines = ["## Job Market Signals\n"]

    total = jobs.get("total_openings")
    if total is None:
        lines.append("**Open Roles:** Unknown")
    else:
        lines.append(f"**Open Roles:** {total}")

    signal = jobs.get("signal", "unknown")
    trend = jobs.get("trend", "unknown")
    signal_conf = jobs.get("signal_confidence", "LOW")

    signal_emoji = {"EXPANSION": "📈", "STABLE": "➡️", "CONTRACTION": "📉"}.get(signal, "❓")
    lines.append(f"**Signal:** {signal_emoji} {signal}")
    lines.append(f"**Trend:** {trend}")
    lines.append(f"**Confidence:** {signal_conf}")

    breakdown = jobs.get("department_breakdown", {})
    if breakdown:
        lines.append("\n**Department Breakdown:**")
        for dept, count in list(breakdown.items())[:5]:
            lines.append(f"- {dept}: {count}")

    source_url = jobs.get("source_url", "unknown")
    lines.append(f"\n_Source: LinkedIn | {source_url}_")

    return "\n".join(lines)


def _build_talking_points(funding: dict, news: list, jobs: dict) -> list[str]:
    """Build suggested talking points."""
    points = []

    company_name = funding.get("name", "This company")
    company_type = funding.get("company_type", "unknown")

    # Public company talking points
    if funding.get("is_public"):
        market_cap = funding.get("market_cap", "unknown")
        price = funding.get("price")
        if price:
            points.append(f"Stock trading at ${price} ({market_cap} market cap)")
        if funding.get("sector") != "unknown":
            points.append(f"Operating in the {funding.get('sector')} sector")
    else:
        # Private company talking points
        total_raised = funding.get("total_raised", "unknown")
        stage = funding.get("stage", "unknown")
        if total_raised != "unknown":
            points.append(f"Has raised {total_raised} (last: {stage})")
        valuation = funding.get("valuation", "unknown")
        if valuation != "unknown":
            points.append(f"Valuation: {valuation}")

    # Job signals talking points
    signal = jobs.get("signal", "unknown")
    if signal == "EXPANSION":
        points.append(f"Actively hiring with {jobs.get('total_openings', 'multiple')} open roles")
    elif signal == "CONTRACTION":
        points.append(f"Showing contraction signals - may indicate cost optimization phase")

    # News-based talking points
    tier1_news = [n for n in news if n.get("tier_label") == "TIER1"]
    if tier1_news:
        for item in tier1_news[:2]:
            title = item.get("title", "")[:100]
            points.append(f"Recent coverage: {title}")

    if not points:
        points.append("Limited public data available - recommend additional research")

    return points


def _calculate_overall_confidence(funding: dict, news: list, jobs: dict) -> str:
    """Calculate overall report confidence."""
    confidences = []

    fund_conf = funding.get("confidence", "LOW")
    if fund_conf == "HIGH":
        confidences.append(3)
    elif fund_conf == "MEDIUM":
        confidences.append(2)
    else:
        confidences.append(1)

    if news and not (len(news) == 1 and "error" in news[0]):
        confidences.append(3)  # Has news data

    jobs_conf = jobs.get("confidence", "LOW")
    if jobs_conf == "HIGH":
        confidences.append(3)
    elif jobs_conf == "MEDIUM":
        confidences.append(2)
    else:
        confidences.append(1)

    avg = sum(confidences) / len(confidences) if confidences else 1
    if avg >= 2.5:
        return "HIGH"
    elif avg >= 1.5:
        return "MEDIUM"
    return "LOW"


def format_report_brief(report: dict) -> str:
    """
    Format report as a Slack/Telegram-friendly brief.

    Args:
        report: Dict from generate_report

    Returns:
        Formatted string
    """
    lines = []
    meta = report.get("metadata", {})

    lines.append(f"🎯 **{meta.get('company', 'Unknown')}** Intelligence Brief")
    lines.append(f"_Generated: {datetime.now().strftime('%b %d, %Y %H:%M')} | Confidence: {report.get('metadata', {}).get('confidence', 'LOW')}_\n")

    # Overview (simplified)
    lines.append("*OVERVIEW*")
    overview = report.get("overview", "")
    for line in overview.split("\n")[2:6]:  # Skip header and first few lines
        if line.strip():
            lines.append(line.strip())

    # Latest developments
    lines.append("\n*LATEST DEVELOPMENTS*")
    latest = report.get("latest_developments", [])
    for i, dev in enumerate(latest[:5], 1):
        tier = dev.get("tier_label", "T3")
        tier_emoji = {"TIER1": "🟢", "TIER2": "🟡", "TIER3": "⚪"}.get(tier, "⚪")
        title = dev.get("title", "")[:70]
        lines.append(f"{tier_emoji} {title}")
        if dev.get("url"):
            lines.append(f"   ↳ {dev.get('url')[:80]}")

    # Talking points
    lines.append("\n*TALKING POINTS*")
    for point in report.get("talking_points", [])[:5]:
        lines.append(f"• {point}")

    return "\n".join(lines)


def format_report_full(report: dict) -> str:
    """
    Format report as a full detailed document.

    Args:
        report: Dict from generate_report

    Returns:
        Formatted string
    """
    lines = []
    meta = report.get("metadata", {})

    lines.append("=" * 60)
    lines.append(f"COMPANY INTELLIGENCE REPORT: {meta.get('company', 'Unknown')}")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Confidence: {report.get('metadata', {}).get('confidence', 'LOW')}")
    lines.append("")

    lines.append(report.get("overview", ""))
    lines.append("")

    lines.append("-" * 40)
    lines.append("LATEST DEVELOPMENTS (7 days)")
    lines.append("-" * 40)
    for dev in report.get("latest_developments", []):
        tier = dev.get("tier_label", "T3")
        lines.append(f"[{tier}] {dev.get('date', 'unknown')}: {dev.get('title', '')}")
        if dev.get("url"):
            lines.append(f"  Source: {dev.get('url')}")
        lines.append("")

    lines.append("-" * 40)
    lines.append("JOB MARKET SIGNALS")
    lines.append("-" * 40)
    lines.append(report.get("job_signals", ""))
    lines.append("")

    lines.append("-" * 40)
    lines.append("TALKING POINTS")
    lines.append("-" * 40)
    for point in report.get("talking_points", []):
        lines.append(f"• {point}")
    lines.append("")

    lines.append("=" * 60)
    lines.append("RAW DATA")
    lines.append("=" * 60)
    import json
    lines.append(json.dumps(report.get("raw_data", {}), indent=2))

    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    domain = sys.argv[2] if len(sys.argv) > 2 else None
    ticker = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"Generating report for: {company}")
    report = generate_report(company, domain, ticker)
    print(json.dumps(report, indent=2, default=str))
