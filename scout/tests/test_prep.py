"""Unit tests for MeetingPrepAgent and MeetingPrepStorage."""

import json
import os
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch


class TestMeetingPrep:
    """Tests for MeetingPrepAgent and MeetingPrepStorage."""

    def test_generate_prep_returns_structure(self, tmp_path):
        """Test that generate_prep returns a dict with all required keys."""
        from agents import prep as prep_module
        from agents.prep import MeetingPrepAgent

        # Mock company store and web search
        mock_company_data = {
            "id": "123",
            "name": "TestCorp",
            "domain": "testcorp.com",
            "status": "active",
        }

        def mock_get_by_name(name):
            return mock_company_data

        with patch.object(prep_module, "_web_search", return_value="Test person background info"):
            with patch.object(prep_module, "_build_prep_content") as mock_build:
                mock_build.return_value = {
                    "context": "Test meeting context",
                    "pain_points": ["pain1", "pain2"],
                    "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
                    "topics_to_avoid": ["topic1"],
                    "key_facts": ["fact1", "fact2", "fact3"],
                }
                with patch("storage.meeting_prep.store"):
                    agent = MeetingPrepAgent(
                        company_store=type("obj", (object,), {"get_by_name": mock_get_by_name})()
                    )
                    result = agent.generate_prep(
                        company_name="TestCorp",
                        attendee_emails=["john@testcorp.com", "jane@testcorp.com"],
                        meeting_time="2026-04-01T10:00:00Z",
                    )

        assert "meeting_id" in result
        assert "company_name" in result
        assert result["company_name"] == "TestCorp"
        assert "attendees" in result
        assert result["attendees"] == ["john@testcorp.com", "jane@testcorp.com"]
        assert "prep_content" in result
        assert "meeting_time" in result
        assert result["meeting_time"] == "2026-04-01T10:00:00Z"
        assert "created_at" in result
        assert "status" in result
        assert result["status"] == "scheduled"

        prep = result["prep_content"]
        assert "context" in prep
        assert "pain_points" in prep
        assert "questions" in prep
        assert "topics_to_avoid" in prep
        assert "key_facts" in prep
        assert len(prep["questions"]) == 5

    def test_storage_store_and_get(self, tmp_path):
        """Test store and get roundtrip."""
        from storage import meeting_prep as meeting_prep_store

        # Patch data file path
        data_file = tmp_path / "meeting_preps.json"
        with patch.object(meeting_prep_store, "DATA_FILE", data_file):
            meeting_prep_store._save({"meeting_preps": []})

            prep_data = {
                "meeting_id": "test-meeting-123",
                "company_name": "Acme Corp",
                "attendees": ["john@acme.com"],
                "prep_content": {"context": "Test context"},
                "meeting_time": "2026-04-01T10:00:00Z",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            }

            meeting_prep_store.store("test-meeting-123", prep_data)
            retrieved = meeting_prep_store.get("test-meeting-123")

        assert retrieved is not None
        assert retrieved["meeting_id"] == "test-meeting-123"
        assert retrieved["company_name"] == "Acme Corp"

    def test_get_by_company(self, tmp_path):
        """Test storing multiple preps and querying by company name."""
        from storage import meeting_prep as meeting_prep_store

        data_file = tmp_path / "meeting_preps.json"
        with patch.object(meeting_prep_store, "DATA_FILE", data_file):
            meeting_prep_store._save({"meeting_preps": []})

            # Store two companies
            prep1 = {
                "meeting_id": "m1",
                "company_name": "Acme Corp",
                "attendees": ["a@acme.com"],
                "prep_content": {},
                "meeting_time": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            }
            prep2 = {
                "meeting_id": "m2",
                "company_name": "Beta Inc",
                "attendees": ["b@beta.com"],
                "prep_content": {},
                "meeting_time": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            }
            prep3 = {
                "meeting_id": "m3",
                "company_name": "Acme Corp",
                "attendees": ["c@acme.com"],
                "prep_content": {},
                "meeting_time": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            }

            meeting_prep_store.store("m1", prep1)
            meeting_prep_store.store("m2", prep2)
            meeting_prep_store.store("m3", prep3)

            acme_results = meeting_prep_store.get_by_company("Acme Corp")
            beta_results = meeting_prep_store.get_by_company("beta inc")

        assert len(acme_results) == 2
        assert all(m["company_name"] == "Acme Corp" for m in acme_results)
        assert len(beta_results) == 1
        assert beta_results[0]["company_name"] == "Beta Inc"

    def test_mark_complete(self, tmp_path):
        """Test storing a prep, marking it complete, and verifying status."""
        from storage import meeting_prep as meeting_prep_store

        data_file = tmp_path / "meeting_preps.json"
        with patch.object(meeting_prep_store, "DATA_FILE", data_file):
            meeting_prep_store._save({"meeting_preps": []})

            prep_data = {
                "meeting_id": "complete-test",
                "company_name": "TestCo",
                "attendees": ["t@testco.com"],
                "prep_content": {},
                "meeting_time": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            }

            meeting_prep_store.store("complete-test", prep_data)
            result = meeting_prep_store.mark_complete("complete-test")

            assert result is True
            retrieved = meeting_prep_store.get("complete-test")
            assert retrieved["status"] == "completed"

    def test_get_upcoming(self, tmp_path):
        """Test get_upcoming returns meetings within the specified time window."""
        from storage import meeting_prep as meeting_prep_store

        data_file = tmp_path / "meeting_preps.json"
        with patch.object(meeting_prep_store, "DATA_FILE", data_file):
            meeting_prep_store._save({"meeting_preps": []})

            now = datetime.now(timezone.utc)
            # Meeting in 2 hours (within 24h window)
            soon = (now + timedelta(hours=2)).isoformat()
            # Meeting in 3 days (outside 24h window)
            later = (now + timedelta(days=3)).isoformat()
            # Meeting in past
            past = (now - timedelta(hours=1)).isoformat()

            preps = [
                {
                    "meeting_id": "upcoming-1",
                    "company_name": "SoonCorp",
                    "attendees": [],
                    "prep_content": {},
                    "meeting_time": soon,
                    "created_at": now.isoformat(),
                    "status": "scheduled",
                },
                {
                    "meeting_id": "upcoming-2",
                    "company_name": "LaterCorp",
                    "attendees": [],
                    "prep_content": {},
                    "meeting_time": later,
                    "created_at": now.isoformat(),
                    "status": "scheduled",
                },
                {
                    "meeting_id": "past-meeting",
                    "company_name": "PastCorp",
                    "attendees": [],
                    "prep_content": {},
                    "meeting_time": past,
                    "created_at": now.isoformat(),
                    "status": "scheduled",
                },
            ]

            for p in preps:
                meeting_prep_store.store(p["meeting_id"], p)

            upcoming = meeting_prep_store.get_upcoming(hours_ahead=24)

        assert len(upcoming) == 1
        assert upcoming[0]["company_name"] == "SoonCorp"
