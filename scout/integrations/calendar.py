"""Google Calendar integration for MeetingPrep.

Uses the gog CLI (already authenticated) to fetch upcoming meetings
and extract company names + attendee emails for prep briefs.
"""

import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional


def _run_gog(args: list[str]) -> Optional[str]:
    """Run a gog command and return stdout."""
    try:
        result = subprocess.run(
            ["gog"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def get_upcoming_events(hours_ahead: int = 24) -> list[dict]:
    """Fetch calendar events within the next N hours.

    Returns:
        List of event dicts with keys: event_id, title, start, end, attendees[], summary.
    """
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=hours_ahead)

    # Format for gog: YYYY-MM-DDTHH:MM:SSZ
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = later.strftime("%Y-%m-%dT%H:%M:%SZ")

    output = _run_gog([
        "calendar", "events", "list",
        "--format", "json",
        "--time-min", time_min,
        "--time-max", time_max,
    ])

    if not output:
        return []

    try:
        raw_events = json.loads(output)
    except json.JSONDecodeError:
        return []

    events = []
    for ev in raw_events:
        # Extract attendees
        attendees = []
        for att in ev.get("attendees", []):
            email = att.get("email", "")
            if email and email != ev.get("organizer", {}).get("email", ""):
                attendees.append({
                    "email": email,
                    "name": att.get("displayName", ""),
                    "response": att.get("responseStatus", ""),
                })

        # Extract start time
        start = ev.get("start", {})
        start_time = start.get("dateTime") or start.get("date", "")

        events.append({
            "event_id": ev.get("id", ""),
            "title": ev.get("summary", ""),
            "start": start_time,
            "end": ev.get("end", {}).get("dateTime", ""),
            "attendees": attendees,
            "summary": ev.get("description", ""),
            "location": ev.get("location", ""),
        })

    return events


def extract_company_name(event: dict) -> Optional[str]:
    """Try to extract a company name from a calendar event.

    Heuristics:
    1. Look for "Meeting with [Company]" or "[Company] meeting" patterns
    2. Extract domain from attendee emails (most common)
    3. Use event title as fallback
    """
    title = event.get("title", "")
    attendees = event.get("attendees", [])

    # Pattern: "Meeting with Acme", "Acme Corp Call", "Acme - Intro"
    patterns = [
        r"(?:meeting|call|sync|intro|demo|review)\s+(?:with|for)\s+(.+?)(?:\s*$|\s*[-–—])",
        r"^(.+?)\s*[-–—]\s*(?:meeting|call|sync|intro|demo|review)",
        r"^(.+?)\s+(?:meeting|call|sync|intro|demo|review)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and len(company) < 100:
                return company

    # Fallback: extract company from attendee email domain
    # Skip generic domains
    generic_domains = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "icloud.com", "me.com", "aol.com", "protonmail.com",
    }
    for att in attendees:
        email = att.get("email", "")
        domain = email.split("@")[-1] if "@" in email else ""
        if domain and domain.lower() not in generic_domains:
            # Convert domain to company name: "acme.com" -> "Acme"
            company = domain.split(".")[0].title()
            return company

    return None


def get_upcoming_prep_candidates(hours_ahead: int = 24) -> list[dict]:
    """Get meetings that need prep, with extracted company + attendees.

    Returns:
        List of dicts: {company_name, attendee_emails[], meeting_time, event_id, title}
    """
    events = get_upcoming_events(hours_ahead)
    candidates = []

    for event in events:
        company_name = extract_company_name(event)
        if not company_name:
            continue

        attendee_emails = [a["email"] for a in event.get("attendees", []) if a.get("email")]

        candidates.append({
            "company_name": company_name,
            "attendee_emails": attendee_emails,
            "meeting_time": event.get("start", ""),
            "event_id": event.get("event_id", ""),
            "title": event.get("title", ""),
        })

    return candidates
