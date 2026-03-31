"""Pipeline Intelligence Agent - assesses deal health and pipeline signals."""

from typing import Optional

from storage import pipeline as pipeline_store

HEALTH_SCORING = {
    "discovery": 5,
    "qualification": 10,
    "proposal": 10,
    "negotiation": 15,
    "poc": 20,
    "closed_won": 20,
    "closed_lost": 0,
}

DANGER_SIGNALS = [
    "layoffs",
    "firing",
    "budget cut",
    "hiring freeze",
    "pivot",
    "restructuring",
    "executive departure",
]

MOMENTUM_SIGNALS = [
    "expanding",
    "growing",
    "hiring",
    " Series ",
    "funded",
    "launching",
    "partnering",
    "upscaling",
]


def detect_signals(monitor_snapshot: Optional[dict]) -> dict:
    """Parse a monitor snapshot for danger and momentum signals.

    Args:
        monitor_snapshot: Dict with keys like news, jobs, funding, etc.

    Returns:
        Dict with danger_signals[], momentum_signals[], raw data.
    """
    if monitor_snapshot is None:
        return {"danger_signals": [], "momentum_signals": [], "raw": {}}

    danger: list[str] = []
    momentum: list[str] = []
    raw = monitor_snapshot

    # Check news for danger/momentum keywords
    news_items = raw.get("news", [])
    news_text = " ".join(
        str(n.get("title", "")) + " " + str(n.get("summary", ""))
        for n in news_items
    ).lower()

    for signal in DANGER_SIGNALS:
        if signal.lower() in news_text:
            danger.append(signal)

    for signal in MOMENTUM_SIGNALS:
        if signal.lower() in news_text:
            momentum.append(signal)

    # Check jobs for layoffs
    jobs = raw.get("jobs", {})
    if jobs.get("signal") == "layoffs":
        danger.append("layoffs (jobs signal)")

    # Check for funding news (momentum)
    funding = raw.get("funding", {})
    if funding.get("last_round"):
        momentum.append(f"funded: {funding.get('last_round')}")

    return {
        "danger_signals": list(set(danger)),
        "momentum_signals": list(set(momentum)),
        "raw": raw,
    }


def assess_deal_health(
    company_name: str,
    monitor_snapshot: Optional[dict] = None,
) -> dict:
    """Assess the health score for a tracked opportunity.

    Health score (100 pts max):
    - stage (20 pts): based on HEALTH_SCORING dict
    - champion_stability (20 pts): full if champion_contact exists
    - no_danger_signals (40 pts): -5 per danger signal, min 0
    - momentum (20 pts): +10 if momentum signals present

    Args:
        company_name: Name of the company.
        monitor_snapshot: Optional snapshot data for signal detection.

    Returns:
        Dict with company_name, health_score, breakdown, signals, stage.
    """
    opp = pipeline_store.get_opportunity(company_name)
    if not opp:
        return {
            "company_name": company_name,
            "health_score": 0,
            "breakdown": {"error": "Opportunity not found"},
            "signals": {"danger_signals": [], "momentum_signals": []},
            "stage": None,
        }

    # Stage score
    stage = opp.get("stage", "discovery")
    stage_pts = HEALTH_SCORING.get(stage, 5)
    stage_score = int((stage_pts / 20) * 20)  # normalize to 20pts max

    # Champion stability (20 pts)
    champion_pts = 20 if opp.get("champion_contact") else 0

    # Signal detection
    signals = detect_signals(monitor_snapshot)
    danger_signals = signals.get("danger_signals", [])
    momentum_signals = signals.get("momentum_signals", [])

    # No danger signals (40 pts max, -5 per signal)
    danger_penalty = min(40, len(danger_signals) * 5)
    no_danger_score = max(0, 40 - danger_penalty)

    # Momentum (20 pts)
    momentum_pts = 20 if momentum_signals else 0

    total = stage_score + champion_pts + no_danger_score + momentum_pts
    total = min(100, total)

    breakdown = {
        "stage": stage_score,
        "champion_stability": champion_pts,
        "no_danger_signals": no_danger_score,
        "momentum": momentum_pts,
    }

    return {
        "company_name": company_name,
        "health_score": total,
        "breakdown": breakdown,
        "signals": signals,
        "stage": stage,
    }


def get_unhealthy_deals(threshold: int = 50) -> list[dict]:
    """Get all tracked opportunities with health below threshold.

    Args:
        threshold: Health score threshold (default 50).

    Returns:
        List of unhealthy opportunity dicts.
    """
    return pipeline_store.get_unhealthy(threshold)


def get_pipeline_summary() -> dict:
    """Get a summary of the entire pipeline.

    Returns:
        Dict with total_count, by_stage, avg_health, unhealthy_count.
    """
    opps = pipeline_store.get_all_opportunities()
    if not opps:
        return {
            "total_count": 0,
            "by_stage": {},
            "avg_health": 0,
            "unhealthy_count": 0,
        }

    by_stage: dict[str, int] = {}
    total_health = 0
    unhealthy = 0

    for opp in opps:
        if opp.get("status") != "active":
            continue
        stage = opp.get("stage", "unknown")
        by_stage[stage] = by_stage.get(stage, 0) + 1
        total_health += opp.get("health_score", 0)
        if opp.get("health_score", 0) < 50:
            unhealthy += 1

    active_count = sum(1 for o in opps if o.get("status") == "active")
    avg_health = total_health / active_count if active_count > 0 else 0

    return {
        "total_count": len(opps),
        "by_stage": by_stage,
        "avg_health": round(avg_health, 1),
        "unhealthy_count": unhealthy,
    }


class PipelineIntelligenceAgent:
    """Agent for pipeline health assessment and deal intelligence."""

    def __init__(self) -> None:
        pass

    def assess_deal_health(
        self,
        company_name: str,
        monitor_snapshot: Optional[dict] = None,
    ) -> dict:
        """Assess health of a specific deal."""
        return assess_deal_health(company_name, monitor_snapshot)

    def get_unhealthy_deals(self, threshold: int = 50) -> list[dict]:
        """Get unhealthy deals below score threshold."""
        return get_unhealthy_deals(threshold)

    def get_pipeline_summary(self) -> dict:
        """Get pipeline summary statistics."""
        return get_pipeline_summary()

    def detect_signals(
        self,
        monitor_snapshot: Optional[dict] = None,
    ) -> dict:
        """Detect danger and momentum signals from a monitor snapshot."""
        return detect_signals(monitor_snapshot)