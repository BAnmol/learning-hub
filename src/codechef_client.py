import json
import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
try:
    from curl_cffi import requests
except ImportError:
    import requests

logger = logging.getLogger(__name__)



class CodeChefClient:
    """Scrapes and parses public profile data from CodeChef."""

    BASE_URL = "https://www.codechef.com/users"

    def __init__(self):
        pass

    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """Fetch complete profile, rating, stars, division, and contests from CodeChef."""
        username = username.strip()
        if not username:
            raise ValueError("Username cannot be empty")

        url = f"{self.BASE_URL}/{username}"
        try:
            resp = requests.get(
                url,
                impersonate="chrome120",
                timeout=15,
                headers={"Accept-Language": "en-US,en;q=0.9"},
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to CodeChef: {e}") from e

        if resp.status_code == 404:
            raise ValueError(f"CodeChef user '{username}' not found.")
        elif resp.status_code != 200:
            raise ConnectionError(f"CodeChef returned status {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")

        # Real Name & Avatar
        name_el = soup.find("h1", class_="h2-style") or soup.find("div", class_="user-details-container")
        name = name_el.get_text(strip=True) if name_el else username

        avatar_el = soup.find("div", class_="user-details-container")
        avatar_url = "https://cdn.codechef.com/sites/all/themes/abessive/images/user_default_thumb.jpg"
        if avatar_el:
            img = avatar_el.find("img")
            if img and img.get("src"):
                avatar_url = img.get("src")
                if avatar_url.startswith("/"):
                    avatar_url = f"https://www.codechef.com{avatar_url}"

        # Rating Number
        rating_el = soup.find("div", class_="rating-number")
        try:
            rating = int(rating_el.get_text(strip=True)) if rating_el else 0
        except ValueError:
            rating = 0

        # Stars Rating
        stars_el = soup.find("div", class_="rating-star") or soup.find("span", class_="rating-star")
        stars_raw = stars_el.get_text(strip=True) if stars_el else ""
        if "★" in stars_raw:
            stars = f"{stars_raw.count('★')}★"
        else:
            # Derive stars based on CodeChef rating boundaries
            if rating >= 2500:
                stars = "7★"
            elif rating >= 2200:
                stars = "6★"
            elif rating >= 2000:
                stars = "5★"
            elif rating >= 1800:
                stars = "4★"
            elif rating >= 1600:
                stars = "3★"
            elif rating >= 1400:
                stars = "2★"
            elif rating > 0:
                stars = "1★"
            else:
                stars = "Unrated"

        # Highest Rating
        highest_rating = rating
        small_tag = soup.find("small")
        if small_tag and "Highest Rating" in small_tag.get_text():
            m = re.search(r"Highest Rating\s*(\d+)", small_tag.get_text())
            if m:
                highest_rating = int(m.group(1))

        # Division
        if rating >= 2000:
            division = "Div 1"
        elif rating >= 1600:
            division = "Div 2"
        elif rating >= 1400:
            division = "Div 3"
        elif rating > 0:
            division = "Div 4"
        else:
            division = "Unrated"

        # Global & Country Rank
        global_rank = "N/A"
        country_rank = "N/A"
        ranks_block = soup.find("div", class_="rating-ranks")
        if ranks_block:
            strongs = ranks_block.find_all("strong")
            if len(strongs) >= 1:
                global_rank = strongs[0].get_text(strip=True)
            if len(strongs) >= 2:
                country_rank = strongs[1].get_text(strip=True)

        # Country Name
        country_el = soup.find("span", class_="user-country-name")
        country = country_el.get_text(strip=True) if country_el else "Global"

        # Solved Problems Count
        fully_solved = 0
        partially_solved = 0
        problems_section = soup.find("section", class_="problems-solved")
        if problems_section:
            h5_tags = problems_section.find_all("h5")
            for h5 in h5_tags:
                txt = h5.get_text()
                if "Fully Solved" in txt or "Total Problems Solved" in txt:
                    m = re.search(r"\((\d+)\)", txt)
                    if m:
                        fully_solved = int(m.group(1))
                elif "Partially Solved" in txt:
                    m = re.search(r"\((\d+)\)", txt)
                    if m:
                        partially_solved = int(m.group(1))

        # Contest Rating History
        contest_history: List[Dict[str, Any]] = []
        m_history = re.search(r"var\s+all_rating\s*=\s*(\[.*?\]);", resp.text)
        if m_history:
            try:
                raw_history = json.loads(m_history.group(1))
                for item in raw_history:
                    contest_history.append({
                        "name": item.get("name"),
                        "code": item.get("code"),
                        "rating": item.get("rating"),
                        "rank": item.get("rank"),
                        "date": item.get("end_date") or f"{item.get('getyear')}-{item.get('getmonth')}-{item.get('getday')}",
                    })
            except Exception:
                pass

        contests_count = len(contest_history)
        if contests_count == 0:
            m_cnt = re.search(r"Contests\s*\((\d+)\)", resp.text)
            if m_cnt:
                contests_count = int(m_cnt.group(1))

        return {
            "platform": "codechef",
            "username": username,
            "name": name,
            "avatar": avatar_url,
            "rating": rating,
            "highest_rating": highest_rating,
            "stars": stars,
            "division": division,
            "global_rank": global_rank,
            "country_rank": country_rank,
            "country": country,
            "fully_solved": fully_solved,
            "partially_solved": partially_solved,
            "total_solved": fully_solved + partially_solved,
            "contests_count": contests_count,
            "contest_history": contest_history[-10:],  # Last 10 contests
            "profile_url": f"https://www.codechef.com/users/{username}",
        }
