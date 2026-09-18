-- =============================================================================
-- BRAINFREEZE ALGOS: Supabase PostgreSQL Schema & Security Policies
-- =============================================================================
-- Instructions: Run this entire SQL script inside your Supabase project:
-- Dashboard -> SQL Editor -> New query -> Paste & Run
-- =============================================================================

-- Enable uuid-ossp extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (Authentication, RBAC & Profile Handles)
CREATE TABLE IF NOT EXISTS public.users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    leetcode_user TEXT DEFAULT '',
    codechef_user TEXT DEFAULT '',
    codeforces_user TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    last_login TEXT
);

-- Index for fast user authentication lookups
CREATE INDEX IF NOT EXISTS idx_users_username_lower ON public.users (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON public.users (LOWER(email));

-- 2. Problem Progress Table (User-scoped problem solving status)
CREATE TABLE IF NOT EXISTS public.problem_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    problem_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unsolved' CHECK (status IN ('unsolved', 'attempted', 'solved')),
    solved_at TEXT,
    attempts_count INTEGER DEFAULT 0,
    last_code TEXT,
    notes TEXT,
    is_bookmarked INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    CONSTRAINT uq_user_problem UNIQUE (user_id, problem_id)
);

CREATE INDEX IF NOT EXISTS idx_progress_user_id ON public.problem_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_status ON public.problem_progress(user_id, status);

-- 3. Submissions Log Table (Code evaluations, runtime telemetry)
CREATE TABLE IF NOT EXISTS public.submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    problem_id TEXT NOT NULL,
    code TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_time_ms REAL DEFAULT 0.0,
    tests_passed INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON public.submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON public.submissions(user_id, created_at DESC);

-- 4. Daily Activity Table (Heatmap & Practice Streaks)
CREATE TABLE IF NOT EXISTS public.daily_activity (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    date TEXT NOT NULL, -- YYYY-MM-DD
    problems_solved_count INTEGER DEFAULT 0,
    submissions_count INTEGER DEFAULT 0,
    CONSTRAINT uq_user_date UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_activity_user_date ON public.daily_activity(user_id, date);

-- 5. Mock Interviews Table (Technical Round Sessions, Candidate Intake & Scorecards)
CREATE TABLE IF NOT EXISTS public.mock_interviews (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    target_company TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    focus_skills TEXT NOT NULL,
    qualification TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    problem_title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'timed_out', 'abandoned')),
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
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_mock_interviews_user_id ON public.mock_interviews(user_id);
CREATE INDEX IF NOT EXISTS idx_mock_interviews_created_at ON public.mock_interviews(user_id, created_at DESC);

-- 6. Row Level Security (RLS) Policies for Backend API Access
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mock_interviews ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow backend access to users" ON public.users;
CREATE POLICY "Allow backend access to users" ON public.users FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow backend access to problem_progress" ON public.problem_progress;
CREATE POLICY "Allow backend access to problem_progress" ON public.problem_progress FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow backend access to submissions" ON public.submissions;
CREATE POLICY "Allow backend access to submissions" ON public.submissions FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow backend access to daily_activity" ON public.daily_activity;
CREATE POLICY "Allow backend access to daily_activity" ON public.daily_activity FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow backend access to mock_interviews" ON public.mock_interviews;
CREATE POLICY "Allow backend access to mock_interviews" ON public.mock_interviews FOR ALL USING (true) WITH CHECK (true);

-- 7. User Notion Integrations (Encrypted Multi-Tenant Storage)
CREATE TABLE IF NOT EXISTS public.user_notion_integrations (
    user_id BIGINT PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    notion_token_encrypted TEXT NOT NULL,
    workspace_name TEXT DEFAULT 'Personal Workspace',
    workspace_icon TEXT DEFAULT '',
    bot_id TEXT DEFAULT '',
    problems_database_id TEXT DEFAULT '',
    scorecards_database_id TEXT DEFAULT '',
    auto_sync_enabled BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    updated_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

ALTER TABLE public.user_notion_integrations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow backend access to user_notion_integrations" ON public.user_notion_integrations;
CREATE POLICY "Allow backend access to user_notion_integrations" ON public.user_notion_integrations FOR ALL USING (true) WITH CHECK (true);

-- 8. Seed Default Admin Account (password: admin123)
-- (Only inserts if admin account does not already exist)
INSERT INTO public.users (username, email, password_hash, role, created_at)
VALUES (
    'admin',
    'admin@brainfreezealgos.io',
    'scrypt:32768:8:1$j4tP9hZ1O3dC0h7U$4793f773668352ea93e4334f59cfa5629c49c7198bb6fbbbfec0bceba05273a55fb12b5b3be79dbd00fb8a9d0335e39626c116d4001a1c97a8e23f0545f1bce8',
    'admin',
    to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
)
ON CONFLICT (username) DO NOTHING;

-- 9. Community Public Chat Messages (single global room)
CREATE TABLE IF NOT EXISTS public.community_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE INDEX IF NOT EXISTS idx_community_messages_id ON public.community_messages(id DESC);

ALTER TABLE public.community_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow backend access to community_messages" ON public.community_messages;
CREATE POLICY "Allow backend access to community_messages" ON public.community_messages FOR ALL USING (true) WITH CHECK (true);

-- 10. Direct (Private) Messages between two users
CREATE TABLE IF NOT EXISTS public.direct_messages (
    id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    read_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_dm_participants ON public.direct_messages(sender_id, recipient_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_dm_recipient_unread ON public.direct_messages(recipient_id, read_at);

ALTER TABLE public.direct_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow backend access to direct_messages" ON public.direct_messages;
CREATE POLICY "Allow backend access to direct_messages" ON public.direct_messages FOR ALL USING (true) WITH CHECK (true);

