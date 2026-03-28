"""Scout Main Agent - orchestrates research and brief generation."""

import json
import os
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown

from agents.research import ResearchAgent
from prompts.brief_template import (
    SYSTEM_PROMPT,
    build_brief_prompt,
    build_rule_based_brief,
)
from storage import companies as company_store

console = Console()

PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "scout-monitor-trigger")


def _publish_to_pubsub(company_name: str, company_id: str) -> bool:
    """Publish a trigger message to Pub/Sub topic for on-demand monitoring.

    Returns True if published successfully, False otherwise.
    """
    try:
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(
            os.getenv("GCP_PROJECT", "testforcureforge"),
            PUBSUB_TOPIC,
        )
        message = json.dumps({"company_name": company_name, "company_id": company_id})
        future = publisher.publish(topic_path, message.encode("utf-8"))
        future.result(timeout=10)
        console.print(f"[dim]  Pub/Sub trigger sent for '{company_name}'[/dim]")
        return True
    except ImportError:
        console.print(
            "[yellow]Warning: google-cloud-pubsub not installed — "
            "skipping Pub/Sub trigger[/yellow]"
        )
        return False
    except Exception as e:
        console.print(f"[yellow]Pub/Sub publish failed: {e}[/yellow]")
        return False


def _get_llm_brief(company_name: str, research_data: dict) -> Optional[str]:
    """Generate a brief using an LLM via litellm.

    Returns None if no LLM key is configured.
    """
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not has_openai and not has_anthropic:
        return None

    try:
        from litellm import completion  # type: ignore

        model = "gpt-4o-mini" if has_openai else "claude-haiku-4-5-20251001"
        prompt = build_brief_prompt(company_name, research_data)

        console.print(f"[dim]  Generating brief with {model}...[/dim]")

        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except ImportError:
        console.print("[yellow]Warning: litellm not installed[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]LLM error: {e}[/red]")
        return None


class ScoutAgent:
    """Main agent that orchestrates research and brief generation."""

    def __init__(self) -> None:
        self.research_agent = ResearchAgent()

    def scout(
        self,
        company_name: str,
        domain: str = "",
        alert_email: str = "",
        add_to_monitoring: bool = True,
    ) -> str:
        """Research a company and generate a sales brief.

        Args:
            company_name: Name of the company to scout.
            domain: Optional company domain for enrichment.
            alert_email: Email for monitoring alerts.
            add_to_monitoring: Whether to add to monitoring list.

        Returns:
            Markdown brief as a string.
        """
        console.print(
            f"\n[bold blue]Scout[/bold blue] — researching [bold]{company_name}[/bold]"
        )

        # Step 1: Research
        research_data = self.research_agent.research(company_name, domain=domain)

        # Step 2: Generate brief
        console.print("\n[bold cyan]Generating brief...[/bold cyan]")
        brief = _get_llm_brief(company_name, research_data)

        if brief is None:
            console.print(
                "[yellow]No LLM API key found — using rule-based brief generation.[/yellow]\n"
                "[dim]Set OPENAI_API_KEY or ANTHROPIC_API_KEY for AI-powered briefs.[/dim]"
            )
            brief = build_rule_based_brief(company_name, research_data)

        # Step 3: Add to monitoring
        if add_to_monitoring:
            existing = company_store.get_by_name(company_name)
            if existing:
                console.print(
                    f"\n[dim]'{company_name}' is already in monitoring (id={existing['id']})[/dim]"
                )
            else:
                company = company_store.add(
                    name=company_name,
                    domain=domain,
                    alert_email=alert_email,
                )
                console.print(
                    f"\n[green]Added '{company_name}' to monitoring[/green] "
                    f"(id={company['id']})"
                )
                # Trigger on-demand monitoring via Pub/Sub
                _publish_to_pubsub(company_name, company["id"])

        return brief

    def print_brief(self, brief: str) -> None:
        """Render and print a brief to the terminal."""
        console.print("\n" + "=" * 70)
        console.print(Markdown(brief))
        console.print("=" * 70 + "\n")
