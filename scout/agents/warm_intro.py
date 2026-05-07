"""Warm Intro Finder — finds warm introduction paths to target contacts."""

from typing import Optional

from services.brave_search import BraveSearchService
from services.hunter import HunterService
from storage import intros as intro_store

# Path types and their base scores
PATH_TYPES = {
    "shared_previous_company": 70,
    "shared_education": 60,
    "shared_industry_group": 50,
    "mutual_connection": 80,
    "shared_publication": 40,
    "conference_speaker": 35,
    "general": 20,
}


def find_intro_paths(
    company_name: str,
    target_role: str = "decision maker",
    domain: str = "",
    user_background: Optional[dict] = None,
) -> dict:
    """
    Main entry point. Find warm intro paths to key contacts at a company.

    Steps:
    1. Find key contacts via Hunter.io + web search
    2. For each contact, search for their background
    3. Search for mutual connections / shared backgrounds
    4. Score and rank intro paths

    Args:
        company_name: Target company name.
        target_role: Who to reach (decision maker, champion, influencer).
        domain: Company domain for Hunter.io lookup.
        user_background: Optional dict with user's own background
                        {previous_companies[], education[], industry_groups[]}
                        to find overlap.

    Returns:
        {company_name, contacts[], intro_paths[], recommended_path, created_at}
    """
    from datetime import datetime, timezone

    # Find key contacts
    contacts = _find_key_contacts(company_name, domain, target_role)

    all_paths: list[dict] = []
    contact_backgrounds: list[dict] = []

    for contact in contacts:
        background = _research_contact_background(contact)
        contact_backgrounds.append(background)
        paths = _find_intro_paths(contact, background, user_background)
        all_paths.extend(paths)

    # Score and sort paths
    scored_paths = []
    for path in all_paths:
        path_copy = dict(path)
        path_copy["score"] = _score_intro_path(path_copy)
        scored_paths.append(path_copy)

    scored_paths.sort(key=lambda p: p["score"], reverse=True)

    # Deduplicate by suggested_introducer
    seen_introducers = set()
    unique_paths = []
    for p in scored_paths:
        introducer = p.get("suggested_introducer", "")
        if introducer and introducer not in seen_introducers:
            seen_introducers.add(introducer)
            unique_paths.append(p)

    recommended = unique_paths[0] if unique_paths else None

    result = {
        "company_name": company_name,
        "contacts": contacts,
        "intro_paths": unique_paths,
        "recommended_path": recommended,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to storage
    if contacts and unique_paths:
        primary_contact = contacts[0]
        intro_store.save_intro_request(
            company_name=company_name,
            target_contact={
                "name": primary_contact.get("name", ""),
                "email": primary_contact.get("email", ""),
                "role": primary_contact.get("role", ""),
            },
            intro_paths=unique_paths,
        )

    return result


def _find_key_contacts(company_name: str, domain: str, target_role: str) -> list[dict]:
    """Find key contacts at the company via Hunter.io + web search.

    Returns: [{name, email, role, linkedin_url, source}]
    """
    contacts: list[dict] = []

    # Try Hunter.io domain search
    if domain:
        hunter = HunterService()
        if hunter.available:
            try:
                hunter_contacts = hunter.domain_search(
                    domain=domain,
                    company=company_name,
                    seniority="senior",
                )
                for hc in hunter_contacts[:5]:
                    name = " ".join(
                        filter(None, [hc.get("first_name"), hc.get("last_name")])
                    )
                    if name:
                        contacts.append({
                            "name": name,
                            "email": hc.get("email", ""),
                            "role": hc.get("position", ""),
                            "linkedin_url": hc.get("linkedin_url", ""),
                            "source": "hunter",
                        })
            except Exception:
                pass

    # If no contacts from Hunter, use web search
    if not contacts:
        search = BraveSearchService()
        if search.available:
            query = f'"{company_name}" {target_role} LinkedIn'
            results = search.search(query, count=5)
            for r in results:
                title = r.get("title", "")
                url = r.get("url", "")
                desc = r.get("description", "")
                # Extract name from title (usually "Name - Role - Company" or "Name | Role | Company")
                name = ""
                for sep in [" - ", " | ", " – "]:
                    if sep in title:
                        name = title.split(sep)[0].strip()
                        break
                if not name and title:
                    name = title.split("|")[0].strip().split("-")[0].strip()
                if name and len(name) > 2 and len(name) < 60:
                    contacts.append({
                        "name": name,
                        "email": "",
                        "role": desc[:100] if desc else target_role,
                        "linkedin_url": url if "linkedin" in url.lower() else "",
                        "source": "search",
                    })

    # Deduplicate by name
    seen_names: set[str] = set()
    unique: list[dict] = []
    for c in contacts:
        if c["name"].lower() not in seen_names:
            seen_names.add(c["name"].lower())
            unique.append(c)
    return unique[:5]


def _research_contact_background(contact: dict) -> dict:
    """Search for a contact's professional background via web search.

    Returns: {previous_companies[], education[], publications[], groups[]}
    """
    search = BraveSearchService()
    name = contact.get("name", "")
    company = contact.get("role", "")

    background: dict[str, list] = {
        "previous_companies": [],
        "education": [],
        "publications": [],
        "groups": [],
    }

    if not search.available:
        return background

    # Search for name + background
    queries = [
        f'"{name}" background experience',
        f'"{name}" previous company',
        f'"{name}" LinkedIn alumni',
    ]

    for query in queries[:2]:
        results = search.search(query, count=5)
        for r in results:
            desc = r.get("description", "").lower()
            title = r.get("title", "").lower()
            text = desc + " " + title

            # Detect education
            edu_keywords = ["university", "college", "school", "phd", "bachelor", "master", "mba", "graduated"]
            for kw in edu_keywords:
                if kw in text and kw.title() not in background["education"]:
                    # Try to extract school name
                    for word in r.get("title", "").split():
                        if word and word[0].isupper() and len(word) > 3:
                            background["education"].append(word.title())
                            break
                    if len(background["education"]) < 5:
                        pass

            # Detect previous companies
            company_kw = ["at ", "previously at ", "formerly at ", "ex-"]
            for kw in company_kw:
                if kw in text:
                    idx = text.index(kw) + len(kw)
                    rest = text[idx:idx+50]
                    # Grab the next word sequence
                    words = rest.split()[:3]
                    if words:
                        background["previous_companies"].append(" ".join(w.capitalize() for w in words))

    # Remove duplicates
    background["previous_companies"] = list(set(background["previous_companies"]))[:5]
    background["education"] = list(set(background["education"]))[:5]

    return background


def _find_intro_paths(
    contact: dict,
    background: dict,
    user_background: Optional[dict],
) -> list[dict]:
    """Find warm intro paths by comparing contact background with user background.

    Search strategy:
    - If user_background provided: look for direct overlap
    - If not: search for common industry connections via web

    Returns: [{path_type, score, reason, suggested_introducer}]
    """
    paths: list[dict] = []

    if user_background:
        user_companies = [c.lower() for c in user_background.get("previous_companies", [])]
        user_edu = [e.lower() for e in user_background.get("education", [])]
        user_groups = [g.lower() for g in user_background.get("industry_groups", [])]

        contact_companies = [c.lower() for c in background.get("previous_companies", [])]
        contact_edu = [e.lower() for e in background.get("education", [])]
        contact_groups = [g.lower() for g in background.get("groups", [])]

        # Shared previous company
        for uc in user_companies:
            for cc in contact_companies:
                if uc and cc and uc == cc:
                    paths.append({
                        "path_type": "shared_previous_company",
                        "suggested_introducer": f"Contact at {uc.title()}",
                        "reason": f"You and {contact.get('name', 'the contact')} both worked at {uc.title()}",
                        "contact": contact.get("name", ""),
                    })

        # Shared education
        for ue in user_edu:
            for ce in contact_edu:
                if ue and ce and ue == ce:
                    paths.append({
                        "path_type": "shared_education",
                        "suggested_introducer": f"Alumni network at {ue.title()}",
                        "reason": f"You and {contact.get('name', 'the contact')} both attended {ue.title()}",
                        "contact": contact.get("name", ""),
                    })

        # Shared industry group
        for ug in user_groups:
            for cg in contact_groups:
                if ug and cg and ug == cg:
                    paths.append({
                        "path_type": "shared_industry_group",
                        "suggested_introducer": f"Member of {ug.title()}",
                        "reason": f"You and {contact.get('name', 'the contact')} are both in {ug.title()}",
                        "contact": contact.get("name", ""),
                    })
    else:
        # No user background — do a general search for mutual connections
        search = BraveSearchService()
        if search.available:
            name = contact.get("name", "")
            query = f'"{name}" mutual connection OR shared contact OR alumni'
            results = search.search(query, count=3)
            for r in results:
                paths.append({
                    "path_type": "mutual_connection",
                    "suggested_introducer": r.get("title", "Check LinkedIn"),
                    "reason": r.get("description", ""),
                    "contact": name,
                })

    # If still no paths found, add a general path
    if not paths:
        paths.append({
            "path_type": "general",
            "suggested_introducer": "Research further via LinkedIn",
            "reason": f"No direct shared background found — recommend deeper LinkedIn research for {contact.get('name', 'the contact')}",
            "contact": contact.get("name", ""),
        })

    # Deduplicate
    seen = set()
    unique = []
    for p in paths:
        key = (p["path_type"], p.get("suggested_introducer", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


def _score_intro_path(path: dict) -> int:
    """Score an intro path (0-100). Base score from PATH_TYPES, adjusted by recency."""
    path_type = path.get("path_type", "general")
    base = PATH_TYPES.get(path_type, PATH_TYPES["general"])

    # Recency bonus: not applicable here since we don't track dates
    # Confidence bonus: if we have a specific introducer name
    bonus = 0
    introducer = path.get("suggested_introducer", "")
    if introducer and "general" not in introducer.lower() and "research" not in introducer.lower():
        bonus = 10

    return min(base + bonus, 100)


def _generate_intro_request(contact: dict, paths: list[dict], company_name: str) -> str:
    """Use LLM to generate a warm intro request message.

    Takes the best intro path and generates a polite, specific request.
    """
    try:
        import anthropic
        import os

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        best_path = paths[0] if paths else {}

        intro_context = (
            f"Contact: {contact.get('name', 'Unknown')} ({contact.get('role', '')}) at {company_name}\n"
            f"Intro path: {best_path.get('path_type', 'general')}\n"
            f"Reason: {best_path.get('reason', '')}\n"
            f"Introducer: {best_path.get('suggested_introducer', 'TBD')}"
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a concise, professional warm intro request message. "
                        f"Context:\n{intro_context}\n\n"
                        f"Keep it under 100 words. Be specific about the shared connection. "
                        f"Do not be pushy."
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception:
        return (
            f"Hi, I noticed we share a connection via {best_path.get('suggested_introducer', 'LinkedIn')}. "
            f"I'm interested in connecting with {contact.get('name', 'the team')} at {company_name}. "
            f"Would you be open to making an introduction?"
        )


def print_intro_result(result: dict) -> None:
    """Pretty-print intro finder results using Rich console."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print(f"\n[bold cyan]Warm Intro Finder: {result['company_name']}[/bold cyan]")

    # Contacts
    contacts = result.get("contacts", [])
    if contacts:
        console.print("\n[bold]Key Contacts Found:[/bold]")
        for c in contacts:
            name = c.get("name", "Unknown")
            role = c.get("role", "")
            email = c.get("email", "")
            source = c.get("source", "")
            console.print(f"  • {name} — {role} {f'({email})' if email else ''} [dim][{source}][/dim]")

    # Intro paths
    paths = result.get("intro_paths", [])
    if paths:
        console.print(f"\n[bold]Warm Intro Paths ({len(paths)}):[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Suggested Introducer", style="green")
        table.add_column("Reason")

        for p in paths[:8]:
            score = p.get("score", 0)
            score_color = "green" if score >= 70 else "yellow" if score >= 50 else "dim"
            table.add_row(
                p.get("path_type", ""),
                f"[{score_color}]{score}[/{score_color}]",
                p.get("suggested_introducer", "—"),
                p.get("reason", "")[:60],
            )
        console.print(table)

    # Recommended path
    recommended = result.get("recommended_path")
    if recommended:
        console.print(f"\n[bold green]Recommended Intro Path:[/bold green]")
        console.print(f"  {recommended.get('reason', '')}")
        console.print(f"  [dim]Via: {recommended.get('suggested_introducer', '')} (score: {recommended.get('score', 0)})[/dim]")
    else:
        console.print("\n[yellow]No strong intro paths found.[/yellow]")
