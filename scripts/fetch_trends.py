"""
fetch_trends.py
---------------
Fetches the top 50 trending YouTube videos per country using the
YouTube Data API v3 and returns structured records ready for the database.

API quota: ~3 units per call x 3 countries = ~9 units/day
(free quota is 10,000 units/day — well within limits)

Countries tracked: US (United States), IN (India), GB (Great Britain)
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
API_KEY   = os.getenv("YOUTUBE_API_KEY")
COUNTRIES = ["US", "IN", "GB"]

CATEGORY_MAP = {
    "1":  "Film & Animation",
    "2":  "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


def _safe_int(value, default=0) -> int:
    """Convert a string to int safely, returning default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_trending(country: str, youtube) -> list[dict]:
    """
    Fetch the top 50 trending videos for a given country code.
    Returns a list of dicts, one per video.
    """
    try:
        response = youtube.videos().list(
            part        = "snippet,statistics",
            chart       = "mostPopular",
            regionCode  = country,
            maxResults  = 50,
            hl          = "en",
        ).execute()
    except HttpError as e:
        print(f"  [!] API error for {country}: {e}")
        return []

    records = []
    fetched_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for item in response.get("items", []):
        snippet    = item.get("snippet", {})
        stats      = item.get("statistics", {})
        cat_id     = snippet.get("categoryId", "")

        records.append({
            "video_id":      item["id"],
            "title":         snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id":    snippet.get("channelId", ""),
            "category_id":   cat_id,
            "category_name": CATEGORY_MAP.get(cat_id, "Other"),
            "country":       country,
            "published_at":  snippet.get("publishedAt", ""),
            "fetched_date":  fetched_date,
            "view_count":    _safe_int(stats.get("viewCount")),
            "like_count":    _safe_int(stats.get("likeCount")),
            "comment_count": _safe_int(stats.get("commentCount")),
            "description":   snippet.get("description", "")[:500],
            "tags":          ",".join(snippet.get("tags", [])[:20]),
            "thumbnail_url": snippet.get("thumbnails", {})
                                     .get("medium", {})
                                     .get("url", ""),
        })

    return records


def fetch_all() -> list[dict]:
    """Fetch trending videos for all countries and return combined records."""
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY not set in .env")

    youtube  = build("youtube", "v3", developerKey=API_KEY, cache_discovery=False)
    all_recs = []

    for country in COUNTRIES:
        print(f"  Fetching trends for {country}...")
        recs = fetch_trending(country, youtube)
        all_recs.extend(recs)
        print(f"    -> {len(recs)} videos fetched")

    print(f"  Total: {len(all_recs)} videos across {len(COUNTRIES)} countries")
    return all_recs


if __name__ == "__main__":
    records = fetch_all()
    print("\nSample record:")
    if records:
        for k, v in list(records[0].items())[:8]:
            print(f"  {k}: {v}")
