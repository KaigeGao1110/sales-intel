"""PipelineWatcher - checks tracked opportunities during monitor runs."""

from typing import Optional

from storage import pipeline as pipeline_store
from agents import pipeline as pipeline_agent


class PipelineWatcher:
    """Watches pipeline health during monitor checks and generates alerts."""

    def __init__(self) -> None:
        self.agent = pipeline_agent.PipelineIntelligenceAgent()

    def run(self, company_name: str, changes_detected: dict) -> dict:
        """Check pipeline health for a company during monitor run.

        Args:
            company_name: Name of the company.
            changes_detected: Dict of changes from MonitorAgent watchers.

        Returns:
            Dict with score, details, alert_triggered, previous_score.
        """
        opp = pipeline_store.get_opportunity(company_name)
        if not opp:
            return {
                "score": 0,
                "details": "Not a tracked opportunity",
                "alert_triggered": False,
                "previous_score": None,
            }

        # Get monitor snapshot from changes_detected (may contain research data)
        monitor_snapshot = changes_detected.get("research_data")

        # Assess current health
        result = self.agent.assess_deal_health(company_name, monitor_snapshot)
        current_score = result.get("health_score", 0)
        previous_score = opp.get("health_score", 50)

        # Update stored health score
        signals = result.get("signals", {})
        pipeline_store.update_health_score(
            company_name,
            current_score,
            signals=signals.get("danger_signals", []) + signals.get("momentum_signals", []),
        )

        # Detect score drop alert
        score_delta = current_score - previous_score
        alert_triggered = score_delta < -10  # Alert if dropped more than 10 pts

        details_parts = [f"health={current_score}"]
        if result.get("signals", {}).get("danger_signals"):
            details_parts.append(f"danger={result['signals']['danger_signals']}")
        if result.get("signals", {}).get("momentum_signals"):
            details_parts.append(f"momentum={result['signals']['momentum_signals']}")
        if alert_triggered:
            details_parts.append(f"DROP={score_delta}")

        return {
            "score": current_score,
            "details": ", ".join(details_parts),
            "alert_triggered": alert_triggered,
            "previous_score": previous_score,
            "score_delta": score_delta,
        }