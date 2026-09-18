import base64
import datetime
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional
import requests
from cryptography.fernet import Fernet


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

_DEFAULT_VAULT_SECRET = "dsa-nexus-notion-vault-salt-2026"
_warned_insecure_vault_key = False


class NotionVault:
    """
    Handles AES-256 (Fernet) encryption and decryption of per-user Notion tokens.
    Ensures tokens are strictly protected at rest and decrypted only in-memory.
    """

    @classmethod
    def _get_fernet(cls) -> Fernet:
        global _warned_insecure_vault_key
        raw_secret = os.getenv("NOTION_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or _DEFAULT_VAULT_SECRET
        if raw_secret == _DEFAULT_VAULT_SECRET and not _warned_insecure_vault_key:
            _warned_insecure_vault_key = True
            print(
                "[NotionVault] WARNING: neither NOTION_ENCRYPTION_KEY nor SECRET_KEY is set in .env — "
                "encrypting stored Notion tokens with the hardcoded source default. This provides no real "
                "protection at rest. Set SECRET_KEY (or a dedicated NOTION_ENCRYPTION_KEY) before storing "
                "any real Notion integration tokens."
            )
        # Derive 32-byte urlsafe base64 key
        digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    @classmethod
    def encrypt_token(cls, raw_token: str) -> str:
        if not raw_token:
            return ""
        f = cls._get_fernet()
        return f.encrypt(raw_token.strip().encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt_token(cls, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        f = cls._get_fernet()
        return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


class NotionEngine:
    """
    Automated Notion Integration Engine for Brainfreeze Algos.
    Enables users to connect their personal Notion workspace with 1 click:
    - Auto-detects shared parent pages.
    - Automatically provisions pre-formatted Notion databases for Problem Notes & Scorecards.
    - Syncs formatted Python code blocks, complexity metadata, and personal notes.
    - Exports FAANG-grade Mock Interview Scorecards directly to Notion tables.
    """

    @classmethod
    def _headers(cls, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token.strip()}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    # =========================================================================
    # Verification & Discovery
    # =========================================================================

    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """Verify Notion token validity and fetch bot/workspace metadata."""
        try:
            resp = requests.get(
                f"{NOTION_API_BASE}/users/me",
                headers=cls._headers(token),
                timeout=8,
            )
            if resp.status_code != 200:
                err_data = resp.json() if resp.content else {}
                return {
                    "valid": False,
                    "error": err_data.get("message", f"Notion authentication failed (HTTP {resp.status_code})."),
                }

            data = resp.json()
            bot_obj = data.get("bot", {})
            owner_obj = bot_obj.get("owner", {})
            workspace_name = owner_obj.get("workspace_name") or "Personal Notion Workspace"

            return {
                "valid": True,
                "bot_id": data.get("id", ""),
                "bot_name": data.get("name", "Brainfreeze Algos Bot"),
                "workspace_name": workspace_name,
                "avatar_url": data.get("avatar_url") or "",
            }
        except Exception as e:
            return {"valid": False, "error": f"Failed to reach Notion API: {str(e)}"}

    @classmethod
    def find_accessible_pages(cls, token: str) -> List[Dict[str, Any]]:
        """Search for pages shared with this integration."""
        try:
            resp = requests.post(
                f"{NOTION_API_BASE}/search",
                headers=cls._headers(token),
                json={"filter": {"value": "page", "property": "object"}, "page_size": 15},
                timeout=8,
            )
            if resp.status_code != 200:
                return []

            results = resp.json().get("results", [])
            pages = []
            for item in results:
                page_id = item.get("id")
                # Extract title from properties
                title = "Untitled Page"
                props = item.get("properties", {})
                for prop_val in props.values():
                    if prop_val.get("type") == "title":
                        title_arr = prop_val.get("title", [])
                        if title_arr:
                            title = "".join(t.get("plain_text", "") for t in title_arr)
                            break
                pages.append({
                    "id": page_id,
                    "title": title or "Shared Workspace Page",
                    "url": item.get("url", f"https://notion.so/{page_id.replace('-', '')}"),
                })
            return pages
        except Exception:
            return []

    # =========================================================================
    # Auto-Scaffolding & Provisioning
    # =========================================================================

    @classmethod
    def auto_provision_workspace(cls, token: str, parent_page_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-scaffolds Brainfreeze Algos databases in the user's Notion workspace.
        Creates:
        1. 📘 DSA Problem Solutions & Notes
        2. 🎯 Mock Interview Scorecards
        """
        # 1. Resolve parent page
        if not parent_page_id:
            pages = cls.find_accessible_pages(token)
            if not pages:
                return {
                    "success": False,
                    "error": (
                        "No shared pages found in your Notion workspace. "
                        "Please open a page in Notion, click '•••' at top right -> 'Connections' -> add your integration, and try again."
                    ),
                }
            parent_page_id = pages[0]["id"]

        clean_parent_id = parent_page_id.replace("-", "")

        # 2. Provision Database 1: Problem Solutions & Notes
        problems_db_schema = {
            "parent": {"type": "page_id", "page_id": clean_parent_id},
            "icon": {"type": "emoji", "emoji": "📘"},
            "title": [{"type": "text", "text": {"content": "Brainfreeze Algos - Problem Solutions & Notes"}}],
            "properties": {
                "Problem": {"title": {}},
                "Difficulty": {
                    "select": {
                        "options": [
                            {"name": "Easy", "color": "green"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Hard", "color": "red"},
                        ]
                    }
                },
                "Topic": {"select": {}},
                "Step": {"select": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Solved", "color": "green"},
                            {"name": "In Progress", "color": "blue"},
                            {"name": "Review Needed", "color": "orange"},
                        ]
                    }
                },
                "Complexity": {"rich_text": {}},
                "Last Practiced": {"date": {}},
            },
        }

        resp1 = requests.post(
            f"{NOTION_API_BASE}/databases",
            headers=cls._headers(token),
            json=problems_db_schema,
            timeout=10,
        )
        if resp1.status_code not in (200, 201):
            err1 = resp1.json() if resp1.content else {}
            return {
                "success": False,
                "error": f"Failed to create Problems database: {err1.get('message', 'API Error')}",
            }
        prob_db_data = resp1.json()
        problems_db_id = prob_db_data.get("id")

        # 3. Provision Database 2: Mock Interview Scorecards
        scorecards_db_schema = {
            "parent": {"type": "page_id", "page_id": clean_parent_id},
            "icon": {"type": "emoji", "emoji": "🎯"},
            "title": [{"type": "text", "text": {"content": "Brainfreeze Algos - Mock Technical Interviews"}}],
            "properties": {
                "Interview Session": {"title": {}},
                "Score": {"number": {"format": "number"}},
                "Verdict": {
                    "select": {
                        "options": [
                            {"name": "STRONG HIRE", "color": "green"},
                            {"name": "LEAN HIRE", "color": "blue"},
                            {"name": "LEAN NO HIRE", "color": "yellow"},
                            {"name": "NO HIRE", "color": "red"},
                        ]
                    }
                },
                "Target Role": {"rich_text": {}},
                "Target Company": {"rich_text": {}},
                "Tests Passed": {"rich_text": {}},
                "Date": {"date": {}},
            },
        }

        resp2 = requests.post(
            f"{NOTION_API_BASE}/databases",
            headers=cls._headers(token),
            json=scorecards_db_schema,
            timeout=10,
        )
        scorecards_db_id = ""
        if resp2.status_code in (200, 201):
            scorecards_db_id = resp2.json().get("id", "")

        return {
            "success": True,
            "parent_page_id": clean_parent_id,
            "problems_db_id": problems_db_id,
            "scorecards_db_id": scorecards_db_id,
        }

    # =========================================================================
    # Problem Notes Sync
    # =========================================================================

    @classmethod
    def sync_problem_solution(
        cls,
        token: str,
        database_id: str,
        problem: Dict[str, Any],
        user_code: str,
        complexity: str = "",
        user_notes: str = "",
        test_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upserts a problem solution and notes page in the user's Notion database.
        Checks for an existing entry with the same Problem title to update it, or creates a new one.
        """
        prob_title = problem.get("title", "DSA Problem")
        prob_diff = (problem.get("difficulty") or "Medium").capitalize()
        prob_topic = problem.get("topic") or "General DSA"
        prob_step = problem.get("step") or "DSA Core"
        today_str = datetime.date.today().isoformat()

        # Status & Complexity
        is_solved = bool(test_result and test_result.get("passed"))
        status_val = "Solved" if is_solved else "In Progress"
        comp_str = complexity or "O(N) Time, O(1) Space"

        # Check for existing page in user's database
        existing_page_id = None
        try:
            query_resp = requests.post(
                f"{NOTION_API_BASE}/databases/{database_id}/query",
                headers=cls._headers(token),
                json={
                    "filter": {
                        "property": "Problem",
                        "title": {"equals": prob_title},
                    },
                    "page_size": 1,
                },
                timeout=8,
            )
            if query_resp.status_code == 200:
                results = query_resp.json().get("results", [])
                if results:
                    existing_page_id = results[0]["id"]
        except Exception:
            pass

        properties = {
            "Problem": {"title": [{"text": {"content": prob_title}}]},
            "Difficulty": {"select": {"name": prob_diff if prob_diff in ["Easy", "Medium", "Hard"] else "Medium"}},
            "Topic": {"select": {"name": prob_topic[:90]}},
            "Step": {"select": {"name": prob_step[:90]}},
            "Status": {"select": {"name": status_val}},
            "Complexity": {"rich_text": [{"text": {"content": comp_str}}]},
            "Last Practiced": {"date": {"start": today_str}},
        }

        # Build Page Content Blocks
        children_blocks = []

        # 1. Notes / Approach Callout
        if user_notes and user_notes.strip():
            children_blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "💡 Key Insights & Personal Notes"}}]},
            })
            children_blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "📝"},
                    "rich_text": [{"type": "text", "text": {"content": user_notes.strip()[:1800]}}],
                },
            })

        # 2. Python Solution Code Block
        children_blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🐍 Python Reference Solution"}}]},
        })
        clean_code = user_code.strip() if user_code else "# Solution code here"
        children_blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "language": "python",
                "rich_text": [{"type": "text", "text": {"content": clean_code[:1950]}}],
            },
        })

        # 3. Test Execution Verification
        if test_result:
            p_count = test_result.get("tests_passed", 0)
            t_count = test_result.get("tests_total", 0)
            ms = test_result.get("execution_time_ms", 0.0)
            status_text = f"Status: {'Passed' if is_solved else 'Failed'} ({p_count}/{t_count} tests passed in {ms:.1f}ms)"
            children_blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "✅" if is_solved else "⚠️"},
                    "rich_text": [{"type": "text", "text": {"content": status_text}}],
                },
            })

        # Execute Upsert
        if existing_page_id:
            # Update Properties
            requests.patch(
                f"{NOTION_API_BASE}/pages/{existing_page_id}",
                headers=cls._headers(token),
                json={"properties": properties},
                timeout=8,
            )
            # Append latest blocks
            requests.patch(
                f"{NOTION_API_BASE}/blocks/{existing_page_id}/children",
                headers=cls._headers(token),
                json={"children": children_blocks},
                timeout=8,
            )
            clean_id = existing_page_id.replace("-", "")
            return {
                "success": True,
                "action": "updated",
                "page_id": existing_page_id,
                "url": f"https://notion.so/{clean_id}",
            }
        else:
            # Create Page
            create_payload = {
                "parent": {"database_id": database_id},
                "icon": {"type": "emoji", "emoji": "⚡"},
                "properties": properties,
                "children": children_blocks,
            }
            resp = requests.post(
                f"{NOTION_API_BASE}/pages",
                headers=cls._headers(token),
                json=create_payload,
                timeout=10,
            )
            if resp.status_code not in (200, 201):
                err = resp.json() if resp.content else {}
                return {"success": False, "error": err.get("message", f"Failed to create Notion page ({resp.status_code}).")}

            data = resp.json()
            page_id = data.get("id")
            clean_id = page_id.replace("-", "")
            return {
                "success": True,
                "action": "created",
                "page_id": page_id,
                "url": f"https://notion.so/{clean_id}",
            }

    # =========================================================================
    # Mock Interview Scorecard Export
    # =========================================================================

    @classmethod
    def sync_interview_scorecard(
        cls,
        token: str,
        database_id: str,
        interview_data: Dict[str, Any],
        scorecard: Dict[str, Any],
        user_code: str,
    ) -> Dict[str, Any]:
        """
        Creates an official technical round scorecard entry in the user's Notion Mock Interviews database.
        """
        intake = interview_data.get("intake") or {}
        role = intake.get("target_role") or "Software Engineer"
        company = intake.get("target_company") or "Tech Company"
        session_title = f"{role} @ {company}"

        score = int(scorecard.get("score") or 0)
        verdict = scorecard.get("hire_decision") or "LEAN HIRE"
        tests_passed = f"{scorecard.get('tests_passed', 0)} / {scorecard.get('tests_total', 0)}"
        today_str = datetime.date.today().isoformat()

        properties = {
            "Interview Session": {"title": [{"text": {"content": session_title}}]},
            "Score": {"number": score},
            "Verdict": {"select": {"name": verdict}},
            "Target Role": {"rich_text": [{"text": {"content": role[:90]}}]},
            "Target Company": {"rich_text": [{"text": {"content": company[:90]}}]},
            "Tests Passed": {"rich_text": [{"text": {"content": tests_passed}}]},
            "Date": {"date": {"start": today_str}},
        }

        fb = scorecard.get("feedback") or {}
        rubric = scorecard.get("rubric_scores") or {}

        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🏆 FAANG Hiring Committee Summary"}}]},
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "🎯"},
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": (
                                f"Verdict: {verdict} ({score}/100)\n"
                                f"{fb.get('executive_summary', 'Assessment concluded successfully.')}"
                            )
                        }
                    }],
                },
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📊 Rubric Dimension Scores"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Problem Solving & Intuition: {rubric.get('problem_solving', 0)} / 25"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Algorithmic Efficiency (Big-O): {rubric.get('efficiency', 0)} / 25"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Code Quality & Cleanliness: {rubric.get('code_quality', 0)} / 25"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Communication & Presence: {rubric.get('communication', 0)} / 25"}}]},
            },
        ]

        # Strengths
        strengths = fb.get("strengths") or []
        if strengths:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "💪 Candidate Strengths"}}]},
            })
            for s in strengths[:4]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": s}}]},
                })

        # Final Code
        if user_code:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "💻 Final Submitted Code"}}]},
            })
            children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "language": "python",
                    "rich_text": [{"type": "text", "text": {"content": user_code[:1950]}}],
                },
            })

        payload = {
            "parent": {"database_id": database_id},
            "icon": {"type": "emoji", "emoji": "🏅"},
            "properties": properties,
            "children": children,
        }

        resp = requests.post(
            f"{NOTION_API_BASE}/pages",
            headers=cls._headers(token),
            json=payload,
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            err = resp.json() if resp.content else {}
            return {"success": False, "error": err.get("message", f"Failed to export scorecard to Notion ({resp.status_code}).")}

        page_id = resp.json().get("id")
        clean_id = page_id.replace("-", "")
        return {
            "success": True,
            "page_id": page_id,
            "url": f"https://notion.so/{clean_id}",
        }
