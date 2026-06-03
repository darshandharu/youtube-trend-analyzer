"""
pipeline.py
-----------
Master pipeline runner — orchestrates the full daily workflow:

    1. Fetch trending videos from YouTube API
    2. Run sentiment analysis on titles
    3. Insert new records into SQLite
    4. Print a run summary

Usage:
    python scripts/pipeline.py
"""

import sys
import os
from datetime import datetime

# Allow running from project root or scripts/
sys.path.insert(0, os.path.dirname(__file__))

from fetch_trends      import fetch_all
from sentiment_analysis import enrich
from database           import get_engine, ensure_schema, insert_records, load_all


def run():
    start = datetime.now()
    print("=" * 55)
    print(" YouTube Trend Analyzer — Pipeline START")
    print(f" {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # ── Step 1: Fetch ──────────────────────────────────────────────────────────
    print("\n[1/3] Fetching trending videos from YouTube API...")
    records = fetch_all()
    if not records:
        print("  No records returned. Exiting.")
        return

    # ── Step 2: Sentiment ──────────────────────────────────────────────────────
    print("\n[2/3] Running sentiment analysis on titles...")
    records = enrich(records)
    pos = sum(1 for r in records if r["sentiment_label"] == "Positive")
    neu = sum(1 for r in records if r["sentiment_label"] == "Neutral")
    neg = sum(1 for r in records if r["sentiment_label"] == "Negative")
    print(f"  Positive: {pos} | Neutral: {neu} | Negative: {neg}")

    # ── Step 3: Store ──────────────────────────────────────────────────────────
    print("\n[3/3] Storing records in SQLite...")
    engine = get_engine()
    ensure_schema(engine)
    inserted = insert_records(records, engine)
    total    = len(load_all(engine))
    print(f"  New rows inserted : {inserted}")
    print(f"  Total rows in DB  : {total}")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 55}")
    print(f" Pipeline COMPLETE in {elapsed:.1f}s")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    run()
