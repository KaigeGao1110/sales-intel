"""Tests for calendar integration."""

from unittest.mock import patch, MagicMock
from integrations.calendar import extract_company_name, get_upcoming_events


class TestExtractCompanyName:
    """Tests for company name extraction from calendar events."""

    def test_meeting_with_pattern(self):
        event = {"title": "Meeting with Acme Corp", "attendees": []}
        assert extract_company_name(event) == "Acme Corp"

    def test_intro_pattern(self):
        event = {"title": "Acme - Intro Call", "attendees": []}
        assert extract_company_name(event) == "Acme"

    def test_demo_pattern(self):
        event = {"title": "Demo with Stripe", "attendees": []}
        assert extract_company_name(event) == "Stripe"

    def test_domain_fallback(self):
        event = {
            "title": "Follow-up",
            "attendees": [{"email": "john@staging-company.com"}],
        }
        result = extract_company_name(event)
        assert result == "Staging-Company"

    def test_skips_generic_domains(self):
        event = {
            "title": "Chat",
            "attendees": [{"email": "friend@gmail.com"}],
        }
        assert extract_company_name(event) is None

    def test_multiple_attendees_picks_company(self):
        event = {
            "title": "Call",
            "attendees": [
                {"email": "me@gmail.com"},
                {"email": "buyer@enterprise-co.io"},
            ],
        }
        result = extract_company_name(event)
        assert result == "Enterprise-Co"

    def test_no_company_found(self):
        event = {"title": "Lunch", "attendees": []}
        assert extract_company_name(event) is None


class TestGetUpcomingEvents:
    """Tests for calendar event fetching."""

    @patch("integrations.calendar._run_gog")
    def test_returns_empty_on_gog_failure(self, mock_gog):
        mock_gog.return_value = None
        events = get_upcoming_events(24)
        assert events == []

    @patch("integrations.calendar._run_gog")
    def test_parses_events(self, mock_gog):
        mock_gog.return_value = """[
            {
                "id": "evt1",
                "summary": "Meeting with Acme",
                "start": {"dateTime": "2026-04-01T14:00:00Z"},
                "end": {"dateTime": "2026-04-01T14:30:00Z"},
                "attendees": [{"email": "john@acme.com"}],
                "description": "Intro call"
            }
        ]"""
        events = get_upcoming_events(24)
        assert len(events) == 1
        assert events[0]["title"] == "Meeting with Acme"
        assert events[0]["event_id"] == "evt1"
        assert len(events[0]["attendees"]) == 1
