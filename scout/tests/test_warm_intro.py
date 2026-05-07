"""Tests for Warm Intro Finder module."""

import json
import tempfile
import os
import pytest
from pathlib import Path

# Patch the intros file path before importing
_intros_file = Path(tempfile.gettempdir()) / "test_intros.json"


class TestWarmIntroStorage:
    """Tests for storage/intros.py."""

    def test_save_and_get_intro_request(self):
        """Saving and retrieving an intro request works."""
        # Patch file path
        import storage.intros as intro_store
        original_file = intro_store.INTROS_FILE
        intro_store.INTROS_FILE = _intros_file

        try:
            intro_store._save({"intros": []})

            target_contact = {"name": "Jane Smith", "email": "jane@example.com", "role": "CTO"}
            intro_paths = [
                {"path_type": "shared_previous_company", "score": 75, "reason": "Both worked at Acme", "suggested_introducer": "Bob at Acme"}
            ]

            saved = intro_store.save_intro_request("Acme Corp", target_contact, intro_paths)

            assert saved["company_name"] == "Acme Corp"
            assert saved["target_contact"]["name"] == "Jane Smith"
            assert len(saved["intro_paths"]) == 1
            assert "request_id" in saved
            assert "created_at" in saved

            retrieved = intro_store.get_intro_request("Acme Corp")
            assert retrieved is not None
            assert retrieved["company_name"] == "Acme Corp"

        finally:
            intro_store.INTROS_FILE = original_file
            if _intros_file.exists():
                _intros_file.unlink()

    def test_get_nonexistent(self):
        """Getting a nonexistent intro request returns None."""
        import storage.intros as intro_store
        original_file = intro_store.INTROS_FILE
        intro_store.INTROS_FILE = _intros_file

        try:
            intro_store._save({"intros": []})
            result = intro_store.get_intro_request("Nobody Corp")
            assert result is None
        finally:
            intro_store.INTROS_FILE = original_file

    def test_get_all_returns_list(self):
        """get_all returns a list of all requests."""
        import storage.intros as intro_store
        original_file = intro_store.INTROS_FILE
        intro_store.INTROS_FILE = _intros_file

        try:
            intro_store._save({"intros": []})
            result = intro_store.get_all()
            assert isinstance(result, list)
        finally:
            intro_store.INTROS_FILE = original_file


class TestWarmIntroAgent:
    """Tests for agents/warm_intro.py."""

    def test_path_types_defined(self):
        """All expected path types are defined."""
        from agents.warm_intro import PATH_TYPES

        expected = [
            "shared_previous_company",
            "shared_education",
            "shared_industry_group",
            "mutual_connection",
            "shared_publication",
            "conference_speaker",
            "general",
        ]
        for ptype in expected:
            assert ptype in PATH_TYPES, f"Missing path type: {ptype}"

    def test_score_intro_path(self):
        """_score_intro_path returns a score between 0-100."""
        from agents.warm_intro import _score_intro_path

        path = {"path_type": "shared_previous_company", "suggested_introducer": "Bob"}
        score = _score_intro_path(path)
        assert isinstance(score, int)
        assert 0 <= score <= 100

        # General path scores lower
        general_path = {"path_type": "general", "suggested_introducer": "Research"}
        general_score = _score_intro_path(general_path)
        assert general_score < score

    def test_find_intro_returns_structure(self):
        """find_intro_paths returns expected structure."""
        from agents.warm_intro import find_intro_paths

        result = find_intro_paths(
            company_name="Acme Corp",
            target_role="decision maker",
            domain="",
        )

        assert "company_name" in result
        assert "contacts" in result
        assert "intro_paths" in result
        assert "recommended_path" in result
        assert "created_at" in result
        assert isinstance(result["contacts"], list)
        assert isinstance(result["intro_paths"], list)

    def test_find_intro_paths_with_user_background(self):
        """find_intro_paths uses user_background for overlap detection."""
        from agents.warm_intro import find_intro_paths

        user_bg = {
            "previous_companies": ["Google", "Meta"],
            "education": ["Stanford"],
            "industry_groups": [],
        }

        result = find_intro_paths(
            company_name="Test Corp",
            target_role="CTO",
            domain="",
            user_background=user_bg,
        )

        assert "company_name" in result
        assert isinstance(result["intro_paths"], list)

    def test_print_intro_result_no_crash(self):
        """print_intro_result doesn't raise with valid data."""
        from agents.warm_intro import print_intro_result

        result = {
            "company_name": "Acme Corp",
            "contacts": [
                {"name": "Jane Smith", "role": "CTO", "email": "jane@acme.com", "source": "test"}
            ],
            "intro_paths": [
                {
                    "path_type": "shared_previous_company",
                    "score": 75,
                    "reason": "Both worked at Acme",
                    "suggested_introducer": "Bob",
                    "contact": "Jane Smith",
                }
            ],
            "recommended_path": {
                "path_type": "shared_previous_company",
                "score": 75,
                "reason": "Both worked at Acme",
                "suggested_introducer": "Bob",
            },
        }

        # Should not raise
        print_intro_result(result)
