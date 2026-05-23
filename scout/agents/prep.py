"""MeetingPrepAgent - generates meeting preparation content using AI."""

import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Optional


def _web_search(query: str) -> str:
    """Run a web search via Exa/gemini or fallback to a simple subprocess call.

    Args:
        query: Search query string.

    Returns:
        Raw search results as a string.
    """
    # Try using the system's configured search tool
    # This uses a simple subprocess approach to invoke a search
    try:
        result = subprocess.run(
            ["python", "-c", f"from tools.web import search; print(search({repr(query)}))"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Fallback: use curl to search via DuckDuckGo
    try:
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "10",
                f"https://duckduckgo.com/?q={query.replace(' ', '+')}&format=json",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout[:2000] if result.stdout else ""
    except Exception:
        return ""


def _extract_name_from_email(email: str) -> str:
    """Extract a name guess from an email address.

    Args:
        email: Email address like john.doe@company.com.

    Returns:
        Capitalized name like 'John Doe'.
    """
    local = email.split("@")[0]
    # Handle dots, underscores, numbers
    name = re.sub(r"[._\d]+", " ", local)
    name = name.strip()
    # Title case
    return name.title()


def _research_attendees(emails: list[str]) -> list[dict]:
    """Research each attendee by email address.

    Args:
        emails: List of email addresses.

    Returns:
        List of dicts with keys: name, title, company, background.
    """
    results = []
    for email in emails:
        name = _extract_name_from_email(email)
        domain = email.split("@")[1] if "@" in email else ""

        # Search for attendee background
        search_query = f"{name} {domain} professional background"
        search_results = _web_search(search_query)

        attendee = {
            "name": name,
            "title": "",
            "company": domain,
            "background": search_results[:500] if search_results else "",
        }
        results.append(attendee)

    return results


def _build_prep_content(
    company_data: Optional[dict],
    attendee_data: list[dict],
    meeting_time: Optional[str],
) -> dict:
    """Generate meeting prep content using an LLM.

    Args:
        company_data: Company info dict from company_store.
        attendee_data: List of attendee research dicts.
        meeting_time: ISO datetime string or None.

    Returns:
        Dict with keys: context, pain_points, questions, topics_to_avoid, key_facts.
    """
    try:
        import anthropic
    except ImportError:
        return _fallback_prep_content(company_data, attendee_data, meeting_time)

    client = anthropic.Anthropic()
    model = "claude-sonnet-4-20250514"

    company_name = company_data.get("name", "Unknown Company") if company_data else "Unknown Company"
    company_domain = company_data.get("domain", "") if company_data else ""

    # Build context string for the prompt
    attendees_text = "\n".join(
        f"- {a['name']} ({a.get('title', 'Unknown title')}) at {a.get('company', 'Unknown')}: {a.get('background', 'No background info')[:200]}"
        for a in attendee_data
    )

    system_prompt = (
        "You are an expert sales development representative preparing for a client meeting. "
        "Generate concise, actionable meeting prep content. "
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "context": "string - 2-3 sentence meeting context/summary",\n'
        '  "pain_points": ["string", "string", "string"],\n'
        '  "questions": ["string", "string", "string", "string", "string"],\n'
        '  "topics_to_avoid": ["string", "string"],\n'
        '  "key_facts": ["string", "string", "string"]\n'
        "}\n"
        "pain_points: specific challenges this type of company faces.\n"
        "questions: exactly 5 open-ended questions to ask the client.\n"
        "topics_to_avoid: sensitive topics or off-limits subjects.\n"
        "key_facts: important facts about the company or attendees."
    )

    user_message = f"""Meeting with {company_name} ({company_domain}).

Meeting time: {meeting_time or 'TBD'}

Attendees:
{attendees_text}

Generate the meeting prep content in JSON format."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()
        # Try to extract JSON from the response
        if "```json" in raw_text:
            start = raw_text.index("```json") + 7
            end = raw_text.rindex("```")
            raw_text = raw_text[start:end].strip()
        elif "```" in raw_text:
            start = raw_text.index("```") + 3
            end = raw_text.rindex("```")
            raw_text = raw_text[start:end].strip()

        parsed = json.loads(raw_text)
        return parsed

    except Exception:
        return _fallback_prep_content(company_data, attendee_data, meeting_time)


def _fallback_prep_content(
    company_data: Optional[dict],
    attendee_data: list[dict],
    meeting_time: Optional[str],
) -> dict:
    """Fallback prep content when LLM is unavailable."""
    company_name = company_data.get("name", "the company") if company_data else "the company"

    return {
        "context": f"Meeting scheduled with {company_name}.",
        "pain_points": ["Understanding current workflow", "Identifying inefficiencies", "Budget constraints"],
        "questions": [
            "What are your current priorities?",
            "What challenges are you facing?",
            "What would success look like?",
            "Who else is involved in this decision?",
            "What is your timeline?",
        ],
        "topics_to_avoid": ["Competitor pricing", "Legal issues"],
        "key_facts": [f"Meeting with {company_name}", f"Attendees: {len(attendee_data)}", f"Scheduled: {meeting_time or 'TBD'}"],
    }


class MeetingPrepAgent:
    """Generates meeting preparation content for sales calls."""

    def __init__(self, company_store=None) -> None:
        """Initialize the agent.

        Args:
            company_store: Optional company storage module for lookups.
        """
        self.company_store = company_store

    def generate_prep(
        self,
        company_name: str,
        attendee_emails: list[str],
        meeting_time: Optional[str] = None,
    ) -> dict:
        """Generate meeting prep content.

        Args:
            company_name: Name of the company.
            attendee_emails: List of attendee email addresses.
            meeting_time: Optional ISO datetime string for the meeting.

        Returns:
            Dict containing:
                - meeting_id: UUID string
                - company_name: str
                - attendees: list of email strings
                - prep_content: dict with context, pain_points, questions, topics_to_avoid, key_facts
                - meeting_time: str or None
                - created_at: ISO datetime string
                - status: str ("scheduled")
        """
        # Lookup company data
        company_data = None
        if self.company_store:
            try:
                company_data = self.company_store.get_by_name(company_name)
            except Exception:
                pass

        # Research attendees
        attendee_data = _research_attendees(attendee_emails)

        # Build prep content
        prep_content = _build_prep_content(company_data, attendee_data, meeting_time)

        # Create meeting prep record
        now = datetime.now(timezone.utc)
        meeting_id = str(uuid.uuid4())

        result = {
            "meeting_id": meeting_id,
            "company_name": company_name,
            "attendees": attendee_emails,
            "prep_content": prep_content,
            "meeting_time": meeting_time,
            "created_at": now.isoformat(),
            "status": "scheduled",
        }

        # Store the prep
        try:
            from storage import meeting_prep as meeting_prep_store
            meeting_prep_store.store(meeting_id, result)
        except Exception:
            pass  # Storage failure should not fail the whole operation

        return result
