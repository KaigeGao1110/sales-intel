#!/usr/bin/env python3
"""
Scout CLI - Company Intelligence CLI Orchestrator.

Usage:
    python3 scout_cli.py research <company> [--domain x.com] [--ticker TICKER] [--type public|private|auto] [--output json|brief|full]
    python3 scout_cli.py monitor --companies-file companies.json [--output-dir ./output]
    python3 scout_cli.py weekly-digest --companies-file companies.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from report import generate_report, format_report_brief, format_report_full


def research(
    company_name: str,
    domain: Optional[str] = None,
    ticker: Optional[str] = None,
    company_type: str = "auto",
    output_format: str = "brief"
) -> int:
    """
    Research a single company and generate intelligence report.

    Args:
        company_name: Company name
        domain: Company domain
        ticker: Stock ticker
        company_type: public, private, or auto
        output_format: json, brief, or full

    Returns:
        Exit code (0 success, 1 failure)
    """
    print(f"🔍 Researching {company_name}...", file=sys.stderr)

    try:
        report = generate_report(
            company_name=company_name,
            domain=domain,
            ticker=ticker,
            company_type=company_type,
        )

        if output_format == "json":
            print(json.dumps(report, indent=2, default=str))
        elif output_format == "brief":
            print(format_report_brief(report))
        else:  # full
            print(format_report_full(report))

        return 0
    except Exception as e:
        print(f"❌ Error researching {company_name}: {e}", file=sys.stderr)
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


def monitor(companies_file: str, output_dir: str = "./output") -> int:
    """
    Monitor multiple companies from a JSON file.

    Args:
        companies_file: Path to JSON file with company list
        output_dir: Directory to write output files

    Returns:
        Exit code
    """
    print(f"📊 Monitoring companies from: {companies_file}", file=sys.stderr)

    # Load companies
    try:
        with open(companies_file, "r") as f:
            companies = json.load(f)
    except FileNotFoundError:
        print(f"❌ Companies file not found: {companies_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in companies file: {e}", file=sys.stderr)
        return 1

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"monitor_{timestamp}.json")

    results = []
    for company in companies:
        name = company.get("name")
        if not name:
            continue

        print(f"  🔍 Researching {name}...", file=sys.stderr)
        try:
            report = generate_report(
                company_name=name,
                domain=company.get("domain"),
                ticker=company.get("ticker"),
                company_type=company.get("type", "auto"),
            )
            results.append({
                "company": name,
                "status": "success",
                "report": report,
            })
        except Exception as e:
            results.append({
                "company": name,
                "status": "error",
                "error": str(e),
            })

    # Write results
    with open(output_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "companies": results,
        }, f, indent=2, default=str)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    errors = sum(1 for r in results if r["status"] == "error")
    print(f"\n✅ Monitor complete: {success} succeeded, {errors} failed", file=sys.stderr)
    print(f"📁 Results written to: {output_file}", file=sys.stderr)

    # Print brief summary for each
    for result in results:
        if result["status"] == "success":
            meta = result["report"].get("metadata", {})
            confidence = result["report"].get("metadata", {}).get("confidence", "LOW")
            print(f"  {meta.get('company', result['company'])}: {confidence} confidence")
        else:
            print(f"  {result['company']}: ERROR - {result.get('error', 'unknown')}")

    return 0 if errors == 0 else 1


def weekly_digest(companies_file: str) -> int:
    """
    Generate weekly digest for monitored companies.

    Args:
        companies_file: Path to JSON file with company list

    Returns:
        Exit code
    """
    print(f"📬 Generating weekly digest from: {companies_file}", file=sys.stderr)

    # Load companies
    try:
        with open(companies_file, "r") as f:
            companies = json.load(f)
    except FileNotFoundError:
        print(f"❌ Companies file not found: {companies_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in companies file: {e}", file=sys.stderr)
        return 1

    lines = []
    lines.append("=" * 60)
    lines.append("SCOUT WEEKLY DIGEST")
    lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    lines.append("=" * 60)
    lines.append("")

    for company in companies:
        name = company.get("name")
        if not name:
            continue

        print(f"  🔍 Researching {name}...", file=sys.stderr)
        try:
            report = generate_report(
                company_name=name,
                domain=company.get("domain"),
                ticker=company.get("ticker"),
                company_type=company.get("type", "auto"),
            )

            meta = report.get("metadata", {})
            lines.append(f"## {name}")
            lines.append(f"Type: {meta.get('type', 'unknown').upper()} | Confidence: {report.get('metadata', {}).get('confidence', 'LOW')}")
            lines.append("")

            # Quick overview
            overview = report.get("overview", "")
            for line in overview.split("\n")[2:5]:
                if line.strip():
                    lines.append(line.strip())
            lines.append("")

            # Key developments
            latest = report.get("latest_developments", [])
            if latest:
                lines.append("Key Developments:")
                for dev in latest[:3]:
                    lines.append(f"  • [{dev.get('tier_label', 'T3')}] {dev.get('title', '')[:70]}")
            lines.append("")

            # Job signals
            job_section = report.get("job_signals", "")
            if job_section:
                for line in job_section.split("\n")[:5]:
                    if line.strip():
                        lines.append(line.strip())
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        except Exception as e:
            lines.append(f"## {name}")
            lines.append(f"ERROR: {e}")
            lines.append("")

    digest = "\n".join(lines)
    print("\n" + digest)

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print_help()
        return 1

    command = sys.argv[1]

    if command == "research":
        return cmd_research()
    elif command == "monitor":
        return cmd_monitor()
    elif command == "weekly-digest":
        return cmd_weekly_digest()
    elif command in ("-h", "--help", "help"):
        print_help()
        return 0
    else:
        print(f"❌ Unknown command: {command}", file=sys.stderr)
        print_help()
        return 1


def print_help():
    """Print help message."""
    print("""
Scout CLI - Company Intelligence CLI

Usage:
    python3 scout_cli.py research <company> [options]
    python3 scout_cli.py monitor --companies-file <file> [options]
    python3 scout_cli.py weekly-digest --companies-file <file>

Commands:
    research <company>     Research a single company
    monitor               Monitor multiple companies from JSON file
    weekly-digest         Generate weekly digest for companies

Research Options:
    --domain DOMAIN       Company domain (e.g., stripe.com)
    --ticker TICKER       Stock ticker symbol
    --type TYPE           Company type: public, private, auto (default: auto)
    --output FORMAT       Output format: json, brief, full (default: brief)

Monitor/Weekly-Digest Options:
    --companies-file FILE    JSON file with company list
    --output-dir DIR         Output directory (monitor only)

Examples:
    python3 scout_cli.py research Stripe --domain stripe.com --ticker STRIPE
    python3 scout_cli.py research Anthropic --type private
    python3 scout_cli.py monitor --companies-file companies.json
    python3 scout_cli.py weekly-digest --companies-file companies.json
""")


def cmd_research():
    """Handle research command."""
    if len(sys.argv) < 3:
        print("❌ Missing company name", file=sys.stderr)
        print_help()
        return 1

    company_name = sys.argv[2]
    domain = None
    ticker = None
    company_type = "auto"
    output_format = "brief"

    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--domain" and i + 1 < len(args):
            domain = args[i + 1]
            i += 2
        elif args[i] == "--ticker" and i + 1 < len(args):
            ticker = args[i + 1]
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            company_type = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_format = args[i + 1]
            i += 2
        else:
            i += 1

    if output_format not in ("json", "brief", "full"):
        print(f"❌ Invalid output format: {output_format}", file=sys.stderr)
        return 1

    return research(company_name, domain, ticker, company_type, output_format)


def cmd_monitor():
    """Handle monitor command."""
    companies_file = None
    output_dir = "./output"

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--companies-file" and i + 1 < len(args):
            companies_file = args[i + 1]
            i += 2
        elif args[i] == "--output-dir" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        else:
            i += 1

    if not companies_file:
        print("❌ Missing --companies-file", file=sys.stderr)
        return 1

    return monitor(companies_file, output_dir)


def cmd_weekly_digest():
    """Handle weekly-digest command."""
    companies_file = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--companies-file" and i + 1 < len(args):
            companies_file = args[i + 1]
            i += 2
        else:
            i += 1

    if not companies_file:
        print("❌ Missing --companies-file", file=sys.stderr)
        return 1

    return weekly_digest(companies_file)


if __name__ == "__main__":
    sys.exit(main())
