"""FastAPI REST API for Scout sales intelligence.

Run locally:
    uvicorn scout.api:app --reload --port 8080

Deploy to Cloud Run:
    gcloud run deploy scout-api --source . --region us-central1
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scout.storage import companies as company_store
from scout.storage import alerts as alert_store
from scout.storage import scores as score_store
from scout.storage import snapshots
from scout.agents.scout import ScoutAgent
from scout.agents.monitor import MonitorAgent
from scout.agents.scoring import LeadScoringAgent
from scout.agents.research import ResearchAgent
from scout.agents.outreach import OutreachAgent
from scout.agents.alert import _lookup_contacts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CompanyCreate(BaseModel):
    name: str
    domain: str = ""
    alert_email: str = ""
    alert_channels: Optional[list[str]] = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: str
    added_date: Optional[str]
    last_checked: Optional[str]
    status: str
    alert_channels: list[str]
    alert_email: str


class AlertResponse(BaseModel):
    id: str
    company_id: str
    company_name: str
    alert_date: str
    type: str
    severity: str
    title: str
    summary: str
    score: int
    notified: bool
    notification_date: Optional[str]
    channels: list[str]


class ResearchResponse(BaseModel):
    company_id: str
    company_name: str
    status: str
    message: str


class ScoreResponse(BaseModel):
    company_id: str
    company_name: str
    score: int
    grade: str
    reasons: list[str]
    recommended_action: str


class RankEntry(BaseModel):
    priority_rank: int
    company_id: str
    company_name: str
    score: int
    grade: str
    recommended_action: str


class OutreachResponse(BaseModel):
    company_name: str
    angle: str
    cold_emails: list[str]
    linkedin_messages: list[str]
    subject_lines: list[list[str]]


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Scout API starting up...")
    yield
    logger.info("Scout API shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Scout API",
    description="Sales intelligence API for company monitoring and research",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Companies endpoints
# ---------------------------------------------------------------------------

@app.get("/companies", response_model=list[CompanyResponse])
def list_companies():
    """List all monitored companies."""
    try:
        companies = company_store.get_all()
        return [CompanyResponse(**c) for c in companies]
    except Exception:
        logger.exception("Failed to list companies")
        return []


@app.post("/companies", response_model=CompanyResponse, status_code=201)
def add_company(company: CompanyCreate):
    """Add a new company to monitoring."""
    try:
        existing = company_store.get_by_name(company.name)
        if existing:
            return CompanyResponse(**existing)

        channels = company.alert_channels or (["email"] if company.alert_email else ["console"])
        created = company_store.add(
            name=company.name,
            domain=company.domain,
            alert_email=company.alert_email,
            alert_channels=channels,
        )
        return CompanyResponse(**created)
    except Exception:
        logger.exception("Failed to add company")
        raise HTTPException(status_code=500, detail="Failed to add company")


@app.delete("/companies/{company_id}", status_code=204)
def delete_company(company_id: str):
    """Remove a company from monitoring."""
    try:
        existing = company_store.get_by_id(company_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Company not found")

        removed = company_store.remove(company_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Company not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete company")
        raise HTTPException(status_code=500, detail="Failed to delete company")


# ---------------------------------------------------------------------------
# Research endpoint
# ---------------------------------------------------------------------------

def _run_research(company_id: str, company_name: str, domain: str) -> dict:
    """Background task to run research for a company."""
    try:
        agent = ScoutAgent()
        brief = agent.scout(
            company_name=company_name,
            domain=domain,
            add_to_monitoring=False,
        )
        # Update last checked
        company_store.update_last_checked(company_id)
        return {"status": "success", "company_name": company_name}
    except Exception:
        logger.exception(f"Research failed for {company_name}")
        return {"status": "error", "company_name": company_name}


@app.post("/companies/{company_id}/research", response_model=ResearchResponse)
def trigger_research(company_id: str, background_tasks: BackgroundTasks):
    """Trigger on-demand research brief for a company."""
    try:
        company = company_store.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Run research in background to avoid timeout
        background_tasks.add_task(
            _run_research,
            company_id,
            company["name"],
            company.get("domain", ""),
        )

        return ResearchResponse(
            company_id=company_id,
            company_name=company["name"],
            status="started",
            message="Research task queued",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to trigger research")
        raise HTTPException(status_code=500, detail="Failed to trigger research")


# ---------------------------------------------------------------------------
# Alerts endpoint
# ---------------------------------------------------------------------------

@app.get("/companies/{company_id}/alerts", response_model=list[AlertResponse])
def get_company_alerts(company_id: str):
    """Get alerts for a specific company."""
    try:
        company = company_store.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        all_alerts = alert_store.get_all()
        company_alerts = [
            AlertResponse(**a)
            for a in all_alerts
            if a.get("company_id") == company_id
        ]
        return company_alerts
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get alerts")
        return []


# ---------------------------------------------------------------------------
# Scoring endpoints
# ---------------------------------------------------------------------------

@app.get("/score/{company_name}", response_model=ScoreResponse)
def get_company_score(company_name: str):
    """Get the latest score for a company."""
    company = company_store.get_by_name(company_name)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    score_data = score_store.get_latest(company["id"])
    if not score_data:
        raise HTTPException(status_code=404, detail="No score found for this company")

    return ScoreResponse(
        company_id=company["id"],
        company_name=company_name,
        score=score_data["score"],
        grade=score_data["grade"],
        reasons=score_data["reasons"],
        recommended_action=score_data["recommended_action"],
    )


@app.get("/rank", response_model=list[RankEntry])
def get_rank():
    """Get ranked list of all active companies."""
    try:
        scorer = LeadScoringAgent()
        results = scorer.rank_all()
        return [
            RankEntry(
                priority_rank=r["priority_rank"],
                company_id=r.get("company_id", ""),
                company_name=r["company_name"],
                score=r["score"],
                grade=r["grade"],
                recommended_action=r["recommended_action"],
            )
            for r in results
        ]
    except Exception:
        logger.exception("Failed to rank companies")
        return []


# ---------------------------------------------------------------------------
# Outreach endpoint
# ---------------------------------------------------------------------------

def _detect_angle_for_api(research_data: dict) -> str:
    """Detect angle from research data for API response."""
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


@app.post("/outreach/{company_name}", response_model=OutreachResponse)
def generate_outreach(company_name: str, background_tasks: BackgroundTasks):
    """Generate personalized outreach for a company.

    Runs research if not cached, looks up contacts, generates outreach, and logs it.
    """
    # Check if company is monitored
    company = company_store.get_by_name(company_name)
    domain = ""

    if company:
        domain = company.get("domain", "")

    # Try to load from snapshot first
    research_data = None
    if company:
        snapshot = snapshots.get_latest(company["id"])
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

    # If no snapshot, run fresh research in background
    if not research_data:
        try:
            agent = ResearchAgent()
            research_data = agent.research(company_name, domain=domain)
        except Exception:
            logger.exception(f"Research failed for {company_name}")
            raise HTTPException(status_code=500, detail="Research failed")

    # Look up contacts
    contacts = _lookup_contacts(company_name, domain=domain)

    # Generate outreach
    try:
        outreach_agent = OutreachAgent()
        result = outreach_agent.generate(
            company_name=company_name,
            brief="",
            research_data=research_data,
            contacts=contacts,
            variants=2,
        )
    except Exception:
        logger.exception(f"Outreach generation failed for {company_name}")
        raise HTTPException(status_code=500, detail="Outreach generation failed")

    # Log asynchronously
    def _log_outreach():
        try:
            from scout.storage import outreach as outreach_store
            company_id = company["id"] if company else "unknown"
            outreach_store.log(
                company_id=company_id,
                company_name=company_name,
                contacts=contacts,
                variants=result,
            )
        except Exception:
            logger.exception("Failed to log outreach")

    background_tasks.add_task(_log_outreach)

    return OutreachResponse(
        company_name=company_name,
        angle=_detect_angle_for_api(research_data),
        cold_emails=result.get("cold_emails", []),
        linkedin_messages=result.get("linkedin_messages", []),
        subject_lines=result.get("subject_lines", []),
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
