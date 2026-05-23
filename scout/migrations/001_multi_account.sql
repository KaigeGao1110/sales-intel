-- Scout Multi-Account Architecture Migration
-- Run this migration against your Supabase project to add multi-account support.
--
-- Prerequisites:
--   - Supabase SQL Editor or psql connected to your Supabase project
--   - Backup your data before running in production
--
-- Usage:
--   1. Review this migration in a non-production environment first
--   2. Run against production with proper backup in place
--   3. The migration is idempotent: rerunning after partial failure may cause errors
--      on already-created objects. Drop objects first if needed.

BEGIN;

-- ══════════════════════════════════════════════════════════════════════════════
-- 1. Create accounts table
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS accounts (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    name            TEXT            NOT NULL,
    email           TEXT            NOT NULL UNIQUE,
    company_name     TEXT            NOT NULL,
    plan_type       TEXT            NOT NULL DEFAULT 'free',
    max_companies   INTEGER         NOT NULL DEFAULT 5,
    is_active       BOOLEAN         NOT NULL DEFAULT true,
    notification_channels JSONB     NOT NULL DEFAULT '["email"]',
    alert_threshold INTEGER         NOT NULL DEFAULT 10,
    webhook_url     TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_accounts_is_active  ON accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_accounts_email     ON accounts(email);

-- ══════════════════════════════════════════════════════════════════════════════
-- 2. Add account_id to companies (NOT NULL — each company belongs to an account)
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_companies_account_id      ON companies(account_id);
CREATE INDEX IF NOT EXISTS idx_companies_account_status  ON companies(account_id, status);

-- ══════════════════════════════════════════════════════════════════════════════
-- 3. Add account_id to snapshots (nullable — historical data may predate accounts)
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE snapshots
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_snapshots_account_id  ON snapshots(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 4. Add account_id to alerts
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_alerts_account_id  ON alerts(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 5. Add account_id to scores
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE scores
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_scores_account_id  ON scores(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 6. Add account_id to outreach
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE outreach
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_outreach_account_id  ON outreach(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 7. Add account_id to pipeline
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE pipeline
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_pipeline_account_id  ON pipeline(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 8. Add account_id to intros
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE intros
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_intros_account_id  ON intros(account_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- 9. Add account_id to meeting_prep
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE meeting_prep
    ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_meeting_prep_account_id  ON meeting_prep(account_id);

COMMIT;

-- ══════════════════════════════════════════════════════════════════════════════
-- Verification queries (run these to confirm the migration succeeded)
-- ══════════════════════════════════════════════════════════════════════════════

-- SELECT table_name, column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND column_name = 'account_id'
-- ORDER BY table_name;

-- SELECT table_name, indexname, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
--   AND indexname LIKE 'idx_%_account_id'
-- ORDER BY tablename;
