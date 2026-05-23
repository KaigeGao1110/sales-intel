#!/usr/bin/env python3
"""
Job Market Signals Scraper for Scout.

Uses LinkedIn jobs page scraping with proper headers.
Returns job count, department breakdown, and trend signals.
"""

import random
import re
import time as time_mod
from datetime import datetime, timedelta
from typing import Optional

import requests

TIMEOUT = 10

# User agent to mimic browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Known job counting keywords that indicate expansion vs contraction
EXPANSION_KEYWORDS = [
    "hiring", "join us", "we're growing", "open roles", "new positions",
    "expanding", "hiring now", "careers", "open positions", "hiring engineers",
    "hiring designers", "hiring managers", "hiring sales", "hiring marketers",
]
CONTRACTION_KEYWORDS = [
    "layoffs", "cutting", "reducing", "restructuring", "rto",
    "headcount reduction", "cost cutting", "efficiency", "reorganization",
]


def _extract_job_count_from_text(text: str) -> Optional[int]:
    """Try to extract job count from text."""
    # Look for patterns like "100+ jobs", "100 jobs", "Over 100 open roles"
    patterns = [
        r'([\d,]+)\+?\s*(?:open\s+)?(?:roles?|positions?|jobs?)',
        r'Hiring\s+([\d,]+)',
        r'([\d,]+)\s+(?:people|employees)\s+(?:in|at)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count_str = match.group(1).replace(",", "")
            try:
                return int(count_str)
            except ValueError:
                continue
    return None


def _classify_signal(text: str) -> dict:
    """Classify job posting text for expansion/contraction signals."""
    text_lower = text.lower()
    expansion_count = sum(1 for kw in EXPANSION_KEYWORDS if kw in text_lower)
    contraction_count = sum(1 for kw in CONTRACTION_KEYWORDS if kw in text_lower)

    if contraction_count > expansion_count:
        signal = "CONTRACTION"
        confidence = "HIGH" if contraction_count >= 2 else "MEDIUM"
    elif expansion_count > contraction_count:
        signal = "EXPANSION"
        confidence = "HIGH" if expansion_count >= 2 else "MEDIUM"
    else:
        signal = "STABLE"
        confidence = "LOW"

    return {"signal": signal, "confidence": confidence, "expansion_signals": expansion_count, "contraction_signals": contraction_count}


def _parse_linkedin_jobs(text: str) -> dict:
    """Parse LinkedIn jobs page content."""
    result = {
        "total_openings": None,
        "department_breakdown": {},
        "trend": "unknown",
        "signal": "unknown",
        "signal_confidence": "LOW",
        "recent_postings": 0,
        "source_url": "unknown",
    }

    # Extract total job count
    total = _extract_job_count_from_text(text)
    result["total_openings"] = total

    # Look for department/team mentions
    dept_pattern = r'(\d+)\s+(?:open\s+)?(?:roles?|positions?|jobs?)\s+(?:in|for|on)\s+([A-Za-z\s]+)'
    for match in re.finditer(dept_pattern, text, re.IGNORECASE):
        dept = match.group(2).strip()
        count = int(match.group(1))
        result["department_breakdown"][dept] = count

    # Extract signal
    signal_info = _classify_signal(text)
    result["signal"] = signal_info["signal"]
    result["signal_confidence"] = signal_info["confidence"]

    return result


def get_job_signals(
    company_name: str,
    domain: Optional[str] = None,
    days: int = 30
) -> dict:
    """
    Fetch job market signals for a company.

    Args:
        company_name: Company name
        domain: Company domain (e.g., "stripe.com")
        days: Look for postings from last N days

    Returns:
        Dict with keys:
        - company_name, domain
        - total_openings (int or None)
        - department_breakdown (dict)
        - trend (EXPANSION/STABLE/CONTRACTION)
        - signal, signal_confidence
        - recent_postings (int)
        - source_url
        - last_updated
    """
    result = {
        "company_name": company_name,
        "domain": domain or "unknown",
        "total_openings": None,
        "department_breakdown": {},
        "trend": "unknown",
        "signal": "unknown",
        "signal_confidence": "LOW",
        "recent_postings": 0,
        "source_url": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}/jobs",
        "last_updated": datetime.now().isoformat(),
        "confidence": "LOW",
        "raw_findings": [],
    }

    if not domain:
        result["source_url"] = f"https://www.linkedin.com/jobs/search/?keywords={company_name}"
    else:
        result["source_url"] = f"https://www.linkedin.com/company/{domain.split('.')[0]}/jobs"

    # Try LinkedIn jobs search (with delay to avoid rate limiting)
    time_mod.sleep(random.uniform(2, 3))
    try:
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={company_name}&location=United%20States"
        resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)

        if resp.status_code == 200:
            text = resp.text

            # Extract job count
            total = _extract_job_count_from_text(text)
            result["total_openings"] = total

            # Parse signal
            signal_info = _classify_signal(text)
            result["signal"] = signal_info["signal"]
            result["signal_confidence"] = signal_info["confidence"]

            if total:
                if total > 100:
                    result["trend"] = "EXPANSION"
                elif total > 20:
                    result["trend"] = "STABLE"
                else:
                    result["trend"] = "STABLE"

            result["confidence"] = "MEDIUM"
            result["raw_findings"].append(f"LinkedIn search returned {total or 'unknown'} jobs")

    except requests.RequestException as e:
        result["raw_findings"].append(f"LinkedIn search failed: {str(e)}")

    # Try company LinkedIn page directly if domain provided (with delay)
    if domain and domain != "unknown":
        time_mod.sleep(random.uniform(2, 3))
        try:
            company_slug = domain.split(".")[0]
            jobs_url = f"https://www.linkedin.com/company/{company_slug}/jobs"
            resp = requests.get(jobs_url, headers=HEADERS, timeout=TIMEOUT)

            if resp.status_code == 200:
                text = resp.text
                parsed = _parse_linkedin_jobs(text)
                result["department_breakdown"] = parsed.get("department_breakdown", {})
                if parsed.get("total_openings"):
                    result["total_openings"] = parsed["total_openings"]
                if parsed.get("signal") != "unknown":
                    result["signal"] = parsed["signal"]
                    result["signal_confidence"] = parsed.get("signal_confidence", "LOW")
                result["confidence"] = "MEDIUM"
        except Exception:
            pass

    return result


def format_jobs_brief(jobs_data: dict) -> str:
    """
    Format job signals into a brief text summary.

    Args:
        jobs_data: Dict from get_job_signals

    Returns:
        Formatted string suitable for Slack/Telegram
    """
    lines = ["💼 Job Signals:"]

    total = jobs_data.get("total_openings")
    if total is None:
        lines.append("• Openings: unknown")
    else:
        lines.append(f"• Openings: {total}")

    signal = jobs_data.get("signal", "unknown")
    signal_emoji = {"EXPANSION": "📈", "STABLE": "➡️", "CONTRACTION": "📉"}.get(signal, "❓")
    lines.append(f"• Trend: {signal_emoji} {signal} (confidence: {jobs_data.get('signal_confidence', 'LOW')})")

    breakdown = jobs_data.get("department_breakdown", {})
    if breakdown:
        lines.append("• Departments:")
        for dept, count in list(breakdown.items())[:5]:
            lines.append(f"  - {dept}: {count}")

    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"

    print(f"Fetching job signals for: {company}")
    jobs = get_job_signals(company)
    print(json.dumps(jobs, indent=2))
