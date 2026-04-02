# Scout — Supabase Setup Guide

This guide walks you through migrating Scout's JSON-file storage to a Supabase PostgreSQL backend.

---

## 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in (or create a free account).
2. Click **New Project** → give it a name (e.g. `scout-db`) → choose a region close to you.
3. On the project dashboard, copy and save:
   - **Project URL** → `SUPABASE_URL`
   - **API Key** (`service_role` key, under Project Settings → API) → `SUPABASE_KEY`

   > **Security note:** The `service_role` key bypasses Row Level Security. Treat it like a database password. For read-heavy workloads you can use the `anon` key instead, but then you must configure Row Level Security (RLS) policies — not covered here.

---

## 2. Configure Environment Variables

Add these to your `.env` file (or `.env.local` for local development):

```env
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-service-role-key>
```

And make sure your app loads `.env` at startup (e.g. via `python-dotenv`).

---

## 3. Run the Schema Migration

### Option A — Via the Supabase Dashboard SQL Editor

1. Open the Supabase dashboard → **SQL Editor** → **New Query**.
2. Open `supabase/migrations/001_scout_schema.sql` and paste its contents.
3. Click **Run**.

### Option B — Via Supabase CLI

```bash
# Install the CLI (one-time)
npm install -g supabase

# Log in
supabase login

# Link to your project
supabase link --project-ref <your-project-ref>

# Push migrations
supabase db push
```

### Option C — Via `psql` directly

```bash
PGPASSWORD=<your-db-password> psql \
  -h <your-project-ref>.supabase.co \
  -p 5432 \
  -U postgres \
  -d postgres \
  -f supabase/migrations/001_scout_schema.sql
```

The connection details are on **Project Settings → Database** in the Supabase dashboard.

---

## 4. Verify the Tables Were Created

In the SQL Editor, run:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see: `alerts`, `companies`, `digests`, `intros`, `meeting_prep`, `outreach`, `pipeline`, `scores`, `snapshots`.

---

## 5. Migrate Existing JSON Data (One-time)

The script below migrates data from Scout's JSON files into Supabase. It is **idempotent** — you can re-run it safely, but it will create duplicate rows if you run it twice (each insert generates a fresh UUID). To avoid duplicates on re-runs, consider adding `ON CONFLICT` handling specific to your needs.

```python
"""
migrate_json_to_supabase.py

One-time migration script. Run it once after the schema is in place.

    python migrate_json_to_supabase.py

Requirements (install separately):
    pip install supabase python-dotenv
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

SCOUT_ROOT = Path(__file__).parent
DATA_DIR   = SCOUT_ROOT / "data"


def make_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key, options=ClientOptions())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def migrate_companies(sb: Client) -> dict[str, str]:
    """Migrate companies.json. Returns {old_id: new_id} for FK resolution."""
    file = DATA_DIR / "companies.json"
    if not file.exists():
        print("companies.json not found, skipping.")
        return {}

    data = json.loads(file.read_text())
    id_map: dict[str, str] = {}

    for c in data.get("companies", []):
        row = {
            "id": c["id"],
            "name": c["name"],
            "domain": c.get("domain", ""),
            "added_date": c.get("added_date", ""),
            "last_checked": c.get("last_checked"),
            "status": c.get("status", "active"),
            "alert_channels": c.get("alert_channels", ["console"]),
            "alert_email": c.get("alert_email", ""),
        }
        sb.table("companies").upsert(row, on_conflict="id").execute()
        id_map[c["id"]] = c["id"]
        print(f"  migrated company: {c['name']}")

    print(f"Companies: {len(id_map)} rows.")
    return id_map


def migrate_snapshots(sb: Client, id_map: dict[str, str]) -> None:
    """Migrate snapshot JSON files in data/snapshots/."""
    snapshot_dir = DATA_DIR / "snapshots"
    if not snapshot_dir.exists():
        print("snapshots/ not found, skipping.")
        return

    count = 0
    for f in snapshot_dir.glob("*.json"):
        try:
            snap = json.loads(f.read_text())
            company_id = snap.get("company_id", "")
            if company_id not in id_map:
                print(f"  SKIP {f.name} — unknown company_id")
                continue

            row = {
                "id": snap.get("id"),
                "company_id": company_id,
                "company_name": snap.get("company_name", ""),
                "source": snap.get("slot", "AM"),
                "check_date": snap.get("check_date", ""),
                "data": {
                    "news": snap.get("news", []),
                    "jobs_signal": snap.get("jobs", {}),
                    "reviews_signal": snap.get("reviews", {}),
                    "funding": snap.get("funding", {}),
                    "raw_signals": snap.get("raw_signals", []),
                },
            }
            sb.table("snapshots").upsert(row, on_conflict="id").execute()
            count += 1
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")

    print(f"Snapshots: {count} rows.")


def migrate_scores(sb: Client, id_map: dict[str, str]) -> None:
    """Migrate ~/.scout/scores.json."""
    file = Path.home() / ".scout" / "scores.json"
    if not file.exists():
        print("scores.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for s in data.get("scores", []):
        company_id = s.get("company_id", "")
        if company_id not in id_map:
            continue
        row = {
            "company_id": company_id,
            "company_name": s.get("company_name", ""),
            "score": s.get("score", 0),
            "grade": s.get("grade", ""),
            "factors": {
                "reasons": s.get("reasons", []),
                "recommended_action": s.get("recommended_action", ""),
            },
        }
        sb.table("scores").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Scores: {count} rows.")


def migrate_alerts(sb: Client, id_map: dict[str, str]) -> None:
    """Migrate data/alerts_log.json."""
    file = DATA_DIR / "alerts_log.json"
    if not file.exists():
        print("alerts_log.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for a in data.get("alerts", []):
        company_id = a.get("company_id", "")
        if company_id not in id_map:
            continue
        row = {
            "id": a["id"],
            "company_id": company_id,
            "company_name": a.get("company_name", ""),
            "alert_date": a.get("alert_date", utc_now()),
            "type": a.get("type", ""),
            "severity": a.get("severity", "medium"),
            "title": a.get("title", ""),
            "summary": a.get("summary", ""),
            "score": a.get("score", 0),
            "notified": a.get("notified", False),
            "notification_date": a.get("notification_date"),
            "channels": a.get("channels", []),
        }
        sb.table("alerts").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Alerts: {count} rows.")


def migrate_outreach(sb: Client, id_map: dict[str, str]) -> None:
    """Migrate ~/.scout/outreach.json."""
    file = Path.home() / ".scout" / "outreach.json"
    if not file.exists():
        print("outreach.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for o in data.get("outreach_records", []):
        company_id = o.get("company_id", "")
        if company_id not in id_map:
            continue
        row = {
            "id": o["id"],
            "company_id": company_id,
            "company_name": o.get("company_name", ""),
            "created_date": o.get("created_date", utc_now()),
            "contacts": o.get("contacts", []),
            "cold_emails": o.get("cold_emails", []),
            "linkedin_messages": o.get("linkedin_messages", []),
            "subject_lines": o.get("subject_lines", []),
        }
        sb.table("outreach").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Outreach: {count} rows.")


def migrate_pipeline(sb: Client) -> None:
    """Migrate data/pipeline.json."""
    file = DATA_DIR / "pipeline.json"
    if not file.exists():
        print("pipeline.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for o in data.get("opportunities", []):
        row = {
            "id": o["opportunity_id"],
            "company_name": o["company_name"],
            "stage": o.get("stage", "discovery"),
            "expected_close": o.get("expected_close"),
            "champion_contact": o.get("champion_contact"),
            "health_score": o.get("health_score", 50),
            "signals": o.get("signals", []),
            "last_assessed": o.get("last_assessed"),
            "status": o.get("status", "active"),
        }
        sb.table("pipeline").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Pipeline: {count} rows.")


def migrate_meeting_preps(sb: Client, id_map: dict[str, str]) -> None:
    """Migrate data/meeting_preps.json."""
    file = DATA_DIR / "meeting_preps.json"
    if not file.exists():
        print("meeting_preps.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for m in data.get("meeting_preps", []):
        company_id = m.get("company_id", "")
        row = {
            "id": m["meeting_id"],
            "company_id": company_id if company_id in id_map else None,
            "company_name": m.get("company_name", ""),
            "meeting_time": m.get("meeting_time"),
            "briefing": m.get("briefing", ""),
            "status": m.get("status", "scheduled"),
        }
        sb.table("meeting_prep").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Meeting preps: {count} rows.")


def migrate_intros(sb: Client) -> None:
    """Migrate data/intros.json."""
    file = DATA_DIR / "intros.json"
    if not file.exists():
        print("intros.json not found, skipping.")
        return

    data = json.loads(file.read_text())
    count = 0
    for i in data.get("intros", []):
        row = {
            "id": i["request_id"],
            "company_name": i["company_name"],
            "target_contact": i.get("target_contact", {}),
            "intro_paths": i.get("intro_paths", []),
        }
        sb.table("intros").upsert(row, on_conflict="id").execute()
        count += 1

    print(f"Intros: {count} rows.")


def main() -> None:
    print("Starting JSON → Supabase migration...\n")

    sb = make_client()

    id_map = migrate_companies(sb)
    migrate_snapshots(sb, id_map)
    migrate_scores(sb, id_map)
    migrate_alerts(sb, id_map)
    migrate_outreach(sb, id_map)
    migrate_pipeline(sb)
    migrate_meeting_preps(sb, id_map)
    migrate_intros(sb)

    print("\nMigration complete.")


if __name__ == "__main__":
    main()
```

---

## 6. Install the Python Dependency

Add the SDK to your `requirements.txt`:

```python
# requirements.txt
supabase>=2.0.0
```

Then install:

```bash
pip install supabase>=2.0.0
```

---

## 7. Switch Storage in Your Code

Instead of importing from the JSON storage modules:

```python
# Old — JSON file backend
from storage import companies, scores, alerts

companies.add("Acme Corp", "acme.com")
scores.save(cid, "Acme Corp", 85, "A", reasons, "Send outreach")
```

Switch to the Supabase client:

```python
# New — Supabase backend
from storage.supabase_client import SupabaseStorage

store = SupabaseStorage()

store.companies.add("Acme Corp", "acme.com")
store.scores.save(cid, "Acme Corp", 85, "A", reasons, "Send outreach")
store.alerts.save_alert(cid, "Acme Corp", "news", "high", ...)
```

Each sub-client (`companies`, `scores`, `snapshots`, etc.) has the same methods as the original JSON modules, so the call sites should not need to change.

---

## 8. Rollback / Keep the JSON Files

- **Do NOT delete the JSON files** until you have verified the Supabase integration is working correctly.
- The JSON files can be kept as a local backup.
- To revert: simply stop using `SupabaseStorage` and go back to importing the original modules.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `SUPABASE_URL and SUPABASE_KEY environment variables must be set` | Check your `.env` is loaded; `print(os.environ.get("SUPABASE_URL"))` to debug |
| `Invalid URL` error | Make sure `SUPABASE_URL` does not have a trailing `/` |
| `JWT expired` or auth errors | The anon key may have expired; regenerate under Project Settings → API |
| Duplicate rows after re-running migration | The migration script is designed to run once; use `ON CONFLICT` clauses or truncate tables before re-running |
| `rows affected: 0` on delete | This is normal — the row may not exist; it returns `False` gracefully |

---

## Going to Production

- **Enable Row Level Security (RLS)** and write policies so the anon key can only do what you intend.
- **Use the `anon` key** in client code (never the `service_role` key in frontend/unsandboxed contexts).
- **Set up Point-in-Time Recovery** (available on Supabase Pro tier) for disaster recovery.
- **Consider connection pooling** via `pgbouncer` if you expect high concurrency.
