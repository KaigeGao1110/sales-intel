"""Unit tests for Pipeline storage and intelligence modules."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ---- PipelineStorage tests ----

class TestPipelineStorage:
    """Tests for PipelineStorage functions."""

    def test_track_and_get(self):
        from storage import pipeline as pipeline_store

        # Use a list-backed store so mock_save can replace contents
        _store = [{"opportunities": []}]

        def mock_load():
            return _store[0]

        def mock_save(data):
            _store[0] = data

        with patch.object(pipeline_store, "_load", mock_load):
            with patch.object(pipeline_store, "_save", mock_save):
                opp = pipeline_store.track_opportunity(
                    "TestCo",
                    stage="discovery",
                    expected_close="2025-06-01",
                    champion_contact="john@testco.com",
                )

                assert opp["company_name"] == "TestCo"
                assert opp["stage"] == "discovery"
                assert opp["health_score"] == 50
                assert opp["status"] == "active"
                assert opp["opportunity_id"] is not None

                # get_opportunity within same mock context
                found = pipeline_store.get_opportunity("TestCo")
                assert found is not None
                assert found["company_name"] == "TestCo"

    def test_untrack(self):
        from storage import pipeline as pipeline_store

        _store = [{
            "opportunities": [
                {"opportunity_id": "123", "company_name": "TestCo", "stage": "discovery",
                 "health_score": 50, "signals": [], "last_assessed": None,
                 "created_at": datetime.now(timezone.utc).isoformat(), "status": "active"}
            ]
        }]

        def mock_load():
            return _store[0]

        def mock_save(data):
            _store[0] = data

        with patch.object(pipeline_store, "_load", mock_load):
            with patch.object(pipeline_store, "_save", mock_save):
                result = pipeline_store.untrack("TestCo")
                assert result is True
                assert len(_store[0]["opportunities"]) == 0

        # Untrack non-existent returns False
        with patch.object(pipeline_store, "_load", mock_load):
            result = pipeline_store.untrack("NonExistent")
            assert result is False

    def test_update_health_score(self):
        from storage import pipeline as pipeline_store

        _store = [{
            "opportunities": [
                {"opportunity_id": "123", "company_name": "TestCo", "stage": "proposal",
                 "health_score": 50, "signals": [], "last_assessed": None,
                 "created_at": datetime.now(timezone.utc).isoformat(), "status": "active"}
            ]
        }]

        def mock_load():
            return _store[0]

        def mock_save(data):
            _store[0] = data

        with patch.object(pipeline_store, "_load", mock_load):
            with patch.object(pipeline_store, "_save", mock_save):
                opp = pipeline_store.update_health_score(
                    "TestCo", 75, signals=["hiring", "expanding"]
                )
                assert opp is not None
                assert opp["health_score"] == 75
                assert "hiring" in opp["signals"]
                assert opp["last_assessed"] is not None

    def test_get_unhealthy(self):
        from storage import pipeline as pipeline_store

        _store = [{
            "opportunities": [
                {"opportunity_id": "1", "company_name": "HealthyCo", "stage": "poc",
                 "health_score": 80, "signals": [], "last_assessed": None,
                 "created_at": datetime.now(timezone.utc).isoformat(), "status": "active"},
                {"opportunity_id": "2", "company_name": "UnhealthyCo", "stage": "discovery",
                 "health_score": 30, "signals": ["layoffs"], "last_assessed": None,
                 "created_at": datetime.now(timezone.utc).isoformat(), "status": "active"},
            ]
        }]

        with patch.object(pipeline_store, "_load", lambda: _store[0]):
            unhealthy = pipeline_store.get_unhealthy(threshold=50)
            assert len(unhealthy) == 1
            assert unhealthy[0]["company_name"] == "UnhealthyCo"


# ---- PipelineAgent tests ----

class TestPipelineAgent:
    """Tests for PipelineIntelligenceAgent."""

    def test_health_scoring_stage(self):
        from agents.pipeline import HEALTH_SCORING, assess_deal_health

        assert HEALTH_SCORING["discovery"] == 5
        assert HEALTH_SCORING["poc"] == 20
        assert HEALTH_SCORING["closed_won"] == 20
        assert HEALTH_SCORING["closed_lost"] == 0

        mock_opp = {
            "company_name": "TestCo",
            "stage": "discovery",
            "champion_contact": None,
            "health_score": 50,
            "signals": [],
            "last_assessed": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        with patch("agents.pipeline.pipeline_store.get_opportunity", return_value=mock_opp):
            result = assess_deal_health("TestCo", monitor_snapshot=None)
            assert result["health_score"] > 0
            assert result["breakdown"]["stage"] < 20  # discovery = low stage score

    def test_assess_deal_returns_structure(self):
        from agents.pipeline import PipelineIntelligenceAgent

        mock_opp = {
            "company_name": "TestCo",
            "stage": "proposal",
            "champion_contact": "champion@testco.com",
            "health_score": 50,
            "signals": [],
            "last_assessed": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        with patch("agents.pipeline.pipeline_store.get_opportunity", return_value=mock_opp):
            agent = PipelineIntelligenceAgent()
            result = agent.assess_deal_health("TestCo")

            assert "company_name" in result
            assert "health_score" in result
            assert "breakdown" in result
            assert "signals" in result
            assert "stage" in result
            assert result["company_name"] == "TestCo"

    def test_detect_signals(self):
        from agents.pipeline import detect_signals

        snapshot = {
            "news": [
                {"title": "Company laying off 10% of workforce - layoffs announced"},
                {"title": "Company raising Series C funding"},
            ],
            "jobs": {"signal": "hiring"},
            "funding": {"last_round": "Series B"},
        }

        result = detect_signals(snapshot)

        assert "danger_signals" in result
        assert "momentum_signals" in result
        danger = result["danger_signals"]
        assert any("layoff" in str(d).lower() for d in danger)

    def test_pipeline_summary(self):
        from agents.pipeline import get_pipeline_summary

        mock_opps = [
            {"company_name": "Co1", "stage": "discovery", "health_score": 30, "status": "active"},
            {"company_name": "Co2", "stage": "proposal", "health_score": 70, "status": "active"},
            {"company_name": "Co3", "stage": "poc", "health_score": 60, "status": "active"},
        ]

        with patch("agents.pipeline.pipeline_store.get_all_opportunities", return_value=mock_opps):
            summary = get_pipeline_summary()

            assert summary["total_count"] == 3
            assert "discovery" in summary["by_stage"]
            assert summary["avg_health"] > 0
            assert summary["unhealthy_count"] == 1  # Co1 at 30
