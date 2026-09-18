import logging
from typing import Any, Dict, List, Optional, Set
import requests

logger = logging.getLogger(__name__)


class CodeforcesClient:
    """Client for fetching statistics from the official Codeforces REST API."""

    BASE_URL = "https://codeforces.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def get_user_profile(self, handle: str) -> Dict[str, Any]:
        """Fetch user info, solved problems count, and contest rating history."""
        handle = handle.strip()
        if not handle:
            raise ValueError("Handle cannot be empty")

        # 1. Fetch User Info
        info_url = f"{self.BASE_URL}/user.info?handles={handle}"
        try:
            resp = self.session.get(info_url, timeout=10)
            data = resp.json()
            if data.get("status") != "OK" or not data.get("result"):
                raise ValueError(f"Codeforces user '{handle}' not found.")
            user_info = data["result"][0]
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to Codeforces API: {e}") from e

        # 2. Fetch User Rating History
        rating_history: List[Dict[str, Any]] = []
        try:
            rating_url = f"{self.BASE_URL}/user.rating?handle={handle}"
            r_resp = self.session.get(rating_url, timeout=10)
            r_data = r_resp.json()
            if r_data.get("status") == "OK":
                for item in r_data.get("result", []):
                    rating_history.append({
                        "contest_id": item.get("contestId"),
                        "contest_name": item.get("contestName"),
                        "rank": item.get("rank"),
                        "old_rating": item.get("oldRating"),
                        "new_rating": item.get("newRating"),
                    })
        except Exception:
            pass

        # 3. Fetch Solved Submissions (Unique Solved Problems)
        solved_problems: Set[str] = set()
        recent_solved: List[Dict[str, Any]] = []
        try:
            status_url = f"{self.BASE_URL}/user.status?handle={handle}&from=1&count=100"
            s_resp = self.session.get(status_url, timeout=10)
            s_data = s_resp.json()
            if s_data.get("status") == "OK":
                for sub in s_data.get("result", []):
                    verdict = sub.get("verdict")
                    prob = sub.get("problem", {})
                    contest_id = prob.get("contestId")
                    index = prob.get("index")
                    name = prob.get("name")
                    if contest_id and index and name:
                        prob_key = f"{contest_id}{index}"
                        if verdict == "OK":
                            if prob_key not in solved_problems:
                                solved_problems.add(prob_key)
                                if len(recent_solved) < 8:
                                    recent_solved.append({
                                        "name": name,
                                        "rating": prob.get("rating", "N/A"),
                                        "tags": prob.get("tags", []),
                                        "link": f"https://codeforces.com/contest/{contest_id}/problem/{index}",
                                    })
        except Exception:
            pass

        first_name = user_info.get("firstName", "")
        last_name = user_info.get("lastName", "")
        full_name = f"{first_name} {last_name}".strip() or handle

        avatar = user_info.get("titlePhoto") or user_info.get("avatar") or ""
        if avatar.startswith("//"):
            avatar = f"https:{avatar}"

        return {
            "platform": "codeforces",
            "username": handle,
            "name": full_name,
            "avatar": avatar,
            "rating": user_info.get("rating", 0),
            "max_rating": user_info.get("maxRating", 0),
            "rank": (user_info.get("rank") or "unrated").title(),
            "max_rank": (user_info.get("maxRank") or "unrated").title(),
            "country": user_info.get("country", "Global"),
            "city": user_info.get("city", "N/A"),
            "organization": user_info.get("organization", "N/A"),
            "contribution": user_info.get("contribution", 0),
            "friend_of_count": user_info.get("friendOfCount", 0),
            "total_solved": len(solved_problems),
            "contests_count": len(rating_history),
            "contest_history": rating_history[-10:],
            "recent_solved": recent_solved,
            "profile_url": f"https://codeforces.com/profile/{handle}",
        }
