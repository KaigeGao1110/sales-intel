#!/usr/bin/env python3
"""
Scout AI Sales Intelligence Toolkit - Main CLI Entry Point.

A unified command-line interface for accessing funding, news,
and jobs intelligence for sales prospecting.
"""

import sys


def main():
    """Route commands to appropriate modules."""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    if command in ("funding", "fund"):
        from funding import main as funding_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        funding_main()
    elif command in ("news", "press"):
        from news import main as news_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        news_main()
    elif command in ("jobs", "hiring"):
        from jobs import main as jobs_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        jobs_main()
    elif command == "report":
        from report import main as report_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        report_main()
    elif command in ("help", "--help", "-h"):
        print_help()
    elif command == "version":
        print("Scout AI Sales Intelligence Toolkit v1.0.0")
    else:
        print(f"Unknown command: {command}")
        print_help()


def print_help():
    """Print usage help."""
    help_text = """Scout AI Sales Intelligence Toolkit v1.0.0

Usage: scout <command> [options]

Commands:
  funding <subcommand>  - Funding intelligence
  news <subcommand>     - News monitoring
  jobs <subcommand>      - Job postings analysis
  report <subcommand>    - Comprehensive reports
  help                   - Show this help
  version                - Show version

Funding Subcommands:
  scout funding                  - Show funding report
  scout funding <company>        - Funding data for company
  scout funding --recent [days]  - Recent funding rounds
  scout funding --top [n]        - Top funded companies
  scout funding --report [name]  - Full funding report

News Subcommands:
  scout news <company>           - News for company
  scout news --recent [days]     - Recent news
  scout news --signals           - Buying signals
  scout news --positive          - Positive news
  scout news --report [name]     - Full news report

Jobs Subcommands:
  scout jobs <company>           - Jobs for company
  scout jobs --trends            - Hiring trends
  scout jobs --signals           - Growth signals
  scout jobs --tech              - Technology adoption
  scout jobs --remote            - Remote jobs
  scout jobs --report [name]     - Full jobs report

Report Subcommands:
  scout report company <name>    - Company intelligence report
  scout report market            - Market overview report
  scout report targets [raised] [jobs] - Target list
  scout report export [company]  - Export data as JSON

Examples:
  scout funding acme corp
  scout news --signals
  scout jobs --trends
  scout report company "Acme Corp"
  scout report targets 5000000 5
"""
    print(help_text)


if __name__ == "__main__":
    main()
