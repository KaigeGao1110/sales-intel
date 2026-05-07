"""Slash command handlers for Scout Slack Bot.

Each handler calls into the existing Scout agents (ScoutAgent, MonitorAgent,
LeadScoringAgent, OutreachAgent) and returns Slack Block Kit messages.
"""

import sys
from pathlib import Path
from typing import Optional

# Allow imports from parent package
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import scout as scout_agent_module
from agents import scoring as scoring_module
from agents import outreach as outreach_module
from agents import monitor as monitor_module
from agents import research as research_module
from agents.alert import _lookup_contacts
from storage import companies as company_store
from storage import scores as score_store
from storage import snapshots as snapshot_store


# ---------------------------------------------------------------------------
# Grade emoji / color helpers
# ---------------------------------------------------------------------------

_GRADE_EMOJI = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴"}
_GRADE_COLOR = {"A": "#00aa00", "B": "#0070aa", "C": "#ffaa00", "D": "#ff0000"}


def _grade_blocks(grade: str) -> list[dict]:
    emoji = _GRADE_EMOJI.get(grade, "⚪")
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Grade: *{emoji} {grade}*",
            },
        },
    ]


def _top_signal_from_reasons(reasons: list[str]) -> str:
    """Extract the top (highest-scoring) signal from reasons list."""
    max_pts = 0
    top = ""
    for reason in reasons:
        try:
            pts = int(reason.split("(")[-1].replace("pts)", ""))
            if pts > max_pts and pts > 0:
                max_pts = pts
                top = reason.split(":")[1].split("(")[0].strip()
        except Exception:
            pass
    return top[:80] if top else "—"


# ---------------------------------------------------------------------------
# /scout-rank
# ---------------------------------------------------------------------------

def handle_rank() -> dict:
    """Handle /scout-rank — respond with ranked table of all monitored companies."""
    try:
        scorer = scoring_module.LeadScoringAgent()
        results = scorer.rank_all()
    except Exception as e:
        return _error_blocks(f"Failed to rank companies: {e}")

    if not results:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No active companies to rank.\nAdd companies with `/scout-add [company name]`",
                    },
                }
            ],
        }

    # Build table rows — Slack fields array supports 2 columns per row
    header_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🏆 Lead Rankings",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    rows = []
    for r in results:
        grade = r["grade"]
        emoji = _GRADE_EMOJI.get(grade, "⚪")
        top_sig = _top_signal_from_reasons(r["reasons"])
        action = r["recommended_action"][:50] + ("..." if len(r["recommended_action"]) > 50 else "")

        rows.append(
            f"*{emoji} {r['company_name']}*  |  Score: *{r['score']}*  |  Grade: {grade}\n"
            f"Signal: {top_sig}\n"
            f"→ {action}"
        )

    # Split into chunks of 10 for readability
    block_items: list[dict] = []
    for row in rows:
        block_items.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": row},
            }
        )

    return {
        "response_type": "in_channel",
        "blocks": header_blocks + block_items,
    }


# ---------------------------------------------------------------------------
# /scout-add
# ---------------------------------------------------------------------------

def handle_add(company_name: str) -> dict:
    """Handle /scout-add [company_name] — add to monitoring and run initial scout."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-add [company name]`")

    company_name = company_name.strip()

    # Check if already monitored
    existing = company_store.get_by_name(company_name)
    if existing:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ `{company_name}` is already being monitored.\n"
                                f"Run `/scout-score {company_name}` to see its current score.",
                    },
                }
            ],
        }

    try:
        # Run ScoutAgent
        scout = scout_agent_module.ScoutAgent()
        brief = scout.scout(company_name=company_name, add_to_monitoring=True)

        # Reload company after scout
        company = company_store.get_by_name(company_name)
        company_id = company["id"] if company else ""

        # Score it
        snapshot = snapshot_store.get_latest(company_id) if company_id else None
        if snapshot:
            research_data = {
                "news": snapshot.get("news", []),
                "jobs_signal": snapshot.get("jobs", {}),
                "funding": snapshot.get("funding", {}),
                "reviews_signal": snapshot.get("reviews", {}),
            }
            scorer = scoring_module.LeadScoringAgent()
            score_result = scorer.score(company_name, research_data)
            score_store.save(
                company_id=company_id,
                company_name=company_name,
                score=score_result["score"],
                grade=score_result["grade"],
                reasons=score_result["reasons"],
                recommended_action=score_result["recommended_action"],
            )
            grade = score_result["grade"]
            emoji = _GRADE_EMOJI.get(grade, "⚪")
            score_text = f"\n{emoji} Grade: *{grade}* — Score: *{score_result['score']}*"
        else:
            score_text = ""

        summary_lines = []
        if brief:
            # First 300 chars of brief as summary
            preview = brief.strip()[:300].replace("\n", " ")
            summary_lines.append(f"__{preview}..._")

        blocks: list[dict] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *{company_name}* added to monitoring.{score_text}",
                },
            },
        ]
        if summary_lines:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(summary_lines)},
                }
            )

        return {"response_type": "in_channel", "blocks": blocks}

    except Exception as e:
        return _error_blocks(f"Failed to scout {company_name}: {e}")


# ---------------------------------------------------------------------------
# /scout-score
# ---------------------------------------------------------------------------

def handle_score(company_name: str) -> dict:
    """Handle /scout-score [company_name] — show score breakdown."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-score [company name]`")

    company_name = company_name.strip()

    company = company_store.get_by_name(company_name)
    if not company:
        return _error_blocks(
            f"`{company_name}` not found in monitoring.\n"
            f"Add it with `/scout-add {company_name}` first."
        )

    company_id = company["id"]

    # Load latest score
    score_data = score_store.get_latest(company_id)
    if not score_data:
        return _error_blocks(
            f"No score found for `{company_name}`. "
            f"Run `/scout-rank` or `/scout-monitor` to score it first."
        )

    score = score_data["score"]
    grade = score_data["grade"]
    reasons = score_data.get("reasons", [])
    action = score_data.get("recommended_action", "")

    emoji = _GRADE_EMOJI.get(grade, "⚪")

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Score: {company_name}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Score:*\n*{score}*",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Grade:*\n{emoji} *{grade}*",
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Breakdown:*",
            },
        },
    ]

    # Add each reason as a bullet
    for reason in reasons:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"• {reason}"},
            }
        )

    blocks.extend([
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action:*\n{action}",
            },
        },
    ])

    return {"response_type": "in_channel", "blocks": blocks}


# ---------------------------------------------------------------------------
# /scout-outreach
# ---------------------------------------------------------------------------

_ANGLE_EMOJI = {
    "growth_scaling": "🚀",
    "new_capital": "💰",
    "efficiency": "📉",
    "team_morale": "💬",
    "general_value": "🎯",
}


def _detect_angle(research_data: dict) -> str:
    jobs = research_data.get("jobs_signal", {})
    if jobs.get("signal") == "hiring":
        return "growth_scaling"
    funding = research_data.get("funding", {})
    if funding.get("last_round") not in (None, "", "Unknown"):
        return "new_capital"
    if jobs.get("signal") == "layoffs":
        return "efficiency"
    reviews = research_data.get("reviews_signal", {})
    if reviews.get("avg_rating") is not None and reviews.get("avg_rating") < 3.5:
        return "team_morale"
    return "general_value"


def handle_outreach(company_name: str) -> dict:
    """Handle /scout-outreach [company_name] — generate outreach content."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-outreach [company name]`")

    company_name = company_name.strip()

    company = company_store.get_by_name(company_name)
    domain = company.get("domain", "") if company else ""

    # Load research data from snapshot or run fresh
    research_data = None
    if company:
        snapshot = snapshot_store.get_latest(company["id"])
        if snapshot:
            research_data = {
                "company_name": company_name,
                "news": snapshot.get("news", []),
                "jobs_signal": snapshot.get("jobs", {}),
                "funding": snapshot.get("funding", {}),
                "reviews_signal": snapshot.get("reviews", {}),
                "raw_signals": snapshot.get("raw_signals", []),
                "enrichment": {},
            }

    if not research_data:
        # Run fresh research
        try:
            agent = research_module.ResearchAgent()
            research_data = agent.research(company_name, domain=domain)
        except Exception as e:
            return _error_blocks(f"Research failed for {company_name}: {e}")

    # Look up contacts
    contacts = _lookup_contacts(company_name, domain=domain)

    # Generate outreach
    try:
        outreach = outreach_module.OutreachAgent()
        result = outreach.generate(
            company_name=company_name,
            brief="",
            research_data=research_data,
            contacts=contacts,
            variants=2,
        )
    except Exception as e:
        return _error_blocks(f"Outreach generation failed: {e}")

    cold_emails = result.get("cold_emails", [])
    linkedin_messages = result.get("linkedin_messages", [])
    subject_lines = result.get("subject_lines", [])

    angle = _detect_angle(research_data)
    angle_emoji = _ANGLE_EMOJI.get(angle, "🎯")
    angle_label = {
        "growth_scaling": "🚀 Hiring/Growth",
        "new_capital": "💰 New Funding",
        "efficiency": "📉 Efficiency/Layoffs",
        "team_morale": "💬 Team Morale",
        "general_value": "🎯 General",
    }.get(angle, "🎯")

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📬 Outreach: {company_name}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Angle: {angle_label}"},
            ],
        },
        {"type": "divider"},
    ]

    # Email variants — collapsible sections using sections with fields
    for i, (body, subjects) in enumerate(zip(cold_emails, subject_lines)):
        subject_str = " | ".join(subjects) if subjects else "(no subject)"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📧 Email Variant {i + 1}:*\n```Subject: {subject_str}\n\n{body[:400]}```",
                },
            }
        )
        if len(body) > 400:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"__{body[400:700]}...__"},
                    ],
                }
            )

    blocks.append({"type": "divider"})

    # LinkedIn variants
    for i, msg in enumerate(linkedin_messages):
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💬 LinkedIn Variant {i + 1}:*\n```{msg[:400]}```",
                },
            }
        )
        if len(msg) > 400:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"__{msg[400:600]}...__"},
                    ],
                }
            )

    # Contacts used
    if contacts:
        contact_names = [
            f"{c.get('first_name', '')} {c.get('last_name', '')} ({c.get('position', '')})"
            for c in contacts[:2]
        ]
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_Personalized for: {', '.join(contact_names)}_",
                    },
                ],
            }
        )

    return {"response_type": "in_channel", "blocks": blocks}


# ---------------------------------------------------------------------------
# /scout-monitor
# ---------------------------------------------------------------------------

def handle_monitor() -> dict:
    """Handle /scout-monitor — run MonitorAgent on all companies."""
    try:
        agent = monitor_module.MonitorAgent()
        results = agent.run_all()

        checked = len(results)
        alerts_fired = sum(1 for r in results if r.get("alert_triggered"))

        blocks: list[dict] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Monitor run complete*\n"
                            f"Checked: *{checked}* companies | "
                            f"Alerts fired: *{alerts_fired}*",
                },
            }
        ]

        return {"response_type": "in_channel", "blocks": blocks}

    except Exception as e:
        return _error_blocks(f"Monitor run failed: {e}")


# ---------------------------------------------------------------------------
# /scout-help
# ---------------------------------------------------------------------------

def handle_help() -> dict:
    """Handle /scout-help — show available commands."""
    commands = [
        ("`/scout-rank`", "View all monitored companies ranked by score"),
        ("`/scout-add [name]`", "Add a company to monitoring and run initial scout"),
        ("`/scout-score [name]`", "Show score breakdown for a company"),
        ("`/scout-outreach [name]`", "Generate personalized outreach content"),
        ("`/scout-monitor`", "Run monitoring checks on all companies"),
        ("`/scout-prep [name] [emails]`", "Generate meeting prep brief (e.g. `/scout-prep Acme john@acme.com`)"),
        ("`/scout-warm-intro [name]`", "Find warm intro paths to contacts at a company"),
        ("`/scout-track [name] [stage]`", "Track a company as pipeline deal (e.g. `/scout-track Acme proposal`)"),
        ("`/scout-pipeline`", "View all pipeline deals with health scores"),
        ("`/scout-help`", "Show this help message"),
    ]

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Scout Bot — Available Commands",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    for cmd, desc in commands:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{cmd}\n_{desc}_"},
            }
        )

    blocks.extend([
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Powered by Scout Sales Intelligence",
                },
            ],
        },
    ])

    return {"response_type": "ephemeral", "blocks": blocks}


# ---------------------------------------------------------------------------
# /scout-prep
# ---------------------------------------------------------------------------

def handle_prep(company_name: str, attendee_emails: str = "") -> dict:
    """Handle /scout-prep [company_name] [emails...] — generate meeting prep brief."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-prep [company name] [email1,email2,...]`")

    company_name = company_name.strip()
    emails = [e.strip() for e in attendee_emails.split(",") if e.strip()] if attendee_emails else []

    try:
        from agents.prep import MeetingPrepAgent

        agent = MeetingPrepAgent()
        prep_data = agent.generate_prep(company_name, emails)
    except Exception as e:
        return _error_blocks(f"Meeting prep failed: {e}")

    if "error" in prep_data:
        return _error_blocks(prep_data["error"])

    content = prep_data.get("prep_content", {})

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Meeting Prep: {company_name}",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    # Context
    if content.get("context"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Context:*\n{content['context'][:500]}"},
        })

    # Pain points
    if content.get("pain_points"):
        pp_text = "\n".join(f"• {p}" for p in content["pain_points"][:5])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*⚠️ Pain Points:*\n{pp_text}"},
        })

    # Questions
    if content.get("questions"):
        q_text = "\n".join(f"• {q}" for q in content["questions"][:5])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*💡 Opening Questions:*\n{q_text}"},
        })

    # Topics to avoid
    if content.get("topics_to_avoid"):
        avoid_text = "\n".join(f"• {t}" for t in content["topics_to_avoid"][:3])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🚫 Topics to Avoid:*\n{avoid_text}"},
        })

    return {"response_type": "in_channel", "blocks": blocks}


# ---------------------------------------------------------------------------
# /scout-track
# ---------------------------------------------------------------------------

def handle_track(company_name: str, args: str = "") -> dict:
    """Handle /scout-track [company_name] [stage] — start tracking as pipeline deal."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-track [company] [stage]` (stages: discovery|qualification|proposal|negotiation|poc)")

    company_name = company_name.strip()
    stage = "discovery"
    if args and args.strip():
        stage = args.strip().lower()

    valid_stages = ["discovery", "qualification", "proposal", "negotiation", "poc", "closed_won", "closed_lost"]
    if stage not in valid_stages:
        return _error_blocks(f"Invalid stage: `{stage}`. Valid stages: {', '.join(valid_stages)}")

    try:
        from storage import pipeline as pipeline_store

        opp = pipeline_store.track_opportunity(
            company_name=company_name,
            stage=stage,
        )
    except Exception as e:
        return _error_blocks(f"Failed to track: {e}")

    health = opp.get("health_score", 50)
    health_emoji = "🟢" if health >= 70 else "🟡" if health >= 40 else "🔴"

    return {
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📌 Now tracking *{company_name}* as pipeline opportunity\n"
                            f"Stage: *{stage}* | Health: {health_emoji} *{health}/100*",
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# /scout-pipeline
# ---------------------------------------------------------------------------

def handle_pipeline() -> dict:
    """Handle /scout-pipeline — show all pipeline deals with health scores."""
    try:
        from agents.pipeline import PipelineIntelligenceAgent

        agent = PipelineIntelligenceAgent()
        summary = agent.get_pipeline_summary()
    except Exception as e:
        return _error_blocks(f"Pipeline query failed: {e}")

    if summary["total_count"] == 0:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No pipeline opportunities tracked.\nUse `/scout-track [company] [stage]` to start tracking.",
                    },
                }
            ],
        }

    from storage import pipeline as pipeline_store
    opps = pipeline_store.get_all_opportunities()

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📈 Pipeline Deals",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    for opp in opps:
        if opp.get("status") != "active":
            continue
        health = opp.get("health_score", 50)
        health_emoji = "🟢" if health >= 70 else "🟡" if health >= 40 else "🔴"
        stage = opp.get("stage", "—").title()
        close = opp.get("expected_close") or "—"
        champion = opp.get("champion_contact") or "—"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{opp['company_name']}*\n"
                    f"Stage: {stage} | Health: {health_emoji} *{health}/100* | "
                    f"Close: {close} | Champion: {champion}"
                ),
            },
        })

    if summary["unhealthy_count"] > 0:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *{summary['unhealthy_count']} deal(s)* below health threshold",
            },
        })

    return {"response_type": "in_channel", "blocks": blocks}


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# /scout-warm-intro
# ---------------------------------------------------------------------------

def handle_warm_intro(company_name: str) -> dict:
    """Handle /scout-warm-intro [company_name] — find warm intro paths."""
    if not company_name or not company_name.strip():
        return _error_blocks("Usage: `/scout-warm-intro [company name]`")

    company_name = company_name.strip()

    try:
        from agents.warm_intro import find_intro_paths
        result = find_intro_paths(company_name=company_name)
    except Exception as e:
        return _error_blocks(f"Failed to find intro paths: {e}")

    contacts = result.get("contacts", [])
    intro_paths = result.get("intro_paths", [])
    recommended = result.get("recommended_path")

    if not contacts:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"No contacts found for *{company_name}*.",
                    },
                }
            ],
        }

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🤝 Warm Intro Paths: {company_name}",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    # Contacts found
    contact_lines = []
    for c in contacts[:3]:
        name = c.get("name", "—")
        role = c.get("role", "—")
        email = c.get("email", "—") or "—"
        contact_lines.append(f"• *{name}* — {role} ({email})")

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Key Contacts Found:*\n" + "\n".join(contact_lines),
        },
    })
    blocks.append({"type": "divider"})

    # Intro paths
    if intro_paths:
        path_lines = []
        for p in intro_paths[:5]:
            score = p.get("score", 0)
            path_type = p.get("path_type", "general")
            reason = p.get("reason", "")[:60]
            path_lines.append(f"• `[{score}]` {path_type}: {reason}")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Warm Intro Paths:*\n" + "\n".join(path_lines),
            },
        })

    # Recommended intro request
    if recommended:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Intro Request:*\n```{recommended[:500]}```",
            },
        })

    return {"response_type": "in_channel", "blocks": blocks}


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _error_blocks(message: str) -> dict:
    """Return a standardized error message."""
    return {
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ {message}",
                },
            }
        ],
    }
