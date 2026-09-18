import datetime
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_INSTALLED = True
except ImportError:
    SUPABASE_INSTALLED = False


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dsa_platform.db")


class DSADatabase:
    """
    Dual-engine Database manager supporting:
    1. Supabase PostgreSQL (Cloud Database with Row-Level Security)
    2. Local SQLite3 (Zero-setup local development fallback)
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.is_supabase = False
        self.supabase: Optional[Any] = None

        # Check for Supabase credentials in environment
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()

        if SUPABASE_INSTALLED and supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                self.is_supabase = True
                print("[DSADatabase] Connected to Cloud Supabase PostgreSQL")
            except Exception as e:
                print(f"[DSADatabase] Failed to connect to Supabase: {e}. Falling back to SQLite.")
                self.is_supabase = False
        else:
            self.is_supabase = False

        if not self.is_supabase:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._init_sqlite_tables()
            self._seed_default_admin_sqlite()
            print("[DSADatabase] Using local SQLite database (data/dsa_platform.db)")

    # =========================================================================
    # SQLite Initialization & Helpers
    # =========================================================================

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                leetcode_user TEXT DEFAULT '',
                codechef_user TEXT DEFAULT '',
                codeforces_user TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
            """)

            # 2. Problem Progress Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS problem_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                problem_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unsolved',
                solved_at TEXT,
                attempts_count INTEGER DEFAULT 0,
                last_code TEXT,
                notes TEXT,
                is_bookmarked INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(user_id, problem_id)
            )
            """)

            # 3. Submissions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                problem_id TEXT NOT NULL,
                code TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_time_ms REAL,
                tests_passed INTEGER,
                tests_total INTEGER,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """)

            # 4. Daily Activity Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                date TEXT NOT NULL,
                problems_solved_count INTEGER DEFAULT 0,
                submissions_count INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
            """)

            # 5. Mock Interviews Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                target_role TEXT NOT NULL,
                target_company TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                focus_skills TEXT NOT NULL,
                qualification TEXT NOT NULL,
                problem_id TEXT NOT NULL,
                problem_title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                code TEXT DEFAULT '',
                hints_used INTEGER DEFAULT 0,
                time_spent_seconds INTEGER DEFAULT 0,
                tests_passed INTEGER DEFAULT 0,
                tests_total INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                hire_decision TEXT DEFAULT '',
                rubric_scores TEXT DEFAULT '{}',
                feedback TEXT DEFAULT '{}',
                transcript TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """)

            # 6. User Notion Integrations Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_notion_integrations (
                user_id INTEGER PRIMARY KEY,
                notion_token_encrypted TEXT NOT NULL,
                workspace_name TEXT DEFAULT 'Personal Workspace',
                workspace_icon TEXT DEFAULT '',
                bot_id TEXT DEFAULT '',
                problems_database_id TEXT DEFAULT '',
                scorecards_database_id TEXT DEFAULT '',
                auto_sync_enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            # 7. Community Public Chat Messages
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)

            # 8. Direct (Private) Messages
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read_at TEXT
            )
            """)
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_dm_participants ON direct_messages(sender_id, recipient_id)")
            except Exception:
                pass

            for table in ["problem_progress", "submissions", "daily_activity", "mock_interviews"]:
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row["name"] for row in cursor.fetchall()]
                    if "user_id" not in columns:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")
                except Exception:
                    pass

            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uq_daily_activity ON daily_activity(user_id, date)")
            except Exception:
                pass

            conn.commit()

    def _seed_default_admin_sqlite(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            if not cursor.fetchone():
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                hashed = generate_password_hash("admin123")
                cursor.execute("""
                INSERT OR IGNORE INTO users (username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, 'admin', ?)
                """, ("admin", "admin@brainfreezealgos.io", hashed, now_str))
                conn.commit()
                print(
                    "[DSADatabase] WARNING: seeded default admin account (admin / admin123). "
                    "There is currently no in-app change-password flow, so before deploying "
                    "anywhere reachable outside your own machine, update this account's "
                    "password_hash directly in the database (werkzeug.security.generate_password_hash) "
                    "or delete the row and create a fresh admin via /api/auth/register + a manual role update."
                )

    # =========================================================================
    # User Authentication & Management (Dual-Mode)
    # =========================================================================

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "user",
        leetcode_user: str = "",
        codechef_user: str = "",
        codeforces_user: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Register a new user with hashed password."""
        username = username.strip()
        email = email.strip().lower()
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long.", None
        if not email or "@" not in email:
            return False, "Please provide a valid email address.", None
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters long.", None

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hashed_pw = generate_password_hash(password)

        if self.is_supabase:
            try:
                # Check if username or email exists
                existing_res = self.supabase.table("users").select("id, username, email").or_(f"username.ilike.{username},email.ilike.{email}").execute()
                if existing_res.data:
                    for ex in existing_res.data:
                        if ex.get("username", "").lower() == username.lower():
                            return False, f"Username '{username}' is already taken.", None
                        if ex.get("email", "").lower() == email.lower():
                            return False, f"Email '{email}' is already registered.", None

                insert_payload = {
                    "username": username,
                    "email": email,
                    "password_hash": hashed_pw,
                    "role": role,
                    "leetcode_user": leetcode_user,
                    "codechef_user": codechef_user,
                    "codeforces_user": codeforces_user,
                    "is_active": 1,
                    "created_at": now_str,
                }
                res = self.supabase.table("users").insert(insert_payload).execute()
                if res.data and len(res.data) > 0:
                    user_data = dict(res.data[0])
                    user_data.pop("password_hash", None)
                    return True, "User registered successfully.", user_data
                return False, "Failed to register user in Supabase.", None
            except Exception as e:
                return False, f"Supabase error: {str(e)}", None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email FROM users WHERE username = ? OR email = ?", (username, email))
                existing = cursor.fetchone()
                if existing:
                    if existing["username"].lower() == username.lower():
                        return False, f"Username '{username}' is already taken.", None
                    if existing["email"].lower() == email:
                        return False, f"Email '{email}' is already registered.", None

                try:
                    cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, leetcode_user, codechef_user, codeforces_user, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (username, email, hashed_pw, role, leetcode_user, codechef_user, codeforces_user, now_str))
                    conn.commit()
                    user_id = cursor.lastrowid
                    user_data = self.get_user_by_id(user_id)
                    return True, "User registered successfully.", user_data
                except Exception as e:
                    return False, f"Database error: {str(e)}", None

    def authenticate_user(self, identifier: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate with username or email + password."""
        identifier = identifier.strip()
        if not identifier or not password:
            return False, "Please enter both identifier and password.", None

        if self.is_supabase:
            try:
                res = self.supabase.table("users").select("*").or_(f"username.ilike.{identifier},email.ilike.{identifier}").eq("is_active", 1).execute()
                if not res.data or len(res.data) == 0:
                    return False, "Invalid credentials or account is suspended.", None

                user_dict = dict(res.data[0])
                if not check_password_hash(user_dict["password_hash"], password):
                    return False, "Incorrect password. Please try again.", None

                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.supabase.table("users").update({"last_login": now_str}).eq("id", user_dict["id"]).execute()

                user_dict.pop("password_hash", None)
                user_dict["last_login"] = now_str
                return True, "Authentication successful.", user_dict
            except Exception as e:
                return False, f"Supabase auth error: {str(e)}", None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM users WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)) AND is_active = 1
                """, (identifier, identifier))
                user_row = cursor.fetchone()

                if not user_row:
                    return False, "Invalid credentials or account is suspended.", None

                user_dict = dict(user_row)
                if not check_password_hash(user_dict["password_hash"], password):
                    return False, "Incorrect password. Please try again.", None

                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, user_dict["id"]))
                conn.commit()

                user_dict.pop("password_hash", None)
                user_dict["last_login"] = now_str
                return True, "Authentication successful.", user_dict

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user profile by primary ID."""
        if self.is_supabase:
            try:
                res = self.supabase.table("users").select("*").eq("id", user_id).execute()
                if res.data and len(res.data) > 0:
                    d = dict(res.data[0])
                    d.pop("password_hash", None)
                    return d
                return None
            except Exception:
                return None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    d = dict(row)
                    d.pop("password_hash", None)
                    return d
                return None

    def get_all_users_for_admin(self, search: str = "", role_filter: str = "") -> List[Dict[str, Any]]:
        """Fetch all registered users with detailed progress telemetry for Admin Console."""
        if self.is_supabase:
            try:
                query = self.supabase.table("users").select("*")
                if search:
                    query = query.or_(f"username.ilike.%{search}%,email.ilike.%{search}%")
                if role_filter:
                    query = query.eq("role", role_filter)

                res = query.order("id", desc=True).execute()
                users_list = res.data or []

                result = []
                for u in users_list:
                    user_dict = dict(u)
                    user_dict.pop("password_hash", None)
                    u_id = user_dict["id"]

                    # Solved count
                    s_res = self.supabase.table("problem_progress").select("id", count="exact").eq("user_id", u_id).eq("status", "solved").execute()
                    solved_count = s_res.count or 0

                    # Submissions count
                    sub_res = self.supabase.table("submissions").select("id", count="exact").eq("user_id", u_id).execute()
                    subs_count = sub_res.count or 0

                    # Streak
                    streak = self._calculate_user_streak_supabase(u_id)

                    user_dict["total_solved"] = solved_count
                    user_dict["total_submissions"] = subs_count
                    user_dict["current_streak"] = streak
                    result.append(user_dict)

                return result
            except Exception:
                return []
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM users WHERE 1=1"
                params = []

                if search:
                    query += " AND (username LIKE ? OR email LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%"])
                if role_filter:
                    query += " AND role = ?"
                    params.append(role_filter)

                query += " ORDER BY id DESC"
                cursor.execute(query, params)
                user_rows = cursor.fetchall()

                result = []
                for u in user_rows:
                    user_dict = dict(u)
                    user_dict.pop("password_hash", None)
                    u_id = user_dict["id"]

                    cursor.execute("SELECT COUNT(*) FROM problem_progress WHERE user_id = ? AND status = 'solved'", (u_id,))
                    solved_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ?", (u_id,))
                    subs_count = cursor.fetchone()[0]

                    streak = self._calculate_user_streak_sqlite(cursor, u_id)

                    user_dict["total_solved"] = solved_count
                    user_dict["total_submissions"] = subs_count
                    user_dict["current_streak"] = streak
                    result.append(user_dict)

                return result

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        if new_role not in ["admin", "user"]:
            return False
        if self.is_supabase:
            try:
                res = self.supabase.table("users").update({"role": new_role}).eq("id", user_id).execute()
                return bool(res.data)
            except Exception:
                return False
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
                conn.commit()
                return cursor.rowcount > 0

    def toggle_user_status(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        new_status = 0 if user.get("is_active", 1) == 1 else 1

        if self.is_supabase:
            try:
                res = self.supabase.table("users").update({"is_active": new_status}).eq("id", user_id).execute()
                return bool(res.data)
            except Exception:
                return False
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
                conn.commit()
                return cursor.rowcount > 0

    def get_admin_dashboard_stats(self) -> Dict[str, Any]:
        """Aggregate global metrics for Admin Console."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        if self.is_supabase:
            try:
                # Total users
                u_res = self.supabase.table("users").select("id", count="exact").execute()
                total_users = u_res.count or 0

                # Total admins
                a_res = self.supabase.table("users").select("id", count="exact").eq("role", "admin").execute()
                total_admins = a_res.count or 0

                # Registered today
                reg_res = self.supabase.table("users").select("id", count="exact").like("created_at", f"{today_str}%").execute()
                registered_today = reg_res.count or 0

                # Global solved
                sol_res = self.supabase.table("problem_progress").select("id", count="exact").eq("status", "solved").execute()
                global_solved = sol_res.count or 0

                # Global submissions
                sub_res = self.supabase.table("submissions").select("id", count="exact").execute()
                global_submissions = sub_res.count or 0

                # Active today
                act_res = self.supabase.table("daily_activity").select("user_id").eq("date", today_str).gt("submissions_count", 0).execute()
                active_users_set = {r["user_id"] for r in (act_res.data or [])}
                active_today = len(active_users_set)

                # Recent users
                rec_res = self.supabase.table("users").select("id, username, email, role, created_at, leetcode_user, codechef_user, codeforces_user").order("id", desc=True).limit(6).execute()
                recent_users = rec_res.data or []

                return {
                    "total_users": total_users,
                    "total_admins": total_admins,
                    "registered_today": registered_today,
                    "global_solved": global_solved,
                    "global_submissions": global_submissions,
                    "active_today": active_today,
                    "recent_users": recent_users,
                }
            except Exception:
                return {
                    "total_users": 0, "total_admins": 0, "registered_today": 0,
                    "global_solved": 0, "global_submissions": 0, "active_today": 0, "recent_users": []
                }
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
                total_admins = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today_str}%",))
                registered_today = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM problem_progress WHERE status = 'solved'")
                global_solved = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM submissions")
                global_submissions = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM daily_activity WHERE date = ? AND submissions_count > 0", (today_str,))
                active_today = cursor.fetchone()[0]

                cursor.execute("SELECT id, username, email, role, created_at, leetcode_user, codechef_user, codeforces_user FROM users ORDER BY id DESC LIMIT 6")
                recent_users = [dict(r) for r in cursor.fetchall()]

                return {
                    "total_users": total_users,
                    "total_admins": total_admins,
                    "registered_today": registered_today,
                    "global_solved": global_solved,
                    "global_submissions": global_submissions,
                    "active_today": active_today,
                    "recent_users": recent_users,
                }

    # =========================================================================
    # Problem Progress & Activity (User-Scoped)
    # =========================================================================

    def get_progress(self, problem_id: str, user_id: int = 1) -> Optional[Dict[str, Any]]:
        """Retrieve progress for a specific problem and user."""
        if self.is_supabase:
            try:
                res = self.supabase.table("problem_progress").select("*").eq("user_id", user_id).eq("problem_id", problem_id).execute()
                if res.data and len(res.data) > 0:
                    return dict(res.data[0])
                return None
            except Exception:
                return None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM problem_progress WHERE user_id = ? AND problem_id = ?", (user_id, problem_id))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

    def get_all_progress(self, user_id: int = 1) -> Dict[str, Dict[str, Any]]:
        """Retrieve all problem progress entries for a specific user."""
        if self.is_supabase:
            try:
                res = self.supabase.table("problem_progress").select("*").eq("user_id", user_id).execute()
                rows = res.data or []
                return {row["problem_id"]: dict(row) for row in rows}
            except Exception:
                return {}
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM problem_progress WHERE user_id = ?", (user_id,))
                rows = cursor.fetchall()
                return {row["problem_id"]: dict(row) for row in rows}

    def record_attempt(
        self,
        problem_id: str,
        code: str,
        is_accepted: bool,
        exec_time_ms: float = 0.0,
        tests_passed: int = 0,
        tests_total: int = 0,
        error_message: str = "",
        user_id: int = 1,
    ) -> None:
        """Record an attempt/submission, update streak and problem progress."""
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        today_str = now.strftime("%Y-%m-%d")
        sub_status = "Accepted" if is_accepted else ("Runtime Error" if error_message else "Wrong Answer")

        if self.is_supabase:
            try:
                # 1. Log Submission
                sub_payload = {
                    "user_id": user_id,
                    "problem_id": problem_id,
                    "code": code,
                    "status": sub_status,
                    "execution_time_ms": exec_time_ms,
                    "tests_passed": tests_passed,
                    "tests_total": tests_total,
                    "error_message": error_message,
                    "created_at": now_str,
                }
                self.supabase.table("submissions").insert(sub_payload).execute()

                # 2. Daily Activity upsert
                act_res = self.supabase.table("daily_activity").select("*").eq("user_id", user_id).eq("date", today_str).execute()
                if act_res.data and len(act_res.data) > 0:
                    curr_act = act_res.data[0]
                    new_subs = (curr_act.get("submissions_count") or 0) + 1
                    new_solved = (curr_act.get("problems_solved_count") or 0) + (1 if is_accepted else 0)
                    self.supabase.table("daily_activity").update({
                        "submissions_count": new_subs,
                        "problems_solved_count": new_solved,
                    }).eq("id", curr_act["id"]).execute()
                else:
                    self.supabase.table("daily_activity").insert({
                        "user_id": user_id,
                        "date": today_str,
                        "submissions_count": 1,
                        "problems_solved_count": 1 if is_accepted else 0,
                    }).execute()

                # 3. Problem Progress upsert
                prog_res = self.supabase.table("problem_progress").select("*").eq("user_id", user_id).eq("problem_id", problem_id).execute()
                if prog_res.data and len(prog_res.data) > 0:
                    row = prog_res.data[0]
                    new_status = "solved" if (is_accepted or row.get("status") == "solved") else "attempted"
                    solved_at = row.get("solved_at")
                    if is_accepted and not solved_at:
                        solved_at = now_str

                    attempts = (row.get("attempts_count") or 0) + 1
                    self.supabase.table("problem_progress").update({
                        "status": new_status,
                        "last_code": code,
                        "attempts_count": attempts,
                        "solved_at": solved_at,
                        "updated_at": now_str,
                    }).eq("id", row["id"]).execute()
                else:
                    new_status = "solved" if is_accepted else "attempted"
                    solved_at = now_str if is_accepted else None
                    self.supabase.table("problem_progress").insert({
                        "user_id": user_id,
                        "problem_id": problem_id,
                        "status": new_status,
                        "solved_at": solved_at,
                        "attempts_count": 1,
                        "last_code": code,
                        "updated_at": now_str,
                    }).execute()
            except Exception as e:
                print(f"[DSADatabase] Failed to record attempt in Supabase: {e}")
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Log Submission
                cursor.execute("""
                INSERT INTO submissions (user_id, problem_id, code, status, execution_time_ms, tests_passed, tests_total, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, problem_id, code, sub_status, exec_time_ms, tests_passed, tests_total, error_message, now_str))

                # 2. Update Daily Activity
                cursor.execute("SELECT rowid, submissions_count, problems_solved_count FROM daily_activity WHERE user_id = ? AND date = ?", (user_id, today_str))
                act_row = cursor.fetchone()
                if act_row:
                    cursor.execute("""
                    UPDATE daily_activity 
                    SET submissions_count = submissions_count + 1,
                        problems_solved_count = problems_solved_count + ?
                    WHERE rowid = ?
                    """, (1 if is_accepted else 0, act_row[0]))
                else:
                    cursor.execute("""
                    INSERT INTO daily_activity (user_id, date, problems_solved_count, submissions_count)
                    VALUES (?, ?, ?, 1)
                    """, (user_id, today_str, 1 if is_accepted else 0))



                # 3. Check existing progress
                cursor.execute("SELECT * FROM problem_progress WHERE user_id = ? AND problem_id = ?", (user_id, problem_id))
                row = cursor.fetchone()

                if row:
                    new_status = "solved" if (is_accepted or row["status"] == "solved") else "attempted"
                    solved_at = row["solved_at"]
                    if is_accepted and not solved_at:
                        solved_at = now_str
                        cursor.execute("""
                        UPDATE daily_activity SET problems_solved_count = problems_solved_count + 1 WHERE user_id = ? AND date = ?
                        """, (user_id, today_str))

                    cursor.execute("""
                    UPDATE problem_progress
                    SET status = ?, last_code = ?, attempts_count = attempts_count + 1, solved_at = ?, updated_at = ?
                    WHERE user_id = ? AND problem_id = ?
                    """, (new_status, code, solved_at, now_str, user_id, problem_id))
                else:
                    new_status = "solved" if is_accepted else "attempted"
                    solved_at = now_str if is_accepted else None
                    if is_accepted:
                        cursor.execute("""
                        UPDATE daily_activity SET problems_solved_count = problems_solved_count + 1 WHERE user_id = ? AND date = ?
                        """, (user_id, today_str))

                    cursor.execute("""
                    INSERT INTO problem_progress (user_id, problem_id, status, solved_at, attempts_count, last_code, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """, (user_id, problem_id, new_status, solved_at, code, now_str))

                conn.commit()

    def update_notes_bookmark(
        self, problem_id: str, notes: Optional[str] = None, is_bookmarked: Optional[bool] = None, user_id: int = 1
    ) -> None:
        """Update personal notes or bookmark toggle for a problem."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.is_supabase:
            try:
                res = self.supabase.table("problem_progress").select("*").eq("user_id", user_id).eq("problem_id", problem_id).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    current_notes = notes if notes is not None else row.get("notes", "")
                    current_bm = int(is_bookmarked) if is_bookmarked is not None else (row.get("is_bookmarked") or 0)
                    self.supabase.table("problem_progress").update({
                        "notes": current_notes,
                        "is_bookmarked": current_bm,
                        "updated_at": now_str,
                    }).eq("id", row["id"]).execute()
                else:
                    self.supabase.table("problem_progress").insert({
                        "user_id": user_id,
                        "problem_id": problem_id,
                        "status": "unsolved",
                        "notes": notes or "",
                        "is_bookmarked": 1 if is_bookmarked else 0,
                        "updated_at": now_str,
                    }).execute()
            except Exception as e:
                print(f"[DSADatabase] Failed to update notes/bookmark in Supabase: {e}")
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM problem_progress WHERE user_id = ? AND problem_id = ?", (user_id, problem_id))
                row = cursor.fetchone()

                if row:
                    current_notes = notes if notes is not None else row["notes"]
                    current_bm = int(is_bookmarked) if is_bookmarked is not None else row["is_bookmarked"]
                    cursor.execute("""
                    UPDATE problem_progress SET notes = ?, is_bookmarked = ?, updated_at = ? WHERE user_id = ? AND problem_id = ?
                    """, (current_notes, current_bm, now_str, user_id, problem_id))
                else:
                    cursor.execute("""
                    INSERT INTO problem_progress (user_id, problem_id, status, notes, is_bookmarked, updated_at)
                    VALUES (?, ?, 'unsolved', ?, ?, ?)
                    """, (user_id, problem_id, notes or "", 1 if is_bookmarked else 0, now_str))

                conn.commit()

    def _calculate_user_streak_supabase(self, user_id: int) -> int:
        try:
            today = datetime.date.today()
            res = self.supabase.table("daily_activity").select("date").eq("user_id", user_id).gt("submissions_count", 0).order("date", desc=True).execute()
            rows = res.data or []
            active_dates = [datetime.datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows]

            current_streak = 0
            if active_dates:
                if active_dates[0] >= today - datetime.timedelta(days=1):
                    curr = active_dates[0]
                    current_streak = 1
                    for d in active_dates[1:]:
                        if d == curr - datetime.timedelta(days=1):
                            current_streak += 1
                            curr = d
                        else:
                            break
            return current_streak
        except Exception:
            return 0

    def _calculate_user_streak_sqlite(self, cursor: sqlite3.Cursor, user_id: int) -> int:
        today = datetime.date.today()
        cursor.execute("SELECT DISTINCT date FROM daily_activity WHERE user_id = ? AND submissions_count > 0 ORDER BY date DESC", (user_id,))
        active_dates = [datetime.datetime.strptime(r["date"], "%Y-%m-%d").date() for r in cursor.fetchall()]

        current_streak = 0
        if active_dates:
            if active_dates[0] >= today - datetime.timedelta(days=1):
                curr = active_dates[0]
                current_streak = 1
                for d in active_dates[1:]:
                    if d == curr - datetime.timedelta(days=1):
                        current_streak += 1
                        curr = d
                    else:
                        break
        return current_streak

    def get_stats(self, user_id: int = 1) -> Dict[str, Any]:
        """Calculate total solved, difficulty breakdown, streak, and daily heatmap for a user."""
        if self.is_supabase:
            try:
                # Solved
                sol_res = self.supabase.table("problem_progress").select("id", count="exact").eq("user_id", user_id).eq("status", "solved").execute()
                total_solved = sol_res.count or 0

                # Attempted
                att_res = self.supabase.table("problem_progress").select("id", count="exact").eq("user_id", user_id).eq("status", "attempted").execute()
                total_attempted = att_res.count or 0

                # Submissions
                sub_res = self.supabase.table("submissions").select("id", count="exact").eq("user_id", user_id).execute()
                total_submissions = sub_res.count or 0

                # Heatmap
                act_res = self.supabase.table("daily_activity").select("date, problems_solved_count, submissions_count").eq("user_id", user_id).order("date", desc=False).execute()
                activity_rows = act_res.data or []
                activity_map = {row["date"]: {"solved": row.get("problems_solved_count", 0), "submissions": row.get("submissions_count", 0)} for row in activity_rows}

                current_streak = self._calculate_user_streak_supabase(user_id)

                return {
                    "total_solved": total_solved,
                    "total_attempted": total_attempted,
                    "total_submissions": total_submissions,
                    "current_streak": current_streak,
                    "activity_heatmap": activity_map,
                }
            except Exception:
                return {
                    "total_solved": 0,
                    "total_attempted": 0,
                    "total_submissions": 0,
                    "current_streak": 0,
                    "activity_heatmap": {},
                }
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM problem_progress WHERE user_id = ? AND status = 'solved'", (user_id,))
                total_solved = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM problem_progress WHERE user_id = ? AND status = 'attempted'", (user_id,))
                total_attempted = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ?", (user_id,))
                total_submissions = cursor.fetchone()[0]

                cursor.execute("SELECT date, problems_solved_count, submissions_count FROM daily_activity WHERE user_id = ? ORDER BY date ASC", (user_id,))
                activity_rows = cursor.fetchall()
                activity_map = {row["date"]: {"solved": row["problems_solved_count"], "submissions": row["submissions_count"]} for row in activity_rows}

                current_streak = self._calculate_user_streak_sqlite(cursor, user_id)

                return {
                    "total_solved": total_solved,
                    "total_attempted": total_attempted,
                    "total_submissions": total_submissions,
                    "current_streak": current_streak,
                    "activity_heatmap": activity_map,
                }

    # =========================================================================
    # Mock Interview Engine Methods (Dual-Mode)
    # =========================================================================

    def create_interview_session(
        self,
        user_id: int,
        intake_data: Dict[str, Any],
        problem_id: str,
        problem_title: str,
        initial_code: str = "",
    ) -> Optional[int]:
        """Create a new mock interview session."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_role = intake_data.get("target_role", "Software Development Engineer (SDE)")
        target_company = intake_data.get("target_company", "FAANG / Tier-1 Tech")
        experience_level = intake_data.get("experience_level", "Junior (0-2 YOE)")
        focus_skills = intake_data.get("focus_skills", "General DSA")
        qualification = intake_data.get("qualification", "B.Tech/B.E. in CS/IT")

        if self.is_supabase:
            try:
                payload = {
                    "user_id": user_id,
                    "target_role": target_role,
                    "target_company": target_company,
                    "experience_level": experience_level,
                    "focus_skills": focus_skills,
                    "qualification": qualification,
                    "problem_id": problem_id,
                    "problem_title": problem_title,
                    "status": "in_progress",
                    "code": initial_code,
                    "hints_used": 0,
                    "time_spent_seconds": 0,
                    "tests_passed": 0,
                    "tests_total": 0,
                    "score": 0,
                    "hire_decision": "",
                    "rubric_scores": "{}",
                    "feedback": "{}",
                    "transcript": "[]",
                    "created_at": now_str,
                }
                res = self.supabase.table("mock_interviews").insert(payload).execute()
                if res.data and len(res.data) > 0:
                    return int(res.data[0]["id"])
            except Exception as e:
                print(f"[DSADatabase] Failed to create interview session in Supabase: {e}")

        # SQLite fallback / default
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO mock_interviews (
                    user_id, target_role, target_company, experience_level, focus_skills,
                    qualification, problem_id, problem_title, status, code,
                    hints_used, time_spent_seconds, tests_passed, tests_total,
                    score, hire_decision, rubric_scores, feedback, transcript, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_progress', ?, 0, 0, 0, 0, 0, '', '{}', '{}', '[]', ?)
                """, (
                    user_id, target_role, target_company, experience_level, focus_skills,
                    qualification, problem_id, problem_title, initial_code, now_str
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[DSADatabase] Failed to create interview session in SQLite: {e}")
            return None

    def get_interview_session(self, session_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Retrieve mock interview session details."""
        if self.is_supabase:
            try:
                q = self.supabase.table("mock_interviews").select("*").eq("id", session_id)
                if user_id is not None:
                    q = q.eq("user_id", user_id)
                res = q.execute()
                if res.data and len(res.data) > 0:
                    data = dict(res.data[0])
                    for k in ["rubric_scores", "feedback", "transcript"]:
                        if isinstance(data.get(k), str):
                            try:
                                data[k] = json.loads(data[k])
                            except Exception:
                                pass
                    return data
            except Exception as e:
                print(f"[DSADatabase] Supabase get_interview_session error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM mock_interviews WHERE id = ? AND user_id = ?", (session_id, user_id))
            else:
                cursor.execute("SELECT * FROM mock_interviews WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                for k in ["rubric_scores", "feedback", "transcript"]:
                    if isinstance(data.get(k), str):
                        try:
                            data[k] = json.loads(data[k])
                        except Exception:
                            pass
                return data
            return None

    def update_interview_transcript(self, session_id: int, transcript: List[Dict[str, Any]], user_id: Optional[int] = None) -> bool:
        """Update interview chat transcript."""
        transcript_str = json.dumps(transcript)
        if self.is_supabase:
            try:
                q = self.supabase.table("mock_interviews").update({"transcript": transcript_str}).eq("id", session_id)
                if user_id is not None:
                    q = q.eq("user_id", user_id)
                res = q.execute()
                if res.data:
                    return True
            except Exception as e:
                print(f"[DSADatabase] Supabase update transcript error: {e}")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if user_id is not None:
                    cursor.execute("UPDATE mock_interviews SET transcript = ? WHERE id = ? AND user_id = ?", (transcript_str, session_id, user_id))
                else:
                    cursor.execute("UPDATE mock_interviews SET transcript = ? WHERE id = ?", (transcript_str, session_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def update_interview_progress(
        self,
        session_id: int,
        code: Optional[str] = None,
        hints_used: Optional[int] = None,
        time_spent_seconds: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """Update active code, hints counter, or elapsed time."""
        updates: Dict[str, Any] = {}
        if code is not None:
            updates["code"] = code
        if hints_used is not None:
            updates["hints_used"] = hints_used
        if time_spent_seconds is not None:
            updates["time_spent_seconds"] = time_spent_seconds

        if not updates:
            return True

        if self.is_supabase:
            try:
                q = self.supabase.table("mock_interviews").update(updates).eq("id", session_id)
                if user_id is not None:
                    q = q.eq("user_id", user_id)
                q.execute()
            except Exception as e:
                print(f"[DSADatabase] Supabase update progress error: {e}")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                set_clauses = [f"{k} = ?" for k in updates.keys()]
                params = list(updates.values())
                params.append(session_id)
                query = f"UPDATE mock_interviews SET {', '.join(set_clauses)} WHERE id = ?"
                if user_id is not None:
                    query += " AND user_id = ?"
                    params.append(user_id)
                cursor.execute(query, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def complete_interview_session(
        self,
        session_id: int,
        code: str,
        tests_passed: int,
        tests_total: int,
        score: int,
        hire_decision: str,
        rubric_scores: Dict[str, Any],
        feedback: Dict[str, Any],
        status: str = "completed",
        time_spent_seconds: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """Mark interview session complete and store FAANG scorecard."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rubric_str = json.dumps(rubric_scores)
        feedback_str = json.dumps(feedback)

        updates: Dict[str, Any] = {
            "code": code,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "score": score,
            "hire_decision": hire_decision,
            "rubric_scores": rubric_str,
            "feedback": feedback_str,
            "status": status,
            "completed_at": now_str,
        }
        if time_spent_seconds is not None:
            updates["time_spent_seconds"] = time_spent_seconds

        if self.is_supabase:
            try:
                q = self.supabase.table("mock_interviews").update(updates).eq("id", session_id)
                if user_id is not None:
                    q = q.eq("user_id", user_id)
                q.execute()
            except Exception as e:
                print(f"[DSADatabase] Supabase complete_interview_session error: {e}")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                set_clauses = [f"{k} = ?" for k in updates.keys()]
                params = list(updates.values())
                params.append(session_id)
                query = f"UPDATE mock_interviews SET {', '.join(set_clauses)} WHERE id = ?"
                if user_id is not None:
                    query += " AND user_id = ?"
                    params.append(user_id)
                cursor.execute(query, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[DSADatabase] SQLite complete_interview_session error: {e}")
            return False

    def get_user_interview_history(self, user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieve list of past mock interviews for the candidate."""
        if self.is_supabase:
            try:
                res = (
                    self.supabase.table("mock_interviews")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                results = []
                for row in res.data or []:
                    d = dict(row)
                    for k in ["rubric_scores", "feedback", "transcript"]:
                        if isinstance(d.get(k), str):
                            try:
                                d[k] = json.loads(d[k])
                            except Exception:
                                pass
                    results.append(d)
                return results
            except Exception as e:
                print(f"[DSADatabase] Supabase get_user_interview_history error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM mock_interviews
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                for k in ["rubric_scores", "feedback", "transcript"]:
                    if isinstance(d.get(k), str):
                        try:
                            d[k] = json.loads(d[k])
                        except Exception:
                            pass
                results.append(d)
            return results

    # =========================================================================
    # User Notion Integrations (Encrypted Multi-Tenant Storage)
    # =========================================================================

    def save_notion_integration(
        self,
        user_id: int,
        notion_token_encrypted: str,
        workspace_name: str = "Personal Workspace",
        workspace_icon: str = "",
        bot_id: str = "",
        problems_database_id: str = "",
        scorecards_database_id: str = "",
        auto_sync_enabled: bool = True,
    ) -> bool:
        """Upsert a user's encrypted Notion credentials and provisioned database IDs."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.is_supabase:
            try:
                self.supabase.table("user_notion_integrations").upsert({
                    "user_id": user_id,
                    "notion_token_encrypted": notion_token_encrypted,
                    "workspace_name": workspace_name,
                    "workspace_icon": workspace_icon,
                    "bot_id": bot_id,
                    "problems_database_id": problems_database_id,
                    "scorecards_database_id": scorecards_database_id,
                    "auto_sync_enabled": auto_sync_enabled,
                    "updated_at": now_str,
                }).execute()
                return True
            except Exception as e:
                print(f"[DSADatabase] Supabase save_notion_integration error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO user_notion_integrations (
                user_id, notion_token_encrypted, workspace_name, workspace_icon,
                bot_id, problems_database_id, scorecards_database_id,
                auto_sync_enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                notion_token_encrypted = excluded.notion_token_encrypted,
                workspace_name = excluded.workspace_name,
                workspace_icon = excluded.workspace_icon,
                bot_id = excluded.bot_id,
                problems_database_id = excluded.problems_database_id,
                scorecards_database_id = excluded.scorecards_database_id,
                auto_sync_enabled = excluded.auto_sync_enabled,
                updated_at = excluded.updated_at
            """, (
                user_id, notion_token_encrypted, workspace_name, workspace_icon,
                bot_id, problems_database_id, scorecards_database_id,
                1 if auto_sync_enabled else 0, now_str, now_str
            ))
            conn.commit()
            return True

    def get_notion_integration(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a user's Notion integration record."""
        if self.is_supabase:
            try:
                res = self.supabase.table("user_notion_integrations").select("*").eq("user_id", user_id).execute()
                if res.data and len(res.data) > 0:
                    return dict(res.data[0])
            except Exception as e:
                print(f"[DSADatabase] Supabase get_notion_integration error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_notion_integrations WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["auto_sync_enabled"] = bool(d.get("auto_sync_enabled", 1))
                return d
        return None

    def delete_notion_integration(self, user_id: int) -> bool:
        """Disconnect and delete a user's Notion integration."""
        if self.is_supabase:
            try:
                self.supabase.table("user_notion_integrations").delete().eq("user_id", user_id).execute()
                return True
            except Exception as e:
                print(f"[DSADatabase] Supabase delete_notion_integration error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_notion_integrations WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    def update_notion_sync_settings(self, user_id: int, auto_sync_enabled: bool) -> bool:
        """Update auto-sync preference for a user's Notion integration."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_supabase:
            try:
                self.supabase.table("user_notion_integrations").update({
                    "auto_sync_enabled": auto_sync_enabled,
                    "updated_at": now_str,
                }).eq("user_id", user_id).execute()
                return True
            except Exception as e:
                print(f"[DSADatabase] Supabase update_notion_sync_settings error: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE user_notion_integrations
            SET auto_sync_enabled = ?, updated_at = ?
            WHERE user_id = ?
            """, (1 if auto_sync_enabled else 0, now_str, user_id))
            conn.commit()
            return True

    # =========================================================================
    # Community — Public Chat & Private Direct Messages (Dual-Mode)
    # =========================================================================

    def get_community_users(self, exclude_user_id: int, search: str = "") -> List[Dict[str, Any]]:
        """Directory of other active registered users, for starting a private conversation."""
        if self.is_supabase:
            try:
                q = self.supabase.table("users").select("id, username").eq("is_active", 1).neq("id", exclude_user_id)
                if search:
                    q = q.ilike("username", f"%{search}%")
                res = q.order("username").limit(50).execute()
                return res.data or []
            except Exception:
                return []
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT id, username FROM users WHERE is_active = 1 AND id != ?"
                params: List[Any] = [exclude_user_id]
                if search:
                    query += " AND username LIKE ?"
                    params.append(f"%{search}%")
                query += " ORDER BY username LIMIT 50"
                cursor.execute(query, params)
                return [dict(r) for r in cursor.fetchall()]

    def post_community_message(self, user_id: int, username: str, message: str) -> Optional[Dict[str, Any]]:
        """Post a message to the single global community chat room."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_supabase:
            try:
                res = self.supabase.table("community_messages").insert({
                    "user_id": user_id, "username": username, "message": message, "created_at": now_str,
                }).execute()
                if res.data:
                    return dict(res.data[0])
            except Exception as e:
                print(f"[DSADatabase] Failed to post community message: {e}")
            return None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO community_messages (user_id, username, message, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, username, message, now_str),
                )
                conn.commit()
                return {
                    "id": cursor.lastrowid, "user_id": user_id, "username": username,
                    "message": message, "created_at": now_str,
                }

    def get_community_messages(self, after_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch community chat messages: the latest `limit` if `after_id` is unset (initial
        load), or everything newer than `after_id` (polling for new messages). Always
        returned in chronological order."""
        if self.is_supabase:
            try:
                q = self.supabase.table("community_messages").select("*")
                if after_id:
                    res = q.gt("id", after_id).order("id", desc=False).execute()
                    return res.data or []
                res = q.order("id", desc=True).limit(limit).execute()
                return list(reversed(res.data or []))
            except Exception:
                return []
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if after_id:
                    cursor.execute(
                        "SELECT * FROM community_messages WHERE id > ? ORDER BY id ASC LIMIT ?",
                        (after_id, limit),
                    )
                    return [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT * FROM community_messages ORDER BY id DESC LIMIT ?", (limit,))
                rows = [dict(r) for r in cursor.fetchall()]
                rows.reverse()
                return rows

    def send_direct_message(self, sender_id: int, recipient_id: int, message: str) -> Optional[Dict[str, Any]]:
        """Send a private message. Caller is responsible for verifying recipient_id is a real user."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_supabase:
            try:
                res = self.supabase.table("direct_messages").insert({
                    "sender_id": sender_id, "recipient_id": recipient_id,
                    "message": message, "created_at": now_str, "read_at": None,
                }).execute()
                if res.data:
                    return dict(res.data[0])
            except Exception as e:
                print(f"[DSADatabase] Failed to send direct message: {e}")
            return None
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO direct_messages (sender_id, recipient_id, message, created_at) VALUES (?, ?, ?, ?)",
                    (sender_id, recipient_id, message, now_str),
                )
                conn.commit()
                return {
                    "id": cursor.lastrowid, "sender_id": sender_id, "recipient_id": recipient_id,
                    "message": message, "created_at": now_str, "read_at": None,
                }

    def get_direct_messages(
        self, user_id: int, other_user_id: int, after_id: Optional[int] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch a private thread between two users (both directions), chronological order.
        As a side effect, marks every message the other user sent to `user_id` as read —
        this is what "opening"/polling a conversation means for read-receipt purposes."""
        if self.is_supabase:
            try:
                q = self.supabase.table("direct_messages").select("*").or_(
                    f"and(sender_id.eq.{user_id},recipient_id.eq.{other_user_id}),"
                    f"and(sender_id.eq.{other_user_id},recipient_id.eq.{user_id})"
                )
                if after_id:
                    res = q.gt("id", after_id).order("id", desc=False).execute()
                    rows = res.data or []
                else:
                    res = q.order("id", desc=True).limit(limit).execute()
                    rows = list(reversed(res.data or []))
            except Exception:
                rows = []
            try:
                self.supabase.table("direct_messages").update({
                    "read_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }).eq("sender_id", other_user_id).eq("recipient_id", user_id).is_("read_at", "null").execute()
            except Exception:
                pass
            return rows
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if after_id:
                    cursor.execute("""
                        SELECT * FROM direct_messages
                        WHERE ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))
                        AND id > ?
                        ORDER BY id ASC LIMIT ?
                    """, (user_id, other_user_id, other_user_id, user_id, after_id, limit))
                    rows = [dict(r) for r in cursor.fetchall()]
                else:
                    cursor.execute("""
                        SELECT * FROM direct_messages
                        WHERE ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))
                        ORDER BY id DESC LIMIT ?
                    """, (user_id, other_user_id, other_user_id, user_id, limit))
                    rows = [dict(r) for r in cursor.fetchall()]
                    rows.reverse()

                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    UPDATE direct_messages SET read_at = ?
                    WHERE sender_id = ? AND recipient_id = ? AND read_at IS NULL
                """, (now_str, other_user_id, user_id))
                conn.commit()
                return rows

    def get_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Summarize each DM thread for a user: other participant, last message, unread count."""
        if self.is_supabase:
            try:
                res = self.supabase.table("direct_messages").select("*").or_(
                    f"sender_id.eq.{user_id},recipient_id.eq.{user_id}"
                ).order("id", desc=True).execute()
                rows = res.data or []
            except Exception:
                rows = []
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM direct_messages WHERE sender_id = ? OR recipient_id = ? ORDER BY id DESC",
                    (user_id, user_id),
                )
                rows = [dict(r) for r in cursor.fetchall()]

        threads: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            other_id = row["recipient_id"] if row["sender_id"] == user_id else row["sender_id"]
            if other_id not in threads:
                threads[other_id] = {
                    "other_user_id": other_id,
                    "last_message": row["message"],
                    "last_message_at": row["created_at"],
                    "unread_count": 0,
                }
            if row["recipient_id"] == user_id and not row.get("read_at"):
                threads[other_id]["unread_count"] += 1

        for other_id, thread in threads.items():
            user = self.get_user_by_id(other_id)
            thread["other_username"] = user["username"] if user else "Unknown User"

        return sorted(threads.values(), key=lambda t: t["last_message_at"], reverse=True)

