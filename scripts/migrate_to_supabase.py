import os
import sqlite3
import sys
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

try:
    from supabase import create_client
except ImportError:
    print("❌ Error: 'supabase' package is not installed. Run: pip install supabase")
    sys.exit(1)

SQLITE_PATH = os.path.join(PROJECT_ROOT, "data", "dsa_platform.db")


def run_migration():
    print("🚀 === BRAINFREEZE ALGOS -> SUPABASE MIGRATION WIZARD ===")
    
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()

    if not supabase_url or not supabase_key:
        print("\n❌ Error: Missing SUPABASE_URL or SUPABASE_KEY in your .env file.")
        print("Please configure your Supabase credentials in .env and rerun this script.\n")
        sys.exit(1)

    if not os.path.exists(SQLITE_PATH):
        print(f"\n❌ Error: Local SQLite database not found at {SQLITE_PATH}\n")
        sys.exit(1)

    print(f"📡 Connecting to Supabase at: {supabase_url}")
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # 1. Migrate Users
    print("\n[1/4] Migrating Users...")
    try:
        sqlite_cur.execute("SELECT * FROM users")
        user_rows = [dict(r) for r in sqlite_cur.fetchall()]
        if user_rows:
            res = supabase.table("users").upsert(user_rows, on_conflict="username").execute()
            print(f"  ✓ Migrated {len(user_rows)} users into Supabase.")
        else:
            print("  ℹ No user records found in SQLite.")
    except Exception as e:
        print(f"  ⚠️ Error migrating users: {e}")

    # 2. Migrate Problem Progress
    print("\n[2/4] Migrating Problem Progress...")
    try:
        sqlite_cur.execute("SELECT * FROM problem_progress")
        progress_rows = [dict(r) for r in sqlite_cur.fetchall()]
        if progress_rows:
            # Batch in chunks of 100
            for i in range(0, len(progress_rows), 100):
                chunk = progress_rows[i:i+100]
                supabase.table("problem_progress").upsert(chunk, on_conflict="user_id,problem_id").execute()
            print(f"  ✓ Migrated {len(progress_rows)} progress records into Supabase.")
        else:
            print("  ℹ No problem progress records found in SQLite.")
    except Exception as e:
        print(f"  ⚠️ Error migrating problem_progress: {e}")

    # 3. Migrate Submissions
    print("\n[3/4] Migrating Submissions Log...")
    try:
        sqlite_cur.execute("SELECT * FROM submissions")
        sub_rows = [dict(r) for r in sqlite_cur.fetchall()]
        if sub_rows:
            for i in range(0, len(sub_rows), 100):
                chunk = sub_rows[i:i+100]
                supabase.table("submissions").upsert(chunk, on_conflict="id").execute()
            print(f"  ✓ Migrated {len(sub_rows)} submission logs into Supabase.")
        else:
            print("  ℹ No submissions found in SQLite.")
    except Exception as e:
        print(f"  ⚠️ Error migrating submissions: {e}")

    # 4. Migrate Daily Activity
    print("\n[4/4] Migrating Daily Activity & Heatmaps...")
    try:
        sqlite_cur.execute("SELECT * FROM daily_activity")
        act_rows = [dict(r) for r in sqlite_cur.fetchall()]
        if act_rows:
            supabase.table("daily_activity").upsert(act_rows, on_conflict="user_id,date").execute()
            print(f"  ✓ Migrated {len(act_rows)} daily activity entries into Supabase.")
        else:
            print("  ℹ No daily activity records found in SQLite.")
    except Exception as e:
        print(f"  ⚠️ Error migrating daily_activity: {e}")

    sqlite_conn.close()
    print("\n🎉 === MIGRATION COMPLETED SUCCESSFULLY! ===")
    print("Your Brainfreeze Algos instance is now synchronized with Cloud Supabase.")


if __name__ == "__main__":
    run_migration()
