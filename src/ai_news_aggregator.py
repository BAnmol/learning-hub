import datetime
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# cs.AI (Artificial Intelligence), cs.CL (Computation & Language / NLP), cs.LG (Machine Learning)
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]

# Algolia's HN search does plain full-text matching, not boolean "OR" syntax —
# so we run a few single-term searches and merge/dedupe rather than one
# combined query (which silently returns near-zero results).
HN_SEARCH_TERMS = ["AI", "LLM", "GPT", "machine learning", "deep learning"]


class TrendingNewsError(RuntimeError):
    """Raised when neither source could be reached — callers show this message directly."""


def fetch_trending_ai_news(limit: int = 10) -> List[Dict[str, Any]]:
    """Trending AI/ML news + research, from free, keyless, public APIs only.

    Combines the newest arXiv papers (cs.AI/cs.CL/cs.LG) with well-received
    recent Hacker News stories about AI/ML. Every item is real, fetched
    directly from its source — never model-generated — so there is no
    hallucination risk. Requires no API key and costs nothing, unlike an
    LLM-web-search approach, so it works regardless of OpenRouter credits.
    """
    papers: List[Dict[str, Any]] = []
    stories: List[Dict[str, Any]] = []

    try:
        papers = _fetch_arxiv_papers(limit=max(4, limit // 2))
    except Exception:
        pass  # fall through — we still try Hacker News

    try:
        stories = _fetch_hn_ai_stories(limit=max(4, limit // 2))
    except Exception:
        pass

    if not papers and not stories:
        raise TrendingNewsError(
            "Could not reach arXiv or Hacker News right now. Both are public "
            "APIs with no key required — this is likely a transient network "
            "issue. Try refreshing in a moment."
        )

    # Interleave research papers with industry stories rather than grouping
    # all of one type first, so the feed reads as one mixed "trending" list.
    combined: List[Dict[str, Any]] = []
    i = j = 0
    while i < len(papers) or j < len(stories):
        if i < len(papers):
            combined.append(papers[i])
            i += 1
        if j < len(stories):
            combined.append(stories[j])
            j += 1

    return combined[:limit]


def _fetch_arxiv_papers(limit: int) -> List[Dict[str, Any]]:
    query = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": limit,
    }
    resp = requests.get(ARXIV_API_URL, params=params, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    items = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip().replace("\n", " ")
        title = " ".join(title.split())
        summary = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip().replace("\n", " ")
        summary = " ".join(summary.split())
        if len(summary) > 220:
            summary = summary[:217].rstrip() + "…"
        published = (entry.findtext("atom:published", default="", namespaces=ATOM_NS) or "")[:10]

        link = ""
        for l in entry.findall("atom:link", ATOM_NS):
            if l.get("type") == "text/html" or l.get("rel") == "alternate":
                link = l.get("href", "")
                break

        if not title:
            continue
        items.append({
            "title": title,
            "source": "arXiv",
            "url": link,
            "summary": summary,
            "published": published,
        })
    return items


def _fetch_hn_ai_stories(limit: int) -> List[Dict[str, Any]]:
    since = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).timestamp())

    seen_ids = set()
    hits: List[Dict[str, Any]] = []
    for term in HN_SEARCH_TERMS:
        params = {
            "query": term,
            "tags": "story",
            "numericFilters": f"created_at_i>{since}",
            "hitsPerPage": limit,
        }
        try:
            resp = requests.get(HN_ALGOLIA_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        for hit in resp.json().get("hits", []):
            obj_id = hit.get("objectID")
            if not obj_id or obj_id in seen_ids:
                continue
            seen_ids.add(obj_id)
            hits.append(hit)

    hits.sort(key=lambda h: h.get("points") or 0, reverse=True)

    items = []
    for hit in hits[:limit]:
        title = hit.get("title") or hit.get("story_title") or ""
        if not title:
            continue
        url = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        points = hit.get("points") or 0
        comments = hit.get("num_comments") or 0
        items.append({
            "title": title,
            "source": "Hacker News",
            "url": url,
            "summary": f"{points} points, {comments} comments on Hacker News.",
            "published": (hit.get("created_at") or "")[:10],
        })
    return items
