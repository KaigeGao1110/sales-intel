#!/usr/bin/env python3
"""
Job Postings Analysis Module for Scout.

Analyzes job postings to identify company growth, hiring trends,
and technology adoption signals for sales intelligence.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional


JOBS_DATA_FILE = "jobs_data.json"


def load_jobs(path: str = JOBS_DATA_FILE) -> list[dict]:
    """Load job postings from JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f).get("jobs", [])
    except FileNotFoundError:
        return []


def load_companies(path: str = "companies.json") -> list[dict]:
    """Load companies from JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f).get("companies", [])
    except FileNotFoundError:
        return []


def get_jobs_by_company(company_name: str, jobs: Optional[list[dict]] = None) -> list[dict]:
    """Get job postings for a specific company."""
    if jobs is None:
        jobs = load_jobs()

    return [
        {
            "title": job.get("title"),
            "department": job.get("department"),
            "location": job.get("location"),
            "posted_date": job.get("posted_date"),
            "type": job.get("type", "full-time"),
            "remote": job.get("remote", False),
            "skills": job.get("skills", []),
        }
        for job in jobs
        if company_name.lower() in job.get("company", "").lower()
    ]


def get_jobs_by_department(department: str, jobs: Optional[list[dict]] = None) -> list[dict]:
    """Get job postings by department."""
    if jobs is None:
        jobs = load_jobs()

    return [
        {
            "company": job.get("company"),
            "title": job.get("title"),
            "location": job.get("location"),
            "posted_date": job.get("posted_date"),
        }
        for job in jobs
        if job.get("department", "").lower() == department.lower()
    ]


def get_jobs_by_technology(skill: str, jobs: Optional[list[dict]] = None) -> list[dict]:
    """Get job postings requiring a specific technology."""
    if jobs is None:
        jobs = load_jobs()

    return [
        {
            "company": job.get("company"),
            "title": job.get("title"),
            "department": job.get("department"),
            "posted_date": job.get("posted_date"),
        }
        for job in jobs
        if skill.lower() in [s.lower() for s in job.get("skills", [])]
    ]


def get_hiring_trends(jobs: Optional[list[dict]] = None, days: int = 90) -> dict:
    """Analyze hiring trends over the last N days."""
    if jobs is None:
        jobs = load_jobs()

    cutoff = datetime.now() - timedelta(days=days)
    company_hiring = {}

    for job in jobs:
        try:
            posted = datetime.strptime(job.get("posted_date", ""), "%Y-%m-%d")
            if posted < cutoff:
                continue
        except ValueError:
            continue

        company = job.get("company", "")
        if company not in company_hiring:
            company_hiring[company] = {"company": company, "open_roles": 0, "departments": set()}

        company_hiring[company]["open_roles"] += 1
        company_hiring[company]["departments"].add(job.get("department", "unknown"))

    results = []
    for company, data in company_hiring.items():
        results.append({
            "company": company,
            "open_roles": data["open_roles"],
            "departments": list(data["departments"]),
        })

    return {
        "total_active_jobs": len(jobs),
        "companies_hiring": len(results),
        "breakdown": sorted(results, key=lambda x: x["open_roles"], reverse=True),
    }


def identify_growth_signals(jobs: Optional[list[dict]] = None) -> list[dict]:
    """Identify companies showing growth signals through hiring."""
    if jobs is None:
        jobs = load_jobs()

    trends = get_hiring_trends(jobs, days=30)
    growth_signals = []

    for item in trends["breakdown"]:
        jobs_list = [j for j in jobs if j.get("company", "") == item["company"]]

        sales_eng = sum(1 for j in jobs_list if "sales" in j.get("department", "").lower() or "revenue" in j.get("department", "").lower())
        eng_heavy = sum(1 for j in jobs_list if "engineer" in j.get("title", "").lower())

        if item["open_roles"] >= 5 or sales_eng >= 2:
            growth_signals.append({
                "company": item["company"],
                "open_roles": item["open_roles"],
                "departments": item["departments"],
                "sales_eng_roles": sales_eng,
                "engineering_roles": eng_heavy,
                "signal": "aggressive_hiring" if item["open_roles"] >= 10 else "active_hiring",
            })

    return sorted(growth_signals, key=lambda x: x["open_roles"], reverse=True)


def get_remote_jobs(jobs: Optional[list[dict]] = None) -> list[dict]:
    """Get all remote-friendly job postings."""
    if jobs is None:
        jobs = load_jobs()

    return [
        {
            "company": job.get("company"),
            "title": job.get("title"),
            "department": job.get("department"),
            "location": job.get("location"),
            "posted_date": job.get("posted_date"),
        }
        for job in jobs
        if job.get("remote", False)
    ]


def get_technology_adoption(jobs: Optional[list[dict]] = None) -> dict:
    """Identify technology adoption signals from job postings."""
    if jobs is None:
        jobs = load_jobs()

    tech_counts = {}
    for job in jobs:
        for skill in job.get("skills", []):
            tech_counts[skill] = tech_counts.get(skill, 0) + 1

    return dict(sorted(tech_counts.items(), key=lambda x: x[1], reverse=True))


def generate_jobs_report(company_name: Optional[str] = None) -> str:
    """Generate a jobs intelligence report."""
    jobs = load_jobs()
    lines = ["=" * 60, "SCOUT JOBS INTELLIGENCE REPORT", "=" * 60, ""]

    if company_name:
        company_jobs = get_jobs_by_company(company_name, jobs)
        if not company_jobs:
            return f"No job data found for: {company_name}"
        lines.append(f"Company: {company_name}")
        lines.append(f"Open Roles: {len(company_jobs)}")
        lines.append("")
        by_dept = {}
        for j in company_jobs:
            dept = j["department"]
            by_dept[dept] = by_dept.get(dept, 0) + 1
        lines.append("By Department:")
        for dept, count in sorted(by_dept.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {dept}: {count}")
        lines.append("")
        lines.append("Recent Postings:")
        for j in company_jobs[:10]:
            lines.append(f"  [{j['posted_date']}] {j['title']} ({j['location']})")
            if j.get("skills"):
                lines.append(f"    Skills: {', '.join(j['skills'][:5])}")
    else:
        trends = get_hiring_trends(jobs, days=90)
        lines.append(f"Total Active Job Postings: {trends['total_active_jobs']}")
        lines.append(f"Companies Actively Hiring: {trends['companies_hiring']}")
        lines.append("")

        signals = identify_growth_signals(jobs)
        lines.append("Growth Signals (top hirers):")
        for s in signals[:5]:
            lines.append(f"  {s['company']}: {s['open_roles']} open roles ({s['signal']})")
            lines.append(f"    Departments: {', '.join(s['departments'][:4])}")
        lines.append("")

        tech = get_technology_adoption(jobs)
        lines.append("Top Technologies in Demand:")
        for t, count in list(tech.items())[:10]:
            lines.append(f"  {t}: {count} postings")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            company = sys.argv[2] if len(sys.argv) > 2 else None
            print(generate_jobs_report(company))
        elif sys.argv[1] == "--trends":
            trends = get_hiring_trends()
            print(f"Total Jobs: {trends['total_active_jobs']}")
            print(f"Companies Hiring: {trends['companies_hiring']}")
            print("\nTop Hirers:")
            for b in trends["breakdown"][:10]:
                print(f"  {b['company']}: {b['open_roles']} roles")
        elif sys.argv[1] == "--signals":
            signals = identify_growth_signals()
            for s in signals:
                print(f"{s['company']}: {s['open_roles']} roles ({s['signal']})")
        elif sys.argv[1] == "--tech":
            tech = get_technology_adoption()
            for t, count in tech.items():
                print(f"{t}: {count}")
        elif sys.argv[1] == "--remote":
            remote = get_remote_jobs()
            for r in remote:
                print(f"{r['company']} | {r['title']} | {r['location']}")
        else:
            jobs = get_jobs_by_company(sys.argv[1])
            if jobs:
                for j in jobs:
                    print(f"[{j['posted_date']}] {j['title']} - {j['department']}")
            else:
                print(f"No jobs found for: {sys.argv[1]}")
    else:
        print(generate_jobs_report())


if __name__ == "__main__":
    main()
