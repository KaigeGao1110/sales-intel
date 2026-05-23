"""
Check Supabase migration status.
Lists tables, row counts, and sample data from accounts and companies.
"""

import json
import os
import sys

from supabase import create_client

# All tables managed by SupabaseStorage
TABLES = [
    "accounts",
    "companies",
    "scores",
    "snapshots",
    "alerts",
    "outreach",
    "pipeline",
    "meeting_prep",
    "intros",
    "digests",
]


def main():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        sys.exit(1)

    sb = create_client(url, key)

    print("=" * 60)
    print("SUPABASE MIGRATION CHECK")
    print("=" * 60)

    # 1. List all tables and row counts
    print("\n[1] TABLES AND ROW COUNTS")
    print("-" * 40)
    for table in TABLES:
        try:
            result = sb.table(table).select("*", count="exact").limit(0).execute()
            count = result.count if result.count is not None else "?"
            print(f"  {table:<20} {count:>6} rows")
        except Exception as exc:
            print(f"  {table:<20} ERROR: {exc}")

    # 2. Show first 5 rows of accounts
    print("\n[2] ACCOUNTS TABLE (first 5 rows)")
    print("-" * 40)
    try:
        result = sb.table("accounts").select("*").limit(5).execute()
        if result.data:
            for row in result.data:
                print(f"  id={row['id']}")
                print(f"    name={row.get('name')}")
                print(f"    email={row.get('email')}")
                print(f"    company_name={row.get('company_name')}")
                print(f"    plan_type={row.get('plan_type')}")
                print(f"    is_active={row.get('is_active')}")
                print()
        else:
            print("  (no rows)")
    except Exception as exc:
        print(f"  ERROR: {exc}")

    # 3. Show first 5 rows of companies with account_id
    print("\n[3] COMPANIES TABLE (first 5 rows with account_id)")
    print("-" * 40)
    try:
        result = sb.table("companies").select("*").limit(5).execute()
        if result.data:
            for row in result.data:
                print(f"  id={row['id']}")
                print(f"    account_id={row.get('account_id')}")
                print(f"    name={row.get('name')}")
                print(f"    domain={row.get('domain')}")
                print(f"    status={row.get('status')}")
                print(f"    added_date={row.get('added_date')}")
                print()
        else:
            print("  (no rows)")
    except Exception as exc:
        print(f"  ERROR: {exc}")

    print("=" * 60)
    print("MIGRATION CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()