import json
import os
import sys
import time
from functools import wraps

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from flask import Flask, Response, jsonify, render_template, request, session, stream_with_context
from dotenv import load_dotenv

from src.leetcode_client import LeetCodeClient
from src.codechef_client import CodeChefClient
from src.codeforces_client import CodeforcesClient
from src.problem_loader import ProblemLoader
from src.code_runner import PythonCodeRunner
from src.database import DSADatabase
from src.llm_router import LLMRouter
from src.ai_news_aggregator import fetch_trending_ai_news
from src.explainer import ExplainerEngine, get_sample_test_cases_for_problem
from src.problem_details import get_problem_enrichments
from src.ai_code_reviewer import AICodeReviewer
from src.interview_engine import InterviewEngine
from src.notion_engine import NotionEngine, NotionVault

load_dotenv()

app = Flask(__name__)
_DEFAULT_SECRET_KEY = "dsa_nexus_quantum_secret_2026_rbac_x89a"
app.secret_key = os.getenv("SECRET_KEY", _DEFAULT_SECRET_KEY)
if app.secret_key == _DEFAULT_SECRET_KEY:
    print(
        "[Brainfreeze Algos] WARNING: SECRET_KEY is not set in .env — using the hardcoded "
        "source default. Session cookies are signed with this key, so anyone who reads the "
        "source can forge a login session for any user, including admin. Set SECRET_KEY to a "
        "long random value (see README) before deploying anywhere reachable outside your own machine."
    )
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Multi-Platform Clients
leetcode_client = LeetCodeClient()
codechef_client = CodeChefClient()
codeforces_client = CodeforcesClient()

# DSA Curriculum Catalog & Database
problem_loader = ProblemLoader()
db = DSADatabase()

# AI Mentor Chat — routed through LLMRouter, which tries OpenRouter, then
# Groq, then Gemini (whichever have keys configured) so a single provider
# outage or rate limit doesn't interrupt the chat. Optional at deploy time;
# the chat route degrades to a clean "not configured" response when no key
# is set for any provider, instead of failing. Trending AI News does NOT
# use any of these — it pulls from free, keyless public APIs (arXiv +
# Hacker News), so it works even without a single AI key configured.
llm_router = LLMRouter()

# AI-powered DSA explanation engine (cached per problem+approach)
explainer_engine = ExplainerEngine()

# AI-powered Code Reviewer & Big-O Analyzer
ai_code_reviewer = AICodeReviewer()

# AI-powered Timed Mock Interview Engine
interview_engine = InterviewEngine()

# Cache for multi-platform external profiles
cache = {
    "leetcode": {},
    "codechef": {},
    "codeforces": {},
}

# In-memory cache for the trending AI news feed — serve every user the same
# cached result within the TTL rather than re-fetching both source APIs per
# request.
AI_NEWS_TTL_SECONDS = 60 * 60  # 1 hour (free sources, cheap to refresh more often)
ai_news_cache = {"items": None, "fetched_at": 0.0}


# =============================================================================
# Authentication Helpers & Decorators
# =============================================================================

def get_current_user():
    """Retrieve currently authenticated user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.get_user_by_id(user_id)


def _safe_int(value, default=0):
    """Coerce a request payload value to int, falling back to `default` on bad input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in.",
                "auth_required": True,
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in.",
                "auth_required": True,
            }), 401
        if user.get("role") != "admin":
            return jsonify({
                "success": False,
                "error": "Access denied. Admin privileges required.",
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Core Application Views
# =============================================================================

@app.route("/")
def index():
    user = get_current_user()
    lc_user = (user.get("leetcode_user") if user and user.get("leetcode_user") else os.getenv("LEETCODE_USERNAME", "lee215"))
    cc_user = (user.get("codechef_user") if user and user.get("codechef_user") else os.getenv("CODECHEF_USERNAME", "tourist"))
    cf_user = (user.get("codeforces_user") if user and user.get("codeforces_user") else os.getenv("CODEFORCES_USERNAME", "tourist"))

    return render_template(
        "index.html",
        current_user=user,
        leetcode_user=lc_user,
        codechef_user=cc_user,
        codeforces_user=cf_user,
    )


# =============================================================================
# Auth REST APIs
# =============================================================================

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Register a new user account with role 'user'."""
    payload = request.get_json() or {}
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "")
    leetcode_user = payload.get("leetcode_user", "").strip()
    codechef_user = payload.get("codechef_user", "").strip()
    codeforces_user = payload.get("codeforces_user", "").strip()

    success, msg, user_data = db.create_user(
        username=username,
        email=email,
        password=password,
        role="user",
        leetcode_user=leetcode_user,
        codechef_user=codechef_user,
        codeforces_user=codeforces_user,
    )

    if not success:
        return jsonify({"success": False, "error": msg}), 400

    # Automatically set session
    session["user_id"] = user_data["id"]
    return jsonify({
        "success": True,
        "message": "Account created successfully! Welcome to Brainfreeze Algos.",
        "user": user_data,
    })


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate user by username/email and password."""
    payload = request.get_json() or {}
    identifier = payload.get("identifier", "").strip() or payload.get("username", "").strip() or payload.get("email", "").strip()
    password = payload.get("password", "")

    success, msg, user_data = db.authenticate_user(identifier, password)
    if not success:
        return jsonify({"success": False, "error": msg}), 401

    session["user_id"] = user_data["id"]
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user_data['username']}!",
        "user": user_data,
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Clear session on logout."""
    session.clear()
    return jsonify({"success": True, "message": "Successfully signed out."})


@app.route("/api/auth/me")
def auth_me():
    """Return currently logged-in user details and role."""
    user = get_current_user()
    if user:
        return jsonify({"success": True, "authenticated": True, "user": user})
    return jsonify({"success": True, "authenticated": False, "user": None})


# =============================================================================
# Admin Console REST APIs
# =============================================================================

@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    """Get high-level statistics for Admin Command Center."""
    stats = db.get_admin_dashboard_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/admin/users")
@admin_required
def admin_users():
    """Get full details of all registered users with progress telemetry."""
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()
    users = db.get_all_users_for_admin(search=search, role_filter=role_filter)
    return jsonify({"success": True, "users": users, "total_count": len(users)})


@app.route("/api/admin/user/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_change_role(user_id):
    """Change role of a user (admin or user)."""
    payload = request.get_json() or {}
    new_role = payload.get("role")
    if not new_role:
        return jsonify({"success": False, "error": "Role parameter is required."}), 400

    success = db.update_user_role(user_id, new_role)
    if success:
        return jsonify({"success": True, "message": f"User role updated to '{new_role}'."})
    return jsonify({"success": False, "error": "Failed to update role or invalid role."}), 400


@app.route("/api/admin/user/<int:user_id>/status", methods=["POST"])
@admin_required
def admin_toggle_status(user_id):
    """Toggle user account status (active/suspended)."""
    success = db.toggle_user_status(user_id)
    if success:
        return jsonify({"success": True, "message": "User account status toggled successfully."})
    return jsonify({"success": False, "error": "Failed to toggle user status."}), 400


# =============================================================================
# Multi-Platform External APIs
# =============================================================================

@app.route("/api/config")
@login_required
def get_config():
    user = get_current_user()
    return jsonify({
        "leetcode": user.get("leetcode_user") if user and user.get("leetcode_user") else os.getenv("LEETCODE_USERNAME", ""),
        "codechef": user.get("codechef_user") if user and user.get("codechef_user") else os.getenv("CODECHEF_USERNAME", ""),
        "codeforces": user.get("codeforces_user") if user and user.get("codeforces_user") else os.getenv("CODEFORCES_USERNAME", ""),
    })


@app.route("/api/leetcode/<username>")
@login_required
def get_leetcode_data(username):
    username = username.strip()
    if not username:
        return jsonify({"success": False, "error": "Username cannot be empty"}), 400

    force_refresh = request.args.get("refresh", "false").lower() == "true"
    if not force_refresh and username in cache["leetcode"]:
        return jsonify({"success": True, "data": cache["leetcode"][username], "cached": True})

    try:
        data = leetcode_client.get_full_dashboard(username)
        data["platform"] = "leetcode"
        cache["leetcode"][username] = data
        return jsonify({"success": True, "data": data, "cached": False})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"LeetCode error: {str(e)}"}), 500


@app.route("/api/codechef/<username>")
@login_required
def get_codechef_data(username):
    username = username.strip()
    if not username:
        return jsonify({"success": False, "error": "Username cannot be empty"}), 400

    force_refresh = request.args.get("refresh", "false").lower() == "true"
    if not force_refresh and username in cache["codechef"]:
        return jsonify({"success": True, "data": cache["codechef"][username], "cached": True})

    try:
        data = codechef_client.get_user_profile(username)
        cache["codechef"][username] = data
        return jsonify({"success": True, "data": data, "cached": False})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"CodeChef error: {str(e)}"}), 500


@app.route("/api/codeforces/<username>")
@login_required
def get_codeforces_data(username):
    username = username.strip()
    if not username:
        return jsonify({"success": False, "error": "Handle cannot be empty"}), 400

    force_refresh = request.args.get("refresh", "false").lower() == "true"
    if not force_refresh and username in cache["codeforces"]:
        return jsonify({"success": True, "data": cache["codeforces"][username], "cached": True})

    try:
        data = codeforces_client.get_user_profile(username)
        cache["codeforces"][username] = data
        return jsonify({"success": True, "data": data, "cached": False})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"Codeforces error: {str(e)}"}), 500


# =============================================================================
# DSA Studio & Progress APIs (User-Scoped)
# =============================================================================

@app.route("/api/dsa/steps")
@login_required
def get_dsa_steps():
    """Get all curriculum steps with total vs solved counts for current user."""
    user = get_current_user()
    user_id = user["id"]

    steps_summary = problem_loader.get_steps_summary()
    all_progress = db.get_all_progress(user_id=user_id)

    for step in steps_summary:
        solved_count = sum(1 for pid in step["problem_ids"] if all_progress.get(pid, {}).get("status") == "solved")
        step["solved_count"] = solved_count
        step["progress_pct"] = round((solved_count / step["total_problems"] * 100), 1) if step["total_problems"] > 0 else 0

    return jsonify({"success": True, "steps": steps_summary})


@app.route("/api/dsa/problems")
@login_required
def get_dsa_problems():
    """List problems with filtering and user-scoped status."""
    user = get_current_user()
    user_id = user["id"]

    step_filter = request.args.get("step", "")
    difficulty_filter = request.args.get("difficulty", "")
    status_filter = request.args.get("status", "")
    search_query = request.args.get("search", "").lower().strip()

    all_probs = problem_loader.get_all_problems()
    all_progress = db.get_all_progress(user_id=user_id)

    filtered = []
    for p in all_probs:
        pid = p["id"]
        prog = all_progress.get(pid, {})
        status = prog.get("status", "unsolved")
        is_bookmarked = bool(prog.get("is_bookmarked", 0))

        if step_filter and p["step"] != step_filter:
            continue
        if difficulty_filter and p["difficulty"].lower() != difficulty_filter.lower():
            continue
        if status_filter:
            if status_filter == "bookmarked" and not is_bookmarked:
                continue
            elif status_filter != "bookmarked" and status != status_filter:
                continue
        if search_query:
            if search_query not in p["title"].lower() and search_query not in p["step"].lower() and search_query not in p["topic"].lower():
                continue

        item = {
            "id": p["id"],
            "title": p["title"],
            "step": p["step"],
            "topic": p["topic"],
            "difficulty": p["difficulty"],
            "method_name": p["method_name"],
            "status": status,
            "is_bookmarked": is_bookmarked,
            "solved_at": prog.get("solved_at"),
            "attempts_count": prog.get("attempts_count", 0),
        }
        filtered.append(item)

    return jsonify({"success": True, "problems": filtered, "total_count": len(filtered)})


@app.route("/api/dsa/problem/<problem_id>")
@login_required
def get_dsa_problem_details(problem_id):
    """Get full details of a problem including starter code, user code, notes, and solution."""
    user = get_current_user()
    user_id = user["id"]

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found"}), 404

    prog = db.get_progress(problem_id, user_id=user_id) or {}
    user_code = prog.get("last_code") or prob["starter_code"]
    enrichments = get_problem_enrichments(prob)

    return jsonify({
        "success": True,
        "problem": {
            "id": prob["id"],
            "title": prob["title"],
            "step": prob["step"],
            "topic": prob["topic"],
            "difficulty": prob["difficulty"],
            "method_name": prob["method_name"],
            "description": prob["description"],
            "starter_code": prob["starter_code"],
            "user_code": user_code,
            "reference_solution": prob["reference_solution"],
            "brute_force_solution": prob.get("brute_force_solution"),
            "status": prog.get("status", "unsolved"),
            "notes": prog.get("notes", ""),
            "is_bookmarked": bool(prog.get("is_bookmarked", 0)),
            "attempts_count": prog.get("attempts_count", 0),
            "solved_at": prog.get("solved_at"),
            "parameters": enrichments["parameters"],
            "return_type": enrichments["return_type"],
            "signature": enrichments["signature"],
            "constraints": enrichments["constraints"],
            "sample_test_cases": enrichments["sample_test_cases"],
        }
    })


@app.route("/api/dsa/run", methods=["POST"])
@login_required
def run_dsa_code():
    """Execute Python code against test inputs or custom input."""
    payload = request.get_json() or {}
    problem_id = payload.get("problem_id", "")
    code = payload.get("code", "")
    custom_input = payload.get("custom_input", "")

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found"}), 404

    try:
        res = PythonCodeRunner.execute_code(
            user_code=code,
            method_name=prob["method_name"],
            reference_solution=prob.get("reference_solution"),
            custom_input=custom_input,
            test_cases=prob.get("test_cases"),
        )
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": f"Code execution failed: {str(e)}"}), 500


@app.route("/api/dsa/submit", methods=["POST"])
@login_required
def submit_dsa_code():
    """Submit solution, evaluate against all test cases, update streak and progress for current user."""
    user = get_current_user()
    user_id = user["id"]

    payload = request.get_json() or {}
    problem_id = payload.get("problem_id", "")
    code = payload.get("code", "")

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found"}), 404

    try:
        res = PythonCodeRunner.execute_code(
            user_code=code,
            method_name=prob["method_name"],
            reference_solution=prob.get("reference_solution"),
            test_cases=prob.get("test_cases"),
        )

        is_accepted = res.get("passed", False)
        db.record_attempt(
            problem_id=problem_id,
            code=code,
            is_accepted=is_accepted,
            exec_time_ms=res.get("execution_time_ms", 0.0),
            tests_passed=res.get("tests_passed", 0),
            tests_total=res.get("tests_total", 0),
            error_message=res.get("error") or "",
            user_id=user_id,
        )

        stats = db.get_stats(user_id=user_id)
        return jsonify({
            "success": True,
            "result": res,
            "is_accepted": is_accepted,
            "stats": stats,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Submission failed: {str(e)}"}), 500


@app.route("/api/dsa/notes", methods=["POST"])
@login_required
def save_dsa_notes():
    """Save user notes or toggle bookmark for a problem."""
    user = get_current_user()
    user_id = user["id"]

    payload = request.get_json() or {}
    problem_id = payload.get("problem_id", "")
    notes = payload.get("notes")
    is_bookmarked = payload.get("is_bookmarked")

    db.update_notes_bookmark(problem_id, notes=notes, is_bookmarked=is_bookmarked, user_id=user_id)
    return jsonify({"success": True})


@app.route("/api/dsa/stats")
@login_required
def get_dsa_stats():
    """Get overall DSA practice stats, streak, heatmap, and step roadmaps for current user."""
    user = get_current_user()
    user_id = user["id"]

    stats = db.get_stats(user_id=user_id)
    all_problems = problem_loader.get_all_problems()
    all_progress = db.get_all_progress(user_id=user_id)

    total_problems = len(all_problems)
    total_easy = sum(1 for p in all_problems if p["difficulty"] == "Easy")
    total_medium = sum(1 for p in all_problems if p["difficulty"] == "Medium")
    total_hard = sum(1 for p in all_problems if p["difficulty"] == "Hard")

    solved_easy = sum(1 for p in all_problems if p["difficulty"] == "Easy" and all_progress.get(p["id"], {}).get("status") == "solved")
    solved_medium = sum(1 for p in all_problems if p["difficulty"] == "Medium" and all_progress.get(p["id"], {}).get("status") == "solved")
    solved_hard = sum(1 for p in all_problems if p["difficulty"] == "Hard" and all_progress.get(p["id"], {}).get("status") == "solved")

    steps_summary = problem_loader.get_steps_summary()
    for step in steps_summary:
        solved_cnt = sum(1 for pid in step["problem_ids"] if all_progress.get(pid, {}).get("status") == "solved")
        step["solved_count"] = solved_cnt
        step["progress_pct"] = round((solved_cnt / step["total_problems"] * 100), 1) if step["total_problems"] > 0 else 0

    return jsonify({
        "success": True,
        "stats": {
            **stats,
            "total_available": total_problems,
            "easy": {"solved": solved_easy, "total": total_easy},
            "medium": {"solved": solved_medium, "total": total_medium},
            "hard": {"solved": solved_hard, "total": total_hard},
            "steps": steps_summary,
        }
    })


# =============================================================================
# AI Mentor Chat & Trending AI News — login-gated like every other service;
# each route additionally checks llm_router.is_configured so the UI can show
# a clean setup hint instead of a broken feature when no provider API key
# (OpenRouter / Groq / Gemini) has been configured yet.
# =============================================================================

@app.route("/api/ai/status")
@login_required
def ai_status():
    """Lets the frontend know whether the AI features are usable."""
    return jsonify({"success": True, "configured": llm_router.is_configured})


@app.route("/api/ai/chat", methods=["POST"])
@login_required
def ai_chat():
    """Streams an Ask AI mentor reply as Server-Sent Events."""
    if not llm_router.is_configured:
        return jsonify({
            "success": False,
            "error": "AI Mentor isn't configured yet. Add OPENROUTER_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY to your .env file and restart the server.",
        }), 503

    payload = request.get_json() or {}
    user_message = (payload.get("message") or "").strip()
    history = payload.get("history") or []

    if not user_message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400
    if not isinstance(history, list):
        history = []

    # Bound token usage/cost: only forward well-formed recent turns.
    trimmed_history = [
        {"role": m.get("role"), "content": m.get("content")}
        for m in history[-16:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ]

    system_prompt = {
        "role": "system",
        "content": (
            "You are the Brainfreeze Algos AI Mentor — a focused, practical assistant for engineers "
            "and researchers preparing for AI/ML roles (Data Scientist, GenAI Engineer, "
            "Forward-Deployed Engineer, LLM Developer, NLP Engineer, Deep Learning Engineer). "
            "You help with: Data Structures & Algorithms concepts and interview problems; "
            "machine learning / deep learning / NLP / GenAI theory and system design; "
            "career and interview-prep guidance for AI/ML roles; and general questions about "
            "the AI field. Be concise and technically precise, and use fenced code blocks for "
            "code. If asked something unrelated to software engineering, AI/ML, or careers in "
            "the field, answer briefly and steer back to what you're here to help with."
        ),
    }
    messages = [system_prompt] + trimmed_history + [{"role": "user", "content": user_message}]

    def generate():
        try:
            for chunk in llm_router.stream_chat(messages):
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/ai/news")
@login_required
def ai_news():
    """Trending AI/ML news from free public APIs (arXiv + Hacker News), cached
    server-side. No OpenRouter key required — this works out of the box."""
    now = time.time()
    force_refresh = request.args.get("refresh", "false").lower() == "true"

    if not force_refresh and ai_news_cache["items"] is not None and (now - ai_news_cache["fetched_at"] < AI_NEWS_TTL_SECONDS):
        return jsonify({"success": True, "items": ai_news_cache["items"], "cached": True})

    try:
        items = fetch_trending_ai_news()
        ai_news_cache["items"] = items
        ai_news_cache["fetched_at"] = now
        return jsonify({"success": True, "items": items, "cached": False})
    except Exception as e:
        # Prefer serving a stale cache over a hard failure, if we have one.
        if ai_news_cache["items"] is not None:
            return jsonify({"success": True, "items": ai_news_cache["items"], "cached": True, "stale": True})
        return jsonify({"success": False, "error": str(e)}), 502


# =============================================================================
# DSA Explain — AI-generated step-by-step textual + visual approach explanations
# =============================================================================

@app.route("/api/dsa/explain/<problem_id>")
@login_required
def explain_problem(problem_id):
    """Return a structured explanation for a problem's optimized or brute-force approach.
    Results are cached permanently in data/dsa_explanations.json — AI called once per
    unique problem+approach combination, served instantly on every subsequent request.
    """
    approach = request.args.get("approach", "optimized").strip().lower()
    if approach not in ("optimized", "brute"):
        approach = "optimized"

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found"}), 404

    force = request.args.get("force", "0") == "1"

    try:
        explanation = explainer_engine.generate(
            problem_id=problem_id,
            approach=approach,
            problem_meta=prob,
            force=force,
        )
        return jsonify({"success": True, "explanation": explanation})
    except Exception as e:
        return jsonify({"success": False, "error": f"Explanation generation failed: {str(e)}"}), 500


# =============================================================================
# DSA Code Reviewer & Big-O Analyzer ("Review My Code")
# =============================================================================

@app.route("/api/dsa/review", methods=["POST"])
@login_required
def review_user_code():
    """Analyze the user's active code for time/space complexity, anti-patterns,
    edge cases, and provide an optimal refactoring recommendation.
    """
    payload = request.get_json() or {}
    problem_id = (payload.get("problem_id") or "").strip()
    code = (payload.get("code") or "").strip()

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found"}), 404

    try:
        review_data = ai_code_reviewer.review_code(
            problem_meta=prob,
            user_code=code,
        )
        return jsonify({"success": True, "review": review_data})
    except Exception as e:
        return jsonify({"success": False, "error": f"Code review failed: {str(e)}"}), 500


# =============================================================================
# Timed AI Mock Interview Mode (45-Minute Technical Round)
# =============================================================================

@app.route("/api/interview/start", methods=["POST"])
@login_required
def start_mock_interview():
    """Validate mandatory candidate intake details, match problem, and initialize 45-min round."""
    user = get_current_user()
    user_id = user["id"]

    data = request.get_json() or {}
    intake = data.get("intake") or {}

    # Strict intake validation: without details the test must not start!
    required_fields = [
        ("target_role", "Target Role"),
        ("target_company", "Target Company / Tier"),
        ("experience_level", "Experience Level"),
        ("focus_skills", "Focus DSA / AI/ML Skills"),
        ("qualification", "Academic / Technical Qualification"),
    ]

    for field_key, field_name in required_fields:
        val = (intake.get(field_key) or "").strip()
        if not val:
            return jsonify({
                "success": False,
                "error": f"Candidate detail '{field_name}' is strictly required before starting the 45-minute technical interview.",
            }), 400

    problems = problem_loader.get_all_problems()
    if not problems:
        return jsonify({"success": False, "error": "Problem curriculum is currently unavailable."}), 500

    try:
        matched_problem = interview_engine.select_problem(intake, problems)
        greeting = interview_engine.generate_initial_greeting(intake, matched_problem)

        # Initialize session in database
        initial_transcript = [
            {
                "role": "interviewer",
                "text": greeting,
                "timestamp": time.strftime("%H:%M:%S"),
            }
        ]

        session_id = db.create_interview_session(
            user_id=user_id,
            intake_data=intake,
            problem_id=matched_problem["id"],
            problem_title=matched_problem["title"],
            initial_code=matched_problem.get("starter_code", ""),
        )

        if not session_id:
            return jsonify({"success": False, "error": "Could not create interview session in database."}), 500

        db.update_interview_transcript(session_id, initial_transcript, user_id=user_id)

        # Enrich problem metadata
        enrichments = get_problem_enrichments(matched_problem)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "duration_seconds": 2700,  # 45 minutes
            "intake": intake,
            "problem": {
                "id": matched_problem["id"],
                "title": matched_problem["title"],
                "step": matched_problem.get("step", ""),
                "topic": matched_problem.get("topic", ""),
                "difficulty": matched_problem.get("difficulty", "Medium"),
                "method_name": matched_problem["method_name"],
                "description": matched_problem.get("description", ""),
                "starter_code": matched_problem.get("starter_code", ""),
                "parameters": enrichments.get("parameters", []),
                "return_type": enrichments.get("return_type", ""),
                "signature": enrichments.get("signature", ""),
                "constraints": enrichments.get("constraints", []),
                "sample_test_cases": enrichments.get("sample_test_cases", []),
            },
            "greeting": greeting,
            "transcript": initial_transcript,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to start interview: {str(e)}"}), 500


@app.route("/api/interview/chat", methods=["POST"])
@login_required
def chat_mock_interview():
    """Handle candidate chat, approach pitch, or 3-tier progressive hint requests."""
    user = get_current_user()
    user_id = user["id"]

    data = request.get_json() or {}
    session_id = data.get("session_id")
    message = (data.get("message") or "").strip()
    message_type = data.get("message_type", "chat")  # 'chat', 'pitch', 'hint'
    hint_level = _safe_int(data.get("hint_level"), 1)
    current_code = data.get("current_code", "")

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id."}), 400

    session_data = db.get_interview_session(session_id, user_id=user_id)
    if not session_data:
        return jsonify({"success": False, "error": "Interview session not found or unauthorized."}), 404

    prob = problem_loader.get_problem(session_data["problem_id"])
    if not prob:
        return jsonify({"success": False, "error": "Problem not found."}), 404

    transcript = session_data.get("transcript") or []
    hints_used = session_data.get("hints_used") or 0

    try:
        if message_type == "hint":
            hint_info = interview_engine.generate_hint(prob, hint_level=hint_level, hint_number=hints_used + 1)
            hints_used += 1
            db.update_interview_progress(session_id, hints_used=hints_used, code=current_code, user_id=user_id)

            transcript.append({
                "role": "system",
                "text": f"💡 Requested {hint_info['label']} (-{hint_info['penalty']} pts)",
                "timestamp": time.strftime("%H:%M:%S"),
            })
            transcript.append({
                "role": "interviewer",
                "text": hint_info["text"],
                "timestamp": time.strftime("%H:%M:%S"),
            })
            db.update_interview_transcript(session_id, transcript, user_id=user_id)

            return jsonify({
                "success": True,
                "type": "hint",
                "hint": hint_info,
                "hints_used": hints_used,
                "transcript": transcript,
            })

        # Regular question or approach pitch
        if not message:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        transcript.append({
            "role": "user",
            "type": message_type,
            "text": message,
            "timestamp": time.strftime("%H:%M:%S"),
        })

        intake = {
            "target_role": session_data.get("target_role"),
            "target_company": session_data.get("target_company"),
            "experience_level": session_data.get("experience_level"),
            "focus_skills": session_data.get("focus_skills"),
            "qualification": session_data.get("qualification"),
        }

        interviewer_reply = interview_engine.chat_interviewer(
            intake=intake,
            problem=prob,
            user_message=message,
            chat_history=transcript,
            current_code=current_code,
        )

        transcript.append({
            "role": "interviewer",
            "text": interviewer_reply,
            "timestamp": time.strftime("%H:%M:%S"),
        })

        db.update_interview_transcript(session_id, transcript, user_id=user_id)
        if current_code:
            db.update_interview_progress(session_id, code=current_code, user_id=user_id)

        return jsonify({
            "success": True,
            "type": message_type,
            "reply": interviewer_reply,
            "transcript": transcript,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Interviewer chat failed: {str(e)}"}), 500


@app.route("/api/interview/run", methods=["POST"])
@login_required
def run_mock_interview_tests():
    """Run tests on active code during interview without submitting."""
    user = get_current_user()
    user_id = user["id"]

    data = request.get_json() or {}
    session_id = data.get("session_id")
    code = data.get("code", "")
    time_spent_seconds = _safe_int(data.get("time_spent_seconds"), 0)

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id."}), 400

    session_data = db.get_interview_session(session_id, user_id=user_id)
    if not session_data:
        return jsonify({"success": False, "error": "Interview session not found."}), 404

    prob = problem_loader.get_problem(session_data["problem_id"])
    if not prob:
        return jsonify({"success": False, "error": "Problem not found."}), 404

    try:
        res = PythonCodeRunner.execute_code(
            user_code=code,
            method_name=prob["method_name"],
            reference_solution=prob.get("reference_solution"),
            test_cases=prob.get("test_cases"),
        )

        db.update_interview_progress(
            session_id=session_id,
            code=code,
            time_spent_seconds=time_spent_seconds,
            user_id=user_id,
        )

        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": f"Test run failed: {str(e)}"}), 500


@app.route("/api/interview/submit", methods=["POST"])
@login_required
def submit_mock_interview():
    """Evaluate full interview, grade against FAANG rubric, save to DB, and return scorecard."""
    user = get_current_user()
    user_id = user["id"]

    data = request.get_json() or {}
    session_id = data.get("session_id")
    code = data.get("code", "")
    time_spent_seconds = _safe_int(data.get("time_spent_seconds"), 0)
    status = data.get("status", "completed")  # 'completed' or 'timed_out'

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id."}), 400

    session_data = db.get_interview_session(session_id, user_id=user_id)
    if not session_data:
        return jsonify({"success": False, "error": "Interview session not found."}), 404

    prob = problem_loader.get_problem(session_data["problem_id"])
    if not prob:
        return jsonify({"success": False, "error": "Problem not found."}), 404

    try:
        # Run complete test suite
        test_res = PythonCodeRunner.execute_code(
            user_code=code,
            method_name=prob["method_name"],
            reference_solution=prob.get("reference_solution"),
            test_cases=prob.get("test_cases"),
        )

        tests_passed = test_res.get("tests_passed", 0)
        tests_total = test_res.get("tests_total", 0)
        is_accepted = bool(test_res.get("passed", False))

        intake = {
            "target_role": session_data.get("target_role"),
            "target_company": session_data.get("target_company"),
            "experience_level": session_data.get("experience_level"),
            "focus_skills": session_data.get("focus_skills"),
            "qualification": session_data.get("qualification"),
        }

        transcript = session_data.get("transcript") or []
        hints_used = session_data.get("hints_used") or 0

        # Calculate scorecard
        eval_card = interview_engine.evaluate_interview(
            intake=intake,
            problem=prob,
            user_code=code,
            test_result=test_res,
            time_spent_seconds=time_spent_seconds,
            hints_used=hints_used,
            chat_history=transcript,
        )

        score = eval_card["score"]
        hire_decision = eval_card["hire_decision"]
        rubric_scores = eval_card["rubric_scores"]
        feedback = eval_card["feedback"]
        tests_passed = eval_card["tests_passed"]
        tests_total = eval_card["tests_total"]

        # Save to database
        db.complete_interview_session(
            session_id=session_id,
            code=code,
            tests_passed=tests_passed,
            tests_total=tests_total,
            score=score,
            hire_decision=hire_decision,
            rubric_scores=rubric_scores,
            feedback=feedback,
            status=status,
            time_spent_seconds=time_spent_seconds,
            user_id=user_id,
        )

        # Also log to standard problem attempts so candidate's activity and streak reflect the practice
        db.record_attempt(
            problem_id=session_data["problem_id"],
            code=code,
            is_accepted=is_accepted,
            exec_time_ms=test_res.get("execution_time_ms", 0.0),
            tests_passed=tests_passed,
            tests_total=tests_total,
            error_message=test_res.get("error") or "",
            user_id=user_id,
        )

        return jsonify({
            "success": True,
            "scorecard": eval_card,
            "test_result": test_res,
            "session_id": session_id,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Interview submission failed: {str(e)}"}), 500


@app.route("/api/interview/history", methods=["GET"])
@login_required
def get_mock_interview_history():
    """Retrieve history of mock interviews completed by the authenticated user."""
    user = get_current_user()
    user_id = user["id"]
    history = db.get_user_interview_history(user_id=user_id, limit=30)
    return jsonify({"success": True, "history": history})


@app.route("/api/interview/session/<int:session_id>", methods=["GET"])
@login_required
def get_mock_interview_session(session_id: int):
    """Retrieve specific mock interview session details."""
    user = get_current_user()
    user_id = user["id"]
    sess = db.get_interview_session(session_id, user_id=user_id)
    if not sess:
        return jsonify({"success": False, "error": "Interview session not found."}), 404
    return jsonify({"success": True, "session": sess})


# =============================================================================
# Notion Integration Routes (Multi-Tenant & Encrypted)
# =============================================================================

@app.route("/api/notion/status", methods=["GET"])
@login_required
def get_notion_status():
    """Retrieve current user's Notion integration status and database IDs."""
    user = get_current_user()
    user_id = user["id"]
    integration = db.get_notion_integration(user_id)
    if not integration:
        return jsonify({"success": True, "connected": False})

    return jsonify({
        "success": True,
        "connected": True,
        "workspace_name": integration.get("workspace_name") or "Personal Workspace",
        "workspace_icon": integration.get("workspace_icon") or "",
        "problems_db_id": integration.get("problems_database_id") or "",
        "scorecards_db_id": integration.get("scorecards_database_id") or "",
        "auto_sync_enabled": bool(integration.get("auto_sync_enabled", True)),
        "updated_at": integration.get("updated_at") or "",
    })


@app.route("/api/notion/connect", methods=["POST"])
@login_required
def connect_notion():
    """Verify Notion token, auto-provision databases, encrypt credentials, and save to DB."""
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() or {}
    raw_token = (data.get("token") or "").strip()
    parent_page_id = (data.get("parent_page_id") or "").strip() or None
    auto_provision = data.get("auto_provision", True)

    if not raw_token:
        return jsonify({"success": False, "error": "Notion integration token is required."}), 400

    # 1. Verify token
    verify_res = NotionEngine.verify_token(raw_token)
    if not verify_res.get("valid"):
        return jsonify({"success": False, "error": verify_res.get("error", "Invalid Notion token.")}), 400

    workspace_name = verify_res.get("workspace_name") or "Personal Workspace"
    bot_id = verify_res.get("bot_id") or ""

    # 2. Auto-provision if requested
    problems_db_id = (data.get("problems_db_id") or "").strip()
    scorecards_db_id = (data.get("scorecards_db_id") or "").strip()

    if auto_provision and not problems_db_id:
        prov_res = NotionEngine.auto_provision_workspace(raw_token, parent_page_id)
        if not prov_res.get("success"):
            return jsonify({"success": False, "error": prov_res.get("error", "Failed to auto-create Notion databases.")}), 400
        problems_db_id = prov_res.get("problems_db_id", "")
        scorecards_db_id = prov_res.get("scorecards_db_id", "")

    # 3. Encrypt token at rest
    encrypted_token = NotionVault.encrypt_token(raw_token)

    # 4. Save to user database
    saved = db.save_notion_integration(
        user_id=user_id,
        notion_token_encrypted=encrypted_token,
        workspace_name=workspace_name,
        bot_id=bot_id,
        problems_database_id=problems_db_id,
        scorecards_database_id=scorecards_db_id,
        auto_sync_enabled=True,
    )
    if not saved:
        return jsonify({"success": False, "error": "Database error saving Notion integration."}), 500

    return jsonify({
        "success": True,
        "workspace_name": workspace_name,
        "problems_db_id": problems_db_id,
        "scorecards_db_id": scorecards_db_id,
        "message": "Notion connected and workspace databases provisioned successfully!",
    })


@app.route("/api/notion/disconnect", methods=["POST"])
@login_required
def disconnect_notion():
    """Disconnect and remove Notion integration for authenticated user."""
    user = get_current_user()
    user_id = user["id"]
    db.delete_notion_integration(user_id)
    return jsonify({"success": True, "message": "Notion integration disconnected."})


@app.route("/api/notion/sync-problem", methods=["POST"])
@login_required
def sync_problem_to_notion():
    """Sync problem solution, complexity, and personal notes to user's Notion database."""
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() or {}

    problem_id = data.get("problem_id")
    if not problem_id:
        return jsonify({"success": False, "error": "Problem ID required."}), 400

    prob = problem_loader.get_problem(problem_id)
    if not prob:
        return jsonify({"success": False, "error": "Problem not found."}), 404

    integration = db.get_notion_integration(user_id)
    if not integration or not integration.get("problems_database_id"):
        return jsonify({"success": False, "error": "Notion is not connected or Problems database is missing. Please connect Notion first."}), 400

    token = NotionVault.decrypt_token(integration["notion_token_encrypted"])
    db_id = integration["problems_database_id"]

    code = data.get("code") or prob.get("starter_code") or ""
    complexity = data.get("complexity") or ""
    notes = data.get("notes") or ""
    test_result = data.get("test_result")

    sync_res = NotionEngine.sync_problem_solution(
        token=token,
        database_id=db_id,
        problem=prob,
        user_code=code,
        complexity=complexity,
        user_notes=notes,
        test_result=test_result,
    )

    if not sync_res.get("success"):
        return jsonify({"success": False, "error": sync_res.get("error", "Failed to sync to Notion.")}), 400

    return jsonify({
        "success": True,
        "action": sync_res.get("action", "created"),
        "url": sync_res.get("url"),
        "page_id": sync_res.get("page_id"),
    })


@app.route("/api/notion/sync-interview", methods=["POST"])
@login_required
def sync_interview_to_notion():
    """Sync a mock interview scorecard to user's Notion database."""
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"success": False, "error": "Session ID required."}), 400

    sess = db.get_interview_session(session_id, user_id=user_id)
    if not sess:
        return jsonify({"success": False, "error": "Interview session not found."}), 404

    integration = db.get_notion_integration(user_id)
    if not integration or not integration.get("scorecards_database_id"):
        return jsonify({"success": False, "error": "Notion is not connected or Scorecards database is missing. Please connect Notion first."}), 400

    token = NotionVault.decrypt_token(integration["notion_token_encrypted"])
    db_id = integration["scorecards_database_id"]

    scorecard = {
        "score": sess.get("score", 0),
        "hire_decision": sess.get("hire_decision", "LEAN HIRE"),
        "tests_passed": sess.get("tests_passed", 0),
        "tests_total": sess.get("tests_total", 0),
        "time_spent_seconds": sess.get("time_spent_seconds", 0),
        "rubric_scores": sess.get("rubric_scores") or {},
        "feedback": sess.get("feedback") or {},
    }

    interview_data = {
        "intake": {
            "target_role": sess.get("target_role", ""),
            "target_company": sess.get("target_company", ""),
        }
    }

    sync_res = NotionEngine.sync_interview_scorecard(
        token=token,
        database_id=db_id,
        interview_data=interview_data,
        scorecard=scorecard,
        user_code=sess.get("code") or "",
    )

    if not sync_res.get("success"):
        return jsonify({"success": False, "error": sync_res.get("error", "Failed to export scorecard to Notion.")}), 400

    return jsonify({
        "success": True,
        "url": sync_res.get("url"),
        "page_id": sync_res.get("page_id"),
    })


@app.route("/api/notion/toggle-autosync", methods=["POST"])
@login_required
def toggle_notion_autosync():
    """Toggle auto-sync preference."""
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() or {}
    enabled = bool(data.get("auto_sync_enabled", True))
    db.update_notion_sync_settings(user_id, enabled)
    return jsonify({"success": True, "auto_sync_enabled": enabled})


# =============================================================================
# Community — Public Chat & Private Direct Messages
# Registered-users-only, same as every other tab: there's no separate "guest"
# role in this app, so @login_required is what "registered, not a guest"
# means here — the pre-login gate never renders any of this.
# =============================================================================

MAX_MESSAGE_LENGTH = 2000


@app.route("/api/community/messages")
@login_required
def get_community_messages():
    """Fetch the public community chat: latest messages on first load, or
    everything newer than `after_id` when polling for new ones."""
    after_id = request.args.get("after_id", type=int)
    limit = min(request.args.get("limit", 50, type=int) or 50, 100)
    messages = db.get_community_messages(after_id=after_id, limit=limit)
    return jsonify({"success": True, "messages": messages})


@app.route("/api/community/messages", methods=["POST"])
@login_required
def post_community_message():
    """Post a message to the public community chat room."""
    user = get_current_user()
    payload = request.get_json() or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"success": False, "error": f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)."}), 400

    saved = db.post_community_message(user_id=user["id"], username=user["username"], message=message)
    if not saved:
        return jsonify({"success": False, "error": "Failed to post message."}), 500
    return jsonify({"success": True, "message_data": saved})


@app.route("/api/community/users")
@login_required
def get_community_users():
    """Directory of other registered users, for starting a private conversation."""
    user = get_current_user()
    search = request.args.get("search", "").strip()
    users = db.get_community_users(exclude_user_id=user["id"], search=search)
    return jsonify({"success": True, "users": users})


@app.route("/api/community/conversations")
@login_required
def get_conversations():
    """List this user's private conversation threads, most recent first."""
    user = get_current_user()
    conversations = db.get_conversations(user_id=user["id"])
    return jsonify({"success": True, "conversations": conversations})


@app.route("/api/community/dm/<int:other_user_id>")
@login_required
def get_direct_messages(other_user_id):
    """Fetch a private thread with another user. Also marks their messages as read."""
    user = get_current_user()
    if other_user_id == user["id"]:
        return jsonify({"success": False, "error": "Cannot message yourself."}), 400

    other_user = db.get_user_by_id(other_user_id)
    if not other_user:
        return jsonify({"success": False, "error": "User not found."}), 404

    after_id = request.args.get("after_id", type=int)
    limit = min(request.args.get("limit", 100, type=int) or 100, 200)
    messages = db.get_direct_messages(user_id=user["id"], other_user_id=other_user_id, after_id=after_id, limit=limit)
    return jsonify({"success": True, "messages": messages, "other_username": other_user["username"]})


@app.route("/api/community/dm/<int:other_user_id>", methods=["POST"])
@login_required
def send_direct_message(other_user_id):
    """Send a private message to another registered user."""
    user = get_current_user()
    if other_user_id == user["id"]:
        return jsonify({"success": False, "error": "Cannot message yourself."}), 400

    other_user = db.get_user_by_id(other_user_id)
    if not other_user:
        return jsonify({"success": False, "error": "User not found."}), 404

    payload = request.get_json() or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"success": False, "error": f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)."}), 400

    saved = db.send_direct_message(sender_id=user["id"], recipient_id=other_user_id, message=message)
    if not saved:
        return jsonify({"success": False, "error": "Failed to send message."}), 500
    return jsonify({"success": True, "message_data": saved})


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"🚀 Brainfreeze Algos & RBAC Auth running on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug_mode, threaded=True)

