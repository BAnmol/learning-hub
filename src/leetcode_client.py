import json
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class LeetCodeClient:
    """Client for fetching user dashboard and statistics from LeetCode via GraphQL."""

    BASE_URL = "https://leetcode.com/graphql"
    HEADERS = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self, session_cookie: Optional[str] = None, csrf_token: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if session_cookie:
            self.session.cookies.set("LEETCODE_SESSION", session_cookie)
        if csrf_token:
            self.session.cookies.set("csrftoken", csrf_token)
            self.session.headers.update({"x-csrftoken": csrf_token})

    def _execute_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query against LeetCode endpoint."""
        payload = {"query": query, "variables": variables}
        try:
            response = self.session.post(self.BASE_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "errors" in data and not data.get("data"):
                error_messages = ", ".join([e.get("message", "Unknown error") for e in data["errors"]])
                raise ValueError(f"LeetCode GraphQL error: {error_messages}")
            return data.get("data", {})
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to LeetCode API: {e}") from e

    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """Fetch general user profile and problem-solving stats."""
        query = """
        query getUserProfile($username: String!) {
            allQuestionsCount {
                difficulty
                count
            }
            matchedUser(username: $username) {
                username
                githubUrl
                twitterUrl
                linkedinUrl
                profile {
                    ranking
                    userAvatar
                    realName
                    aboutMe
                    school
                    websites
                    countryName
                    company
                    jobTitle
                    skillTags
                    postViewCount
                    reputation
                    solutionCount
                }
                submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                    totalSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                }
                badges {
                    id
                    displayName
                    icon
                    creationDate
                }
                upcomingBadges {
                    name
                    icon
                }
                userCalendar {
                    streak
                    totalActiveDays
                    submissionCalendar
                }
            }
        }
        """
        data = self._execute_query(query, {"username": username})
        matched_user = data.get("matchedUser")
        if not matched_user:
            raise ValueError(f"User '{username}' not found on LeetCode.")

        all_questions = {item["difficulty"]: item["count"] for item in data.get("allQuestionsCount", [])}

        submit_stats = matched_user.get("submitStatsGlobal", {})
        ac_submissions = {
            item["difficulty"]: {
                "count": item["count"],
                "submissions": item.get("submissions", 0),
            }
            for item in submit_stats.get("acSubmissionNum", [])
        }
        total_submissions = {
            item["difficulty"]: {
                "count": item["count"],
                "submissions": item.get("submissions", 0),
            }
            for item in submit_stats.get("totalSubmissionNum", [])
        }

        # Parse submission calendar
        calendar_data = matched_user.get("userCalendar", {})
        raw_calendar = calendar_data.get("submissionCalendar", "{}")
        try:
            submission_map = json.loads(raw_calendar) if isinstance(raw_calendar, str) else raw_calendar
        except json.JSONDecodeError:
            submission_map = {}

        return {
            "username": matched_user.get("username", username),
            "profile": matched_user.get("profile", {}),
            "social": {
                "github": matched_user.get("githubUrl"),
                "twitter": matched_user.get("twitterUrl"),
                "linkedin": matched_user.get("linkedinUrl"),
            },
            "badges": matched_user.get("badges", []),
            "streak": calendar_data.get("streak", 0),
            "total_active_days": calendar_data.get("totalActiveDays", 0),
            "submission_calendar": submission_map,
            "all_questions_count": all_questions,
            "ac_submissions": ac_submissions,
            "total_submissions": total_submissions,
        }

    def get_contest_ranking(self, username: str) -> Dict[str, Any]:
        """Fetch contest ranking and contest rating history."""
        query = """
        query getUserContestRanking($username: String!) {
            userContestRanking(username: $username) {
                attendedContestsCount
                rating
                globalRanking
                totalParticipants
                topPercentage
                badge {
                    name
                }
            }
            userContestRankingHistory(username: $username) {
                attended
                trendDirection
                problemsSolved
                totalProblems
                finishTimeInSeconds
                rating
                ranking
                contest {
                    title
                    startTime
                }
            }
        }
        """
        data = self._execute_query(query, {"username": username})
        ranking_info = data.get("userContestRanking") or {}
        history = [
            h for h in data.get("userContestRankingHistory", [])
            if h.get("attended")
        ]
        return {
            "contest_info": ranking_info,
            "attended_contests": history,
        }

    def get_recent_submissions(self, username: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent accepted submissions."""
        query = """
        query getRecentSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
            }
        }
        """
        data = self._execute_query(query, {"username": username, "limit": limit})
        return data.get("recentAcSubmissionList", [])

    def get_skill_stats(self, username: str) -> Dict[str, Any]:
        """Fetch skill / topic-wise solved problem counts."""
        query = """
        query skillStats($username: String!) {
            matchedUser(username: $username) {
                tagProblemCounts {
                    advanced {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                    intermediate {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                    fundamental {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                }
            }
        }
        """
        try:
            data = self._execute_query(query, {"username": username})
            matched_user = data.get("matchedUser") or {}
            return matched_user.get("tagProblemCounts", {})
        except Exception:
            return {}

    def get_full_dashboard(self, username: str) -> Dict[str, Any]:
        """Aggregate full profile, stats, contest history, and recent submissions."""
        profile_data = self.get_user_profile(username)
        contest_data = self.get_contest_ranking(username)
        recent_submissions = self.get_recent_submissions(username, limit=10)
        skill_stats = self.get_skill_stats(username)

        return {
            **profile_data,
            "contest": contest_data,
            "recent_submissions": recent_submissions,
            "skills": skill_stats,
        }
