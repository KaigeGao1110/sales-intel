"""Tests for OutreachAgent and angle detection."""

import os
import pytest
from unittest.mock import patch

# Ensure no LLM calls in tests
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)


class TestAngleDetection:
    """Test angle detection logic."""

    def test_hiring_signal_returns_growth_angle(self):
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {"last_round": None},
            "reviews_signal": {},
        }
        assert _detect_angle(research) == "growth_scaling"

    def test_funding_signal_returns_capital_angle(self):
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "unknown"},
            "funding": {"last_round": "Series B"},
            "reviews_signal": {},
        }
        assert _detect_angle(research) == "new_capital"

    def test_layoffs_signal_returns_efficiency_angle(self):
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "layoffs"},
            "funding": {"last_round": None},
            "reviews_signal": {},
        }
        assert _detect_angle(research) == "efficiency"

    def test_low_rating_returns_morale_angle(self):
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "unknown"},
            "funding": {"last_round": None},
            "reviews_signal": {"avg_rating": 3.2},
        }
        assert _detect_angle(research) == "team_morale"

    def test_default_angle_when_no_signals(self):
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "unknown"},
            "funding": {"last_round": None},
            "reviews_signal": {"avg_rating": 4.0},
        }
        assert _detect_angle(research) == "general_value"

    def test_hiring_takes_priority_over_funding(self):
        """If both hiring and funding signals present, hiring wins."""
        from agents.outreach import _detect_angle

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {"last_round": "Series B"},
            "reviews_signal": {},
        }
        assert _detect_angle(research) == "growth_scaling"


class TestRuleBasedEmailGeneration:
    """Test rule-based email and LinkedIn generation."""

    def _minimal_research(self, angle: str) -> dict:
        """Return minimal research data for a given angle."""
        base = {
            "news": [],
            "jobs_signal": {"signal": "unknown", "total_postings": 0},
            "funding": {"last_round": None, "amount": None},
            "reviews_signal": {"avg_rating": None},
            "enrichment": {"industry": "software"},
        }
        if angle == "growth_scaling":
            base["jobs_signal"] = {"signal": "hiring", "total_postings": 47}
        elif angle == "new_capital":
            base["funding"] = {"last_round": "Series A", "amount": "$12M"}
        elif angle == "efficiency":
            base["jobs_signal"] = {"signal": "layoffs"}
        elif angle == "team_morale":
            base["reviews_signal"] = {"avg_rating": 2.8}
        return base

    def test_rule_email_has_content_for_hiring_angle(self):
        from agents.outreach import _build_rule_email

        research = self._minimal_research("growth_scaling")
        subjects, body = _build_rule_email("Acme Corp", "growth_scaling", research, {}, 0)
        assert len(body) > 20
        assert "Acme Corp" in body
        assert len(subjects) == 3

    def test_rule_email_has_content_for_funding_angle(self):
        from agents.outreach import _build_rule_email

        research = self._minimal_research("new_capital")
        subjects, body = _build_rule_email("Acme Corp", "new_capital", research, {}, 0)
        assert len(body) > 20
        assert "Acme Corp" in body

    def test_rule_linkedin_has_content(self):
        from agents.outreach import _build_rule_linkedin

        research = self._minimal_research("growth_scaling")
        msg = _build_rule_linkedin("Acme Corp", "growth_scaling", research, {}, 0)
        assert len(msg) > 10
        assert "Acme Corp" in msg

    def test_personalization_with_contact(self):
        from agents.outreach import _build_rule_email, _build_rule_linkedin

        research = self._minimal_research("growth_scaling")
        contact = {"first_name": "Sarah", "last_name": "Chen", "position": "VP Engineering"}

        subjects, body = _build_rule_email("Acme Corp", "growth_scaling", research, contact, 0)
        assert "Sarah" in body

        msg = _build_rule_linkedin("Acme Corp", "growth_scaling", research, contact, 0)
        assert "Sarah" in msg


class TestOutreachAgentGenerate:
    """Test OutreachAgent.generate() output shape and content."""

    def test_generate_returns_dict_with_correct_keys(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "hiring", "total_postings": 10},
            "funding": {"last_round": "Seed", "amount": "$2M"},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=[],
            variants=2,
        )

        assert isinstance(result, dict)
        assert "cold_emails" in result
        assert "linkedin_messages" in result
        assert "subject_lines" in result

    def test_generate_returns_correct_variant_count(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=[],
            variants=3,
        )

        assert len(result["cold_emails"]) == 3
        assert len(result["linkedin_messages"]) == 3
        assert len(result["subject_lines"]) == 3

    def test_generate_without_contacts_still_produces_output(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "unknown"},
            "funding": {},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=[],
            variants=2,
        )

        assert len(result["cold_emails"]) == 2
        assert all(len(email) > 0 for email in result["cold_emails"])
        assert all(len(msg) > 0 for msg in result["linkedin_messages"])

    def test_generate_with_contacts_personalizes_per_contact(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        contacts = [
            {"first_name": "Alice", "last_name": "Manager", "position": "CEO"},
            {"first_name": "Bob", "last_name": "Engineer", "position": "CTO"},
        ]

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=contacts,
            variants=2,
        )

        # Both contacts' names should appear in the emails
        emails_text = " ".join(result["cold_emails"])
        assert "Alice" in emails_text
        assert "Bob" in emails_text

    def test_generate_email_approximately_correct_length(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=[],
            variants=2,
        )

        # Each email should be roughly 150 words for LLM, 50+ for rule-based fallback
        for email in result["cold_emails"]:
            word_count = len(email.split())
            assert 50 < word_count < 250, f"Email word count {word_count} outside expected range"

    def test_generate_linkedin_under_100_words(self):
        from agents.outreach import OutreachAgent

        research = {
            "jobs_signal": {"signal": "hiring"},
            "funding": {},
            "reviews_signal": {},
            "news": [],
            "enrichment": {},
        }

        agent = OutreachAgent()
        result = agent.generate(
            company_name="TestCo",
            brief="",
            research_data=research,
            contacts=[],
            variants=2,
        )

        for msg in result["linkedin_messages"]:
            word_count = len(msg.split())
            assert word_count <= 100, f"LinkedIn message word count {word_count} exceeds 100"


class TestStorageOutreach:
    """Test outreach storage functions."""

    def test_log_creates_record(self, tmp_path, monkeypatch):
        # Patch OUTREACH_FILE to tmp_path
        from storage import outreach as outreach_store

        test_file = tmp_path / "outreach.json"
        monkeypatch.setattr(outreach_store, "OUTREACH_FILE", test_file)

        record = outreach_store.log(
            company_id="test-123",
            company_name="Acme Corp",
            contacts=[{"first_name": "John", "last_name": "Doe", "position": "CEO", "email": "j@acme.com"}],
            variants={
                "cold_emails": ["Hello Acme"],
                "linkedin_messages": ["Hi John"],
                "subject_lines": [["Subject 1", "Subject 2"]],
            },
        )

        assert record["company_id"] == "test-123"
        assert record["company_name"] == "Acme Corp"
        assert record["cold_emails"] == ["Hello Acme"]
        assert "id" in record

    def test_get_by_company_filters_correctly(self, tmp_path, monkeypatch):
        from storage import outreach as outreach_store

        test_file = tmp_path / "outreach.json"
        monkeypatch.setattr(outreach_store, "OUTREACH_FILE", test_file)

        outreach_store.log(
            company_id="test-456",
            company_name="Beta Inc",
            contacts=[],
            variants={"cold_emails": [], "linkedin_messages": [], "subject_lines": []},
        )
        outreach_store.log(
            company_id="test-123",
            company_name="Acme Corp",
            contacts=[],
            variants={"cold_emails": ["Hello"], "linkedin_messages": [], "subject_lines": []},
        )

        acme_records = outreach_store.get_by_company("test-123")
        assert len(acme_records) == 1
        assert acme_records[0]["company_name"] == "Acme Corp"

    def test_get_all_returns_all_records(self, tmp_path, monkeypatch):
        from storage import outreach as outreach_store

        test_file = tmp_path / "outreach.json"
        monkeypatch.setattr(outreach_store, "OUTREACH_FILE", test_file)

        outreach_store.log("c1", "Co1", [], {"cold_emails": [], "linkedin_messages": [], "subject_lines": []})
        outreach_store.log("c2", "Co2", [], {"cold_emails": [], "linkedin_messages": [], "subject_lines": []})

        all_records = outreach_store.get_all()
        assert len(all_records) == 2
