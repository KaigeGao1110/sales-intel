#!/usr/bin/env python3
"""
Comprehensive Report Generation Module for Scout.

Generates combined intelligence reports from all data sources
to provide a holistic view of target companies.
"""

import json
import sys
from datetime import datetime
from typing import Optional

import funding
import news
import jobs


def generate_company_report(company_name: str) -> str:
    """Generate a comprehensive intelligence report for a company."""
    companies = funding.load_companies()
    news_articles = news.load_news()
    job_postings = jobs.load_jobs()

    funding_data = funding.get_funding_by_company(company_name, companies)
    company_news = news.get_news_by_company(company_name, news_articles)
    company_jobs = jobs.get_jobs_by_company(company_name, job_postings)

    lines = [
        "=" * 70,
        f"SCOUT INTELLIGENCE REPORT: {company_name.upper()}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
    ]

    lines.append("## FUNDING INTELLIGENCE")
    lines.append("-" * 40)
    if funding_data:
        lines.append(f"Stage: {funding_data['stage']}")
        lines.append(f"Total Raised: ${funding_data['total_raised']:,.0f}")
        lines.append(f"Last Round: {funding_data['last_round']} (${funding_data['last_round_amount']:,.0f})")
        lines.append(f"Last Round Date: {funding_data['last_round_date']}")
        lines.append(f"Investors: {', '.join(funding_data['investors']) if funding_data['investors'] else 'Unknown'}")
    else:
        lines.append("No funding data available.")
    lines.append("")

    lines.append("## NEWS & MEDIA")
    lines.append("-" * 40)
    if company_news:
        lines.append(f"Total Articles: {len(company_news)}")
        recent_positive = [a for a in company_news if a.get("sentiment") == "positive"]
        if recent_positive:
            lines.append(f"Recent Positive Coverage: {len(recent_positive)} articles")
        lines.append("")
        lines.append("Recent Articles:")
        for a in company_news[:5]:
            lines.append(f"  [{a['date']}] {a['title']}")
            lines.append(f"    Source: {a['source']} | Sentiment: {a['sentiment']} | Category: {a['category']}")
    else:
        lines.append("No news data available.")
    lines.append("")

    lines.append("## HIRING ACTIVITY")
    lines.append("-" * 40)
    if company_jobs:
        lines.append(f"Open Roles: {len(company_jobs)}")
        by_dept = {}
        for j in company_jobs:
            dept = j.get("department", "unknown")
            by_dept[dept] = by_dept.get(dept, 0) + 1
        lines.append("By Department:")
        for dept, count in sorted(by_dept.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {dept}: {count}")
        remote_count = sum(1 for j in company_jobs if j.get("remote"))
        if remote_count > 0:
            lines.append(f"Remote-Friendly Roles: {remote_count}")
        lines.append("")
        lines.append("Recent Postings:")
        for j in company_jobs[:5]:
            lines.append(f"  [{j['posted_date']}] {j['title']} - {j['location']}")
    else:
        lines.append("No job data available.")
    lines.append("")

    lines.append("## SALES SIGNALS SUMMARY")
    lines.append("-" * 40)
    signals = []
    if funding_data and funding_data.get("total_raised", 0) > 10000000:
        signals.append("Well-funded (potential budget for solutions)")
    if funding_data and funding_data.get("stage") in ("series_a", "series_b", "series_c"):
        signals.append("Growth stage (active scaling, likely buying tools)")
    if any(a.get("sentiment") == "positive" for a in company_news):
        signals.append("Positive media momentum")
    if len(company_jobs) >= 5:
        signals.append("Aggressive hiring (likely expanding operations)")
    if any(j.get("department") in ("sales", "revenue", "marketing") for j in company_jobs):
        signals.append("Building out sales/marketing team (may need enablement tools)")
    if len(company_jobs) >= 10:
        signals.append("High growth trajectory")

    if signals:
        for s in signals:
            lines.append(f"  * {s}")
    else:
        lines.append("  No strong signals identified.")
    lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def generate_market_report() -> str:
    """Generate a market-wide intelligence summary."""
    companies = funding.load_companies()
    news_articles = news.load_news()
    job_postings = jobs.load_jobs()

    lines = [
        "=" * 70,
        "SCOUT MARKET INTELLIGENCE REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
    ]

    lines.append("## PORTFOLIO OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"Total Companies Tracked: {len(companies)}")
    total_raised = sum(c.get("total_raised", 0) for c in companies)
    lines.append(f"Total Capital Raised: ${total_raised:,.0f}")
    stages = {}
    for c in companies:
        stage = c.get("stage", "unknown")
        stages[stage] = stages.get(stage, 0) + 1
    lines.append("By Stage:")
    for stage, count in sorted(stages.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {stage}: {count}")
    lines.append("")

    lines.append("## FUNDING ACTIVITY")
    lines.append("-" * 40)
    recent_rounds = funding.get_recent_funding_rounds(companies, days=90)
    lines.append(f"Recent Rounds (90 days): {len(recent_rounds)}")
    for r in recent_rounds[:5]:
        lines.append(f"  [{r['date']}] {r['company']} - {r['round']} ${r['amount']:,.0f}")
    lines.append("")

    opps = funding.identify_funding_opportunities(companies)
    lines.append(f"Companies Due for Next Round: {len(opps)}")
    for o in opps[:5]:
        lines.append(f"  {o['company']} ({o['months_since_round']} months since {o['last_round']})")
    lines.append("")

    lines.append("## NEWS & SIGNALS")
    lines.append("-" * 40)
    signals = news.identify_buying_signals(companies, news_articles)
    lines.append("Top Buying Signals:")
    for s in signals[:5]:
        lines.append(f"  {s['company']}: {s['signal_count']} signals")
        for sig in s['signals'][:2]:
            lines.append(f"    - {sig[:60]}")
    lines.append("")

    lines.append("## HIRING LANDSCAPE")
    lines.append("-" * 40)
    trends = jobs.get_hiring_trends(job_postings, days=90)
    lines.append(f"Total Active Job Postings: {trends['total_active_jobs']}")
    lines.append(f"Companies Actively Hiring: {trends['companies_hiring']}")
    growth = jobs.identify_growth_signals(job_postings)
    lines.append("Top Growth Signals:")
    for g in growth[:5]:
        lines.append(f"  {g['company']}: {g['open_roles']} open roles ({g['signal']})")
    lines.append("")

    tech = jobs.get_technology_adoption(job_postings)
    lines.append("Top Technologies in Demand:")
    for t, count in list(tech.items())[:8]:
        lines.append(f"  {t}: {count}")
    lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def generate_target_list(min_raised: int = 0, min_jobs: int = 0) -> str:
    """Generate a target list based on criteria."""
    companies = funding.load_companies()
    job_postings = jobs.load_jobs()

    trends = jobs.get_hiring_trends(job_postings, days=90)
    hiring_dict = {b["company"]: b["open_roles"] for b in trends["breakdown"]}

    targets = []
    for c in companies:
        total_raised = c.get("total_raised", 0)
        open_roles = hiring_dict.get(c.get("name", ""), 0)
        if total_raised >= min_raised and open_roles >= min_jobs:
            targets.append({
                "company": c.get("name"),
                "total_raised": total_raised,
                "stage": c.get("stage"),
                "open_roles": open_roles,
            })

    targets.sort(key=lambda x: (x["total_raised"], x["open_roles"]), reverse=True)

    lines = [
        "=" * 70,
        "SCOUT TARGET LIST",
        f"Criteria: Min Raised=${min_raised:,.0f} | Min Jobs={min_jobs}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
    ]

    if targets:
        lines.append(f"{'Company':<30} {'Raised':<15} {'Stage':<12} {'Jobs'}")
        lines.append("-" * 70)
        for t in targets:
            lines.append(f"{t['company']:<30} ${t['total_raised']:>12,.0f} {t['stage']:<12} {t['open_roles']}")
    else:
        lines.append("No targets match the specified criteria.")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def export_json(company_name: Optional[str] = None) -> str:
    """Export report data as JSON."""
    companies = funding.load_companies()
    news_articles = news.load_news()
    job_postings = jobs.load_jobs()

    if company_name:
        data = {
            "company": company_name,
            "funding": funding.get_funding_by_company(company_name, companies),
            "news": news.get_news_by_company(company_name, news_articles),
            "jobs": jobs.get_jobs_by_company(company_name, job_postings),
        }
    else:
        data = {
            "companies": [
                {**c, "jobs": len([j for j in job_postings if j.get("company", "").lower() == c.get("name", "").lower()])}
                for c in companies
            ],
            "news_count": len(news_articles),
            "jobs_count": len(job_postings),
            "recent_rounds": funding.get_recent_funding_rounds(companies, days=90),
            "buying_signals": news.identify_buying_signals(companies, news_articles),
            "growth_signals": jobs.identify_growth_signals(job_postings),
        }

    return json.dumps(data, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "company" and len(sys.argv) > 2:
            print(generate_company_report(sys.argv[2]))
        elif command == "market":
            print(generate_market_report())
        elif command == "targets":
            min_raised = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            min_jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 0
            print(generate_target_list(min_raised, min_jobs))
        elif command == "export":
            company = sys.argv[2] if len(sys.argv) > 2 else None
            print(export_json(company))
        else:
            print("Usage:")
            print("  scout report company <name>  - Company report")
            print("  scout report market           - Market overview")
            print("  scout report targets [min_raised] [min_jobs]  - Target list")
            print("  scout report export [company] - Export as JSON")
    else:
        print(generate_market_report())


if __name__ == "__main__":
    main()
