-- Scout Supabase Schema Migration 001
-- Run this after creating a Supabase project.

BEGIN;

-- ─────────────────────────────────────────────
-- Companies
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS companies (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    domain      VARCHAR(255) DEFAULT '',
    added_date  VARCHAR(20)  DEFAULT '',
    last_checked TIMESTAMPTZ,
    status      VARCHAR(20)  DEFAULT 'active',  -- 'active' | 'paused'
    alert_channels JSONB    DEFAULT '["console"]'::jsonb,
    alert_email  VARCHAR(255) DEFAULT '',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_status    ON companies(status);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at);

-- ─────────────────────────────────────────────
-- Snapshots
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS snapshots (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    company_name VARCHAR(255) DEFAULT '',
    source      VARCHAR(10)  DEFAULT 'AM',   -- 'AM' | 'PM' (daily slot)
    check_date  VARCHAR(20)  DEFAULT '',
    data        JSONB        NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_company_id  ON snapshots(company_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots(created_at DESC);

-- ─────────────────────────────────────────────
-- Scores
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id        UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    company_name      VARCHAR(255) DEFAULT '',
    score             INT         NOT NULL DEFAULT 0,
    grade             VARCHAR(5)  DEFAULT '',   -- A | B | C | D
    factors           JSONB       NOT NULL DEFAULT '{}',
    -- factors shape: { "reasons": [...], "recommended_action": "..." }
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scores_company_id   ON scores(company_id);
CREATE INDEX IF NOT EXISTS idx_scores_created_at  ON scores(created_at DESC);

-- ─────────────────────────────────────────────
-- Alerts
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id         UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    company_name       VARCHAR(255) DEFAULT '',
    alert_date         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    type               VARCHAR(30)  DEFAULT '',   -- news | layoff | funding | review | jobs
    severity           VARCHAR(10)  DEFAULT 'medium',
    title              VARCHAR(500) DEFAULT '',
    summary            TEXT         DEFAULT '',
    score              INT          DEFAULT 0,
    notified           BOOLEAN      DEFAULT false,
    notification_date  TIMESTAMPTZ,
    channels           JSONB        DEFAULT '[]'::jsonb,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alerts_company_id   ON alerts(company_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at  ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_date  ON alerts(alert_date DESC);

-- ─────────────────────────────────────────────
-- Outreach
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outreach (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    company_name        VARCHAR(255) DEFAULT '',
    created_date        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    contacts            JSONB       DEFAULT '[]'::jsonb,
    cold_emails         JSONB       DEFAULT '[]'::jsonb,
    linkedin_messages   JSONB       DEFAULT '[]'::jsonb,
    subject_lines       JSONB       DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_company_id  ON outreach(company_id);
CREATE INDEX IF NOT EXISTS idx_outreach_created_at ON outreach(created_at DESC);

-- ─────────────────────────────────────────────
-- Pipeline (Opportunities)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name     VARCHAR(255) NOT NULL,
    stage            VARCHAR(30)  DEFAULT 'discovery',
    expected_close   VARCHAR(30),
    champion_contact VARCHAR(255),
    health_score     INT          DEFAULT 50,
    signals          JSONB       DEFAULT '[]'::jsonb,
    last_assessed    TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    status           VARCHAR(20)  DEFAULT 'active',
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_company_name ON pipeline(company_name);
CREATE INDEX IF NOT EXISTS idx_pipeline_status       ON pipeline(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_health_score  ON pipeline(health_score);
CREATE INDEX IF NOT EXISTS idx_pipeline_created_at    ON pipeline(created_at DESC);

-- ─────────────────────────────────────────────
-- Meeting Prep
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meeting_prep (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id   UUID        REFERENCES companies(id) ON DELETE SET NULL,
    company_name VARCHAR(255) DEFAULT '',
    meeting_time TIMESTAMPTZ,
    briefing     TEXT        DEFAULT '',
    status       VARCHAR(20) DEFAULT 'scheduled',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_meeting_prep_company_id ON meeting_prep(company_id);
CREATE INDEX IF NOT EXISTS idx_meeting_prep_status     ON meeting_prep(status);
CREATE INDEX IF NOT EXISTS idx_meeting_prep_meeting_time ON meeting_prep(meeting_time DESC);

-- ─────────────────────────────────────────────
-- Intros (Warm Intro Requests)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS intros (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name    VARCHAR(255) NOT NULL,
    target_contact  JSONB       NOT NULL DEFAULT '{}',
    intro_paths     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intros_company_name ON intros(company_name);
CREATE INDEX IF NOT EXISTS idx_intros_created_at  ON intros(created_at DESC);

-- ─────────────────────────────────────────────
-- Digests
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS digests (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    type       VARCHAR(50)  NOT NULL,
    content    JSONB       NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_digests_type       ON digests(type);
CREATE INDEX IF NOT EXISTS idx_digests_created_at ON digests(created_at DESC);

COMMIT;
