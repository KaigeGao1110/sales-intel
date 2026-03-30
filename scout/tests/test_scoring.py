"""Unit tests for LeadScoringAgent."""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Patch config/icp.json path before importing scoring module
ICP_CONTENT = {
    "description": "B2B SaaS companies, Series A-C, 50-500 employees",
    "min_employees": 50,
    "max_employees": 500,
    "industries": ["software", "saas", "technology"],
    "funding_stages": ["Series A", "Series B", "Series C"],
}


@pytest.fixture
def mock_icp(tmp_path):
    """Create a temporary ICP config file."""
    icp_path = tmp_path / "icp.json"
    icp_path.write_text(json.dumps(ICP_CONTENT))
    return icp_path


class TestFundingSignal:
    """Tests for funding signal scoring (25pts max)."""

    def test_no_funding_returns_zero(self):
        from agents.scoring import _score_funding
        pts, reason = _score_funding({"funding": {}})
        assert pts == 0

    def test_recent_funding_25pts(self):
        from datetime import datetime, timezone, timedelta
        from agents.scoring import _score_funding

        recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        pts, reason = _score_funding({
            "funding": {"last_round": "Series B", "closed_date": recent_date}
        })
        assert pts == 25
        assert "Recent" in reason

    def test_old_funding_10pts(self):
        from datetime import datetime, timezone, timedelta
        from agents.scoring import _score_funding

        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        pts, reason = _score_funding({
            "funding": {"last_round": "Series A", "closed_date": old_date}
        })
        assert pts == 10
        assert "older" in reason


class TestHiringSignal:
    """Tests for hiring signal scoring (20pts max, -10 penalty)."""

    def test_hiring_signal_20pts(self):
        from agents.scoring import _score_hiring
        pts, reason = _score_hiring({"jobs_signal": {"signal": "hiring"}})
        assert pts == 20
        assert "hiring" in reason.lower()

    def test_layoffs_signal_negative_10pts(self):
        from agents.scoring import _score_hiring
        pts, reason = _score_hiring({"jobs_signal": {"signal": "layoffs"}})
        assert pts == -10
        assert "Layoffs" in reason

    def test_no_signal_returns_zero(self):
        from agents.scoring import _score_hiring
        pts, reason = _score_hiring({"jobs_signal": {}})
        assert pts == 0


class TestGradeAssignment:
    """Tests for grade assignment (A/B/C/D)."""

    def test_grade_a_at_80(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(80) == "A"

    def test_grade_a_at_100(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(100) == "A"

    def test_grade_b_at_60(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(60) == "B"

    def test_grade_b_at_79(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(79) == "B"

    def test_grade_c_at_40(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(40) == "C"

    def test_grade_c_at_59(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(59) == "C"

    def test_grade_d_below_40(self):
        from agents.scoring import _grade_from_score
        assert _grade_from_score(39) == "D"
        assert _grade_from_score(0) == "D"


class TestRecommendedAction:
    """Tests that recommended_action strings are non-empty and specific."""

    def test_action_non_empty_for_grade_a(self):
        from agents.scoring import _build_recommended_action
        action = _build_recommended_action(
            score=85, grade="A", reasons=[], research_data={}
        )
        assert len(action) > 0
        assert "reach" in action.lower() or "out" in action.lower()

    def test_action_non_empty_for_grade_d(self):
        from agents.scoring import _build_recommended_action
        action = _build_recommended_action(
            score=20, grade="D", reasons=[], research_data={}
        )
        assert len(action) > 0

    def test_action_includes_funding_signal_when_recent(self):
        from datetime import datetime, timezone, timedelta
        from agents.scoring import _build_recommended_action

        recent = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        action = _build_recommended_action(
            score=85, grade="A", reasons=[],
            research_data={"funding": {"last_round": "Series B", "closed_date": recent}}
        )
        assert "Series B" in action

    def test_action_includes_layoff_signal(self):
        from agents.scoring import _build_recommended_action
        action = _build_recommended_action(
            score=10, grade="D", reasons=[],
            research_data={"jobs_signal": {"signal": "layoffs"}}
        )
        assert "layoff" in action.lower()


class TestRankAll:
    """Tests for rank_all returns sorted list."""

    def test_rank_all_returns_sorted_descending(self):
        from agents.scoring import LeadScoringAgent

        mock_companies = [
            {"id": "1", "name": "LowCo", "domain": "", "status": "active"},
            {"id": "2", "name": "HighCo", "domain": "", "status": "active"},
            {"id": "3", "name": "MedCo", "domain": "", "status": "active"},
        ]

        def mock_get_active():
            return mock_companies

        def mock_get_latest(cid):
            if cid == "1":
                return {"news": [], "jobs": {}, "reviews": {}, "funding": {}}
            if cid == "2":
                # High score: recent funding + hiring
                from datetime import datetime, timezone, timedelta
                recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                return {
                    "news": [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}, {"e": 5}],
                    "jobs": {"signal": "hiring"},
                    "reviews": {"avg_rating": 4.5},
                    "funding": {"last_round": "Series B", "closed_date": recent},
                }
            return {"news": [], "jobs": {}, "reviews": {}, "funding": {}}

        with patch("agents.scoring.company_store.get_active", mock_get_active):
            with patch("agents.scoring.snapshot_store.get_latest", mock_get_latest):
                agent = LeadScoringAgent()
                results = agent.rank_all()

        assert len(results) == 3
        # Results should be sorted descending by score
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        # Ranks should be 1, 2, 3
        ranks = [r["priority_rank"] for r in results]
        assert ranks == [1, 2, 3]

    def test_rank_all_empty_when_no_companies(self):
        from agents.scoring import LeadScoringAgent

        def mock_get_active():
            return []

        with patch("agents.scoring.company_store.get_active", mock_get_active):
            agent = LeadScoringAgent()
            results = agent.rank_all()

        assert results == []


class TestICPMatch:
    """Tests for ICP matching scoring."""

    def test_no_icp_returns_neutral_12pts(self):
        from agents.scoring import _score_icp_match
        pts, reason = _score_icp_match({"enrichment": {}, "funding": {}}, None)
        assert pts == 12

    def test_industry_match_10pts(self):
        from agents.scoring import _score_icp_match
        icp = {"min_employees": 10, "max_employees": 1000, "industries": ["saas"], "funding_stages": []}
        pts, reason = _score_icp_match(
            {"enrichment": {"industry": "saas"}, "funding": {}}, icp
        )
        assert pts >= 10
        assert "saas" in reason.lower()

    def test_employee_count_match_10pts(self):
        from agents.scoring import _score_icp_match
        icp = {"min_employees": 50, "max_employees": 500, "industries": [], "funding_stages": []}
        pts, reason = _score_icp_match(
            {"enrichment": {"employees": 200}, "funding": {}}, icp
        )
        assert pts >= 10
        assert "200" in reason

    def test_funding_stage_match_5pts(self):
        from agents.scoring import _score_icp_match
        icp = {"min_employees": 0, "max_employees": 99999, "industries": [], "funding_stages": ["Series A", "Series B"]}
        pts, reason = _score_icp_match(
            {"enrichment": {}, "funding": {"last_round": "Series B"}}, icp
        )
        assert pts >= 5


class TestNewsSignal:
    """Tests for news activity scoring."""

    def test_5_or_more_items_15pts(self):
        from agents.scoring import _score_news
        pts, reason = _score_news({"news": [1, 2, 3, 4, 5]})
        assert pts == 15

    def test_2_to_4_items_8pts(self):
        from agents.scoring import _score_news
        pts, reason = _score_news({"news": [1, 2, 3]})
        assert pts == 8

    def test_0_to_1_items_0pts(self):
        from agents.scoring import _score_news
        pts, reason = _score_news({"news": []})
        assert pts == 0
        pts2, _ = _score_news({"news": [1]})
        assert pts2 == 0


class TestReviewsSignal:
    """Tests for review health scoring."""

    def test_high_rating_15pts(self):
        from agents.scoring import _score_reviews
        pts, reason = _score_reviews({"reviews_signal": {"avg_rating": 4.5}})
        assert pts == 15

    def test_moderate_rating_5pts(self):
        from agents.scoring import _score_reviews
        pts, reason = _score_reviews({"reviews_signal": {"avg_rating": 3.5}})
        assert pts == 5

    def test_low_rating_15pts_pain_signal(self):
        from agents.scoring import _score_reviews
        pts, reason = _score_reviews({"reviews_signal": {"avg_rating": 2.5}})
        assert pts == 15
        assert "pain" in reason.lower()

    def test_no_reviews_0pts(self):
        from agents.scoring import _score_reviews
        pts, reason = _score_reviews({"reviews_signal": {}})
        assert pts == 0
