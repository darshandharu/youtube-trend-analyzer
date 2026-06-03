"""
database.py
-----------
Handles all SQLite interactions for the YouTube Trend Analyzer.
Creates the schema on first run and provides insert/query helpers.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "trends.db")


def get_engine():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}")


def ensure_schema(engine):
    """Create tables if they do not already exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trending_videos (
                video_id        TEXT,
                title           TEXT,
                channel_title   TEXT,
                channel_id      TEXT,
                category_id     TEXT,
                category_name   TEXT,
                country         TEXT,
                published_at    TEXT,
                fetched_date    TEXT,
                view_count      INTEGER DEFAULT 0,
                like_count      INTEGER DEFAULT 0,
                comment_count   INTEGER DEFAULT 0,
                description     TEXT,
                tags            TEXT,
                thumbnail_url   TEXT,
                sentiment_score REAL    DEFAULT 0.0,
                sentiment_label TEXT    DEFAULT 'Neutral',
                PRIMARY KEY (video_id, country, fetched_date)
            )
        """))
        conn.commit()


def insert_records(records: list[dict], engine) -> int:
    """
    Insert records into trending_videos, skipping duplicates.
    Returns the number of new rows actually inserted.
    """
    if not records:
        return 0

    df = pd.DataFrame(records)

    # Use INSERT OR IGNORE via raw SQL for duplicate handling
    with engine.connect() as conn:
        inserted = 0
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT OR IGNORE INTO trending_videos
                        (video_id, title, channel_title, channel_id,
                         category_id, category_name, country,
                         published_at, fetched_date,
                         view_count, like_count, comment_count,
                         description, tags, thumbnail_url,
                         sentiment_score, sentiment_label)
                    VALUES
                        (:video_id, :title, :channel_title, :channel_id,
                         :category_id, :category_name, :country,
                         :published_at, :fetched_date,
                         :view_count, :like_count, :comment_count,
                         :description, :tags, :thumbnail_url,
                         :sentiment_score, :sentiment_label)
                """), dict(row))
                inserted += 1
            except Exception:
                pass
        conn.commit()
    return inserted


def load_all(engine) -> pd.DataFrame:
    """Load the full trending_videos table as a DataFrame."""
    return pd.read_sql("SELECT * FROM trending_videos", engine)


def load_recent(engine, days: int = 30) -> pd.DataFrame:
    """Load records from the last N days."""
    return pd.read_sql(f"""
        SELECT * FROM trending_videos
        WHERE fetched_date >= date('now', '-{days} days')
        ORDER BY fetched_date DESC
    """, engine)
