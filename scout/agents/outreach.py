"""OutreachAgent — generates personalized cold email and LinkedIn outreach content."""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Angle detection
# ---------------------------------------------------------------------------

ANGLE_HIRING = "growth_scaling"
ANGLE_FUNDING = "new_capital"
ANGLE_LAYOFFS = "efficiency"
ANGLE_REVIEWS = "team_morale"
ANGLE_DEFAULT = "general_value"


def _detect_angle(research_data: dict) -> str:
    """Detect the primary outreach angle from research data.

    Priority: hiring > funding > layoffs > reviews > default.
    """
    jobs = research_data.get("jobs_signal", {})
    if jobs.get("signal") == "hiring":
        return ANGLE_HIRING

    funding = research_data.get("funding", {})
    if funding.get("last_round") not in (None, "", "Unknown"):
        return ANGLE_FUNDING

    if jobs.get("signal") == "layoffs":
        return ANGLE_LAYOFFS

    reviews = research_data.get("reviews_signal", {})
    avg_rating = reviews.get("avg_rating")
    if avg_rating is not None and avg_rating < 3.5:
        return ANGLE_REVIEWS

    return ANGLE_DEFAULT


# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------

OUTREACH_SYSTEM_PROMPT = """You are Scout, an expert sales development representative.
You write personalized outreach that sounds like a real human — not a template.
You write directly, with confidence, and reference specific company signals.
Never use generic phrases like "I hope this email finds you" or "I'd love to learn more."
Keep emails short and focused (~150 words). Keep LinkedIn DMs under 80 words."""


def _build_outreach_prompt(
    company_name: str,
    angle: str,
    research_data: dict,
    contact: dict,
) -> str:
    """Build the LLM prompt for outreach generation."""
    news = research_data.get("news", [])
    jobs = research_data.get("jobs_signal", {})
    funding = research_data.get("funding", {})
    reviews = research_data.get("reviews_signal", {})
    enrichment = research_data.get("enrichment", {})

    angle_labels = {
        ANGLE_HIRING: "Hiring/Growth Pain — they're scaling fast and likely overwhelmed",
        ANGLE_FUNDING: "New Capital — they've recently raised and are in build mode",
        ANGLE_LAYOFFS: "Efficiency Pressure — they've cut headcount and need to do more with less",
        ANGLE_REVIEWS: "Team Morale — low Glassdoor ratings suggest culture or management issues",
        ANGLE_DEFAULT: "General Value — no strong signal, lead with general value prop",
    }

    contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    contact_role = contact.get("position", "")
    contact_greeting = f"Hi {contact_name}" if contact_name else "Hi there"

    news_block = "\n".join(
        f"- {n.get('title', '')}"
        for n in news[:5]
    ) or "No recent news."

    industry = enrichment.get("industry", "their sector")
    employees = enrichment.get("employee_count", "unknown size")

    prompt = f"""Generate personalized outreach for **{company_name}**.

## Company Context
- Industry: {industry}
- Size: {employees}
- Contact: {contact_name} ({contact_role})

## Detected Angle: {angle_labels.get(angle, angle)}

## Recent Signals
{news_block}

## Hiring Signal: {jobs.get('signal', 'unknown')} ({jobs.get('total_postings', 'N/A')} postings)
## Funding: {funding.get('last_round', 'Unknown')} ({funding.get('amount', 'N/A')})
## Glassdoor Rating: {reviews.get('avg_rating', 'N/A')}

---

Generate the following in exact format (replace CONTENT with actual content):

EMAIL_VARIANT_1:
Subject: [3 subject line options separated by |]
---
CONTENT

EMAIL_VARIANT_2:
Subject: [3 subject line options separated by |]
---
CONTENT

LINKEDIN_VARIANT_1:
CONTENT

LINKEDIN_VARIANT_2:
CONTENT

Rules:
- Email body: ~150 words, plain text, no markdown formatting in body
- LinkedIn DM: ~80 words, conversational
- Reference specific signals from the research (news, funding, hiring, reviews)
- {contact_greeting} opening on emails
- Sound like a human who did their homework, not a mass template
- Do NOT use phrases like "I hope this finds you well" or "I wanted to reach out because..."
- If contact role is available, tailor the message to their perspective (CEO vs CTO vs VP Sales)
"""
    return prompt


def _generate_with_llm(
    company_name: str,
    angle: str,
    research_data: dict,
    contact: dict,
) -> Optional[dict]:
    """Generate outreach using litellm LLM. Returns None if unavailable."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not has_openai and not has_anthropic:
        return None

    try:
        from litellm import completion  # type: ignore
    except ImportError:
        console.print("[yellow]Warning: litellm not installed[/yellow]")
        return None

    model = "gpt-4o-mini" if has_openai else "claude-haiku-4-5-20251001"
    prompt = _build_outreach_prompt(company_name, angle, research_data, contact)

    try:
        console.print(f"[dim]  Generating outreach with {model}...[/dim]")
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": OUTREACH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        return _parse_llm_response(response.choices[0].message.content)
    except Exception as e:
        console.print(f"[red]LLM outreach error: {e}[/red]")
        return None


# ---------------------------------------------------------------------------
# LLM response parsing
# ---------------------------------------------------------------------------

def _parse_llm_response(content: str) -> dict:
    """Parse the LLM output into structured dict."""
    emails = []
    linkedins = []
    subjects = []

    current_email_variant = None
    current_section = None

    for line in content.split("\n"):
        line = line.strip()

        if line.startswith("EMAIL_VARIANT_1:") or line.startswith("EMAIL_VARIANT_1"):
            current_section = "email"
            current_email_variant = 1
            continue
        elif line.startswith("EMAIL_VARIANT_2:") or line.startswith("EMAIL_VARIANT_2"):
            current_section = "email"
            current_email_variant = 2
            continue
        elif line.startswith("LINKEDIN_VARIANT_1:") or line.startswith("LINKEDIN_VARIANT_1"):
            current_section = "linkedin"
            current_email_variant = 1
            continue
        elif line.startswith("LINKEDIN_VARIANT_2:") or line.startswith("LINKEDIN_VARIANT_2"):
            current_section = "linkedin"
            current_email_variant = 2
            continue

        if current_section == "email" and line.startswith("Subject:"):
            subject_line = line[len("Subject:"):].strip()
            subjects.append([s.strip() for s in subject_line.split("|")])
            continue

        if current_section == "email" and current_email_variant:
            key = f"email_{current_email_variant}"
            emails.append({"subject": "", "body": line})

        if current_section == "linkedin" and current_email_variant:
            key = f"linkedin_{current_email_variant}"
            linkedins.append(line)

    # Rebuild emails with bodies
    rebuilt_emails = []
    email_body_lines = []
    current_subject_idx = -1
    in_email = False

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("EMAIL_VARIANT_"):
            if email_body_lines and current_subject_idx >= 0:
                rebuilt_emails.append({
                    "subject": subjects[current_subject_idx] if current_subject_idx < len(subjects) else [],
                    "body": " ".join(email_body_lines).strip(),
                })
            email_body_lines = []
            in_email = True
            var_num = int(line.split("_")[-1].rstrip(":"))
            current_subject_idx = var_num - 1
        elif line.startswith("LINKEDIN_VARIANT_"):
            if email_body_lines and current_subject_idx >= 0:
                rebuilt_emails.append({
                    "subject": subjects[current_subject_idx] if current_subject_idx < len(subjects) else [],
                    "body": " ".join(email_body_lines).strip(),
                })
            email_body_lines = []
            in_email = False
        elif in_email and line and not line.startswith("Subject:"):
            email_body_lines.append(line)

    if email_body_lines and current_subject_idx >= 0:
        rebuilt_emails.append({
            "subject": subjects[current_subject_idx] if current_subject_idx < len(subjects) else [],
            "body": " ".join(email_body_lines).strip(),
        })

    # Parse LinkedIn sections
    rebuilt_linkedins = []
    in_linkedin = False
    li_lines = []
    li_var = 0

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("LINKEDIN_VARIANT_"):
            if li_lines:
                rebuilt_linkedins.append(" ".join(li_lines).strip())
            li_lines = []
            li_var = int(line.split("_")[-1].rstrip(":"))
            in_linkedin = True
        elif in_linkedin and li_var > 0:
            li_lines.append(line)

    if li_lines:
        rebuilt_linkedins.append(" ".join(li_lines).strip())

    # Fallback if parsing produced nothing
    if not rebuilt_emails:
        rebuilt_emails = [{"subject": s, "body": ""} for s in subjects] if subjects else [{"subject": [], "body": ""}]
    if not rebuilt_linkedins:
        rebuilt_linkedins = [""]

    return {
        "cold_emails": [e["body"] for e in rebuilt_emails[:2]],
        "linkedin_messages": rebuilt_linkedins[:2],
        "subject_lines": subjects[:2] if subjects else [[] for _ in rebuilt_emails],
    }


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

_EMAIL_BODIES = {
    ANGLE_HIRING: [
        "Hi {first_name}, I noticed {company} is actively hiring — {count} open roles right now. "
        "Scaling teams like that creates real pressure: new people need training, processes break down, "
        "and onboarding eats into senior bandwidth. "
        "We've helped companies in {industry} cut onboarding time in half while keeping quality up. "
        "Worth a quick chat to see if that'd be relevant to your team at this stage of growth?",
        "{first_name}, the hiring push at {company} caught my attention — growing fast is a great problem to have, "
        "but it also means your senior people are stretched thin between doing the work and teaching others. "
        "Curious if that's resonates with what you're seeing on the ground, and whether tools that scale expertise "
        "would be useful at this stage. Happy to share what's worked for similar teams.",
    ],
    ANGLE_FUNDING: [
        "Hi {first_name}, congrats on the recent {round} — raise momentum is a strong signal that "
        "{company} is in build mode. Companies that just raised tend to move fast on tools "
        "that help them execute. Curious what your current priorities are and whether "
        "something that accelerates team productivity would fit the roadmap right now.",
        "{first_name}, saw the news about {company}'s raise. Fresh capital usually means accelerated hiring "
        "and a push to scale before the next milestone. If there's a workflow or process "
        "that's slowing the team down, now's the window to fix it. Happy to share what's worked "
        "for similar-stage companies if it's useful.",
    ],
    ANGLE_LAYOFFS: [
        "{first_name}, I saw the news about the layoffs at {company}. That's never easy, "
        "and it usually means the remaining team is being asked to do more with less. "
        "That kind of pressure can hurt morale if things feel chaotic. "
        "We work with companies going through transitions to keep their teams focused and productive. "
        "Worth exploring whether there's something that could help your team right now?",
        "Hi {first_name}, layoffs are tough signals to navigate — teams left behind often carry extra load "
        "and managers don't have the bandwidth to check in on everyone. "
        "Figured it might be worth sharing how we're helping companies maintain "
        "alignment and output through periods of change. Happy to compare notes.",
    ],
    ANGLE_REVIEWS: [
        "{first_name}, I came across {company}'s Glassdoor ratings — it looks like team culture "
        "is under pressure right now. Low morale doesn't just affect retention, "
        "it affects output and the ability to attract good people. "
        "We've seen companies address this without massive restructuring. "
        "Happy to share what's worked if that's relevant to where you're at.",
        "Hi {first_name}, the review trends at {company} stood out — when people aren't happy at work, "
        "they leave, and replacing them is expensive. "
        "Before going down the recruiting route, it might be worth looking at "
        "what's driving the dissatisfaction. Happy to talk through possibilities.",
    ],
    ANGLE_DEFAULT: [
        "Hi {first_name}, I do some research on {industry} companies and {company} came up as "
        "someone doing interesting work in the space. I'm not selling anything urgent — "
        "more looking to understand what challenges your team is facing and whether "
        "there's a natural fit somewhere. Worth a quick call to compare notes?",
        "{first_name}, figured I'd reach out because I think what {company} is building is interesting "
        "and I wanted to understand your team's biggest challenges right now. "
        "If there's a fit, great; if not, at least I'll learn something useful. "
        "No pressure either way — happy to chat when it makes sense.",
    ],
}

_LINKEDIN_BODIES = {
    ANGLE_HIRING: [
        "Hi {first_name}, noticed {company} is scaling fast — hiring in a growth phase is exciting but intense. "
        "Happy to share how we're helping companies like yours onboard faster without burning out senior team members.",
        "{first_name}, saw the hiring push at {company}. The challenge with scaling quickly is that your best people end up "
        "training instead of doing. We fix that. Worth a quick chat?",
    ],
    ANGLE_FUNDING: [
        "Congrats on the raise, {first_name} — fresh capital means opportunity to build the team the right way. "
        "Happy to share what's worked for companies at similar stages.",
        "{first_name}, raising is a milestone worth celebrating. If you're thinking about scaling the team "
        "or workflows before the next push, happy to compare notes.",
    ],
    ANGLE_LAYOFFS: [
        "{first_name}, saw what happened at {company}. Tough times — teams left behind often need more support "
        "not less. Happy to share how we're helping companies through transitions.",
        "{first_name}, every restructuring creates a new set of challenges for the people who stay. "
        "We help teams stay aligned and productive through change. Worth a conversation?",
    ],
    ANGLE_REVIEWS: [
        "{first_name}, came across {company}'s Glassdoor scores — culture issues are hard to fix "
        "and harder to talk about openly. Happy to share what's worked for others if it's relevant.",
        "{first_name}, noticed some mixed reviews about life at {company}. Culture problems are often "
        "symptoms of process or communication gaps. Happy to explore if there's something that might help.",
    ],
    ANGLE_DEFAULT: [
        "Hi {first_name}, interesting work happening at {company}. I'm curious what challenges "
        "your team is focused on right now — happy to share what's working for others in {industry}.",
        "{first_name}, came across {company} and liked what I saw. Not trying to sell anything, "
        "just thought it might be worth comparing notes on what you're building.",
    ],
}

_SUBJECT_TEMPLATES = {
    ANGLE_HIRING: [
        "Quick question about scaling at {company}",
        "Onboarding challenge at {company}?",
        "Re: {company} hiring surge",
    ],
    ANGLE_FUNDING: [
        "Congrats on the raise, {company} team",
        "Thought on what to build next at {company}",
        "Re: {company} — post-funding priorities",
    ],
    ANGLE_LAYOFFS: [
        "Quick idea for the {company} team",
        "Thought on keeping {company} productive through transition",
        "Re: what happened at {company}",
    ],
    ANGLE_REVIEWS: [
        "Thought on team culture at {company}",
        "Fixing the {company} work experience?",
        "Re: {company} — something that might help",
    ],
    ANGLE_DEFAULT: [
        "Idea for {company}",
        "Quick note on {company}",
        "Worth a quick chat, {first_name}?",
    ],
}


def _build_rule_email(
    company_name: str,
    angle: str,
    research_data: dict,
    contact: dict,
    variant_idx: int,
) -> tuple[list[str], str]:
    """Build a rule-based email for the given angle and variant."""
    templates = _EMAIL_BODIES.get(angle, _EMAIL_BODIES[ANGLE_DEFAULT])
    template = templates[variant_idx % len(templates)]

    jobs = research_data.get("jobs_signal", {})
    funding = research_data.get("funding", {})
    reviews = research_data.get("reviews_signal", {})
    enrichment = research_data.get("enrichment", {})

    industry = enrichment.get("industry", "tech")
    count = jobs.get("total_postings", "a lot of")
    round_name = funding.get("last_round", "")
    amount = funding.get("amount", "")
    round_str = f"{round_name} {amount}".strip() if round_name else "recent funding"

    first_name = contact.get("first_name", "there")

    # Fill template
    body = template.format(
        company=company_name,
        industry=industry,
        count=count,
        round=round_str,
        first_name=first_name,
    )

    # Build subjects
    subjects_tpl = _SUBJECT_TEMPLATES.get(angle, _SUBJECT_TEMPLATES[ANGLE_DEFAULT])
    subjects = [s.format(company=company_name, first_name=first_name) for s in subjects_tpl]

    return subjects, body


def _build_rule_linkedin(
    company_name: str,
    angle: str,
    research_data: dict,
    contact: dict,
    variant_idx: int,
) -> str:
    """Build a rule-based LinkedIn message."""
    templates = _LINKEDIN_BODIES.get(angle, _LINKEDIN_BODIES[ANGLE_DEFAULT])
    template = templates[variant_idx % len(templates)]

    enrichment = research_data.get("enrichment", {})
    industry = enrichment.get("industry", "tech")
    first_name = contact.get("first_name", "there")

    body = template.format(
        company=company_name,
        first_name=first_name,
        industry=industry,
    )
    return body


# ---------------------------------------------------------------------------
# OutreachAgent
# ---------------------------------------------------------------------------

class OutreachAgent:
    """Generates personalized cold email and LinkedIn outreach content."""

    def generate(
        self,
        company_name: str,
        brief: str,
        research_data: dict,
        contacts: list[dict],
        variants: int = 2,
    ) -> dict:
        """Generate outreach content for a company.

        Args:
            company_name: Name of the company.
            brief: Sales brief text (not currently used but available for context).
            research_data: Research dict from ResearchAgent.
            contacts: List of contact dicts from Hunter.io (may be empty).
            variants: Number of email/LinkedIn variants to generate (default 2).

        Returns:
            Dict with keys: cold_emails, linkedin_messages, subject_lines
        """
        angle = _detect_angle(research_data)
        console.print(f"[dim]  Outreach angle: {angle}[/dim]")

        # Use first contact if available, else empty
        contact = contacts[0] if contacts else {}

        # Try LLM first
        llm_result = _generate_with_llm(company_name, angle, research_data, contact)

        if llm_result:
            console.print("[dim]  LLM generation successful[/dim]")
            return llm_result

        # Rule-based fallback
        console.print("[yellow]  No LLM key — using rule-based generation[/yellow]")
        return self._generate_rule_based(company_name, research_data, contacts, variants, angle)

    def _generate_rule_based(
        self,
        company_name: str,
        research_data: dict,
        contacts: list[dict],
        variants: int,
        angle: str,
    ) -> dict:
        """Generate outreach using templates when no LLM is available."""
        cold_emails = []
        linkedin_messages = []
        subject_lines = []

        for i in range(variants):
            subjects, email_body = _build_rule_email(
                company_name, angle, research_data, {}, i
            )
            cold_emails.append(email_body)
            subject_lines.append(subjects)

            li_body = _build_rule_linkedin(company_name, angle, research_data, {}, i)
            linkedin_messages.append(li_body)

        # Personalize each variant per contact if contacts available
        if contacts:
            personalized_emails = []
            personalized_linkedins = []
            personalized_subjects = []

            for i, contact in enumerate(contacts[:variants]):
                subjects, email_body = _build_rule_email(
                    company_name, angle, research_data, contact, i
                )
                personalized_emails.append(email_body)
                personalized_subjects.append(subjects)

                li_body = _build_rule_linkedin(company_name, angle, research_data, contact, i)
                personalized_linkedins.append(li_body)

            cold_emails = personalized_emails
            linkedin_messages = personalized_linkedins
            subject_lines = personalized_subjects

        return {
            "cold_emails": cold_emails,
            "linkedin_messages": linkedin_messages,
            "subject_lines": subject_lines,
        }


# ---------------------------------------------------------------------------
# CLI print helpers
# ---------------------------------------------------------------------------

def print_outreach_result(result: dict, company_name: str, contacts: list[dict]) -> None:
    """Print outreach result in a formatted Rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    cold_emails = result.get("cold_emails", [])
    linkedin_messages = result.get("linkedin_messages", [])
    subject_lines = result.get("subject_lines", [])

    # Email variants
    table = Table(
        title=f"📧 Cold Email Variants — {company_name}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Variant", style="bold", width=8)
    table.add_column("Subject", style="yellow")
    table.add_column("Body", style="white")

    for i, (body, subjects) in enumerate(zip(cold_emails, subject_lines)):
        subject_str = "\n".join(subjects) if subjects else "(no subject)"
        table.add_row(str(i + 1), subject_str, body[:200] + ("..." if len(body) > 200 else ""))

    console.print(table)

    # LinkedIn variants
    li_table = Table(
        title=f"💬 LinkedIn Message Variants — {company_name}",
        show_header=True,
        header_style="bold cyan",
    )
    li_table.add_column("Variant", style="bold", width=8)
    li_table.add_column("Message", style="white")

    for i, msg in enumerate(linkedin_messages):
        li_table.add_row(str(i + 1), msg[:200] + ("..." if len(msg) > 200 else ""))

    console.print(li_table)

    # Contacts used
    if contacts:
        contact_names = [
            f"{c.get('first_name', '')} {c.get('last_name', '')} ({c.get('position', '')})"
            for c in contacts[:2]
        ]
        console.print(f"[dim]  Personalized for: {', '.join(contact_names)}[/dim]")
