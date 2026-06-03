"""
dashboard.py
------------
Interactive Streamlit dashboard for the YouTube Trend Analyzer.

Features:
  - KPI cards: total videos, total views, avg sentiment, top category
  - Sidebar filters: country, category, date range, sentiment
  - Sentiment by category (bar chart)
  - Top channels by total views (bar chart)
  - Daily sentiment trend (line chart)
  - Category distribution (pie chart)
  - Trending keywords from video titles (bar chart)
  - Full searchable & filterable video table

Usage:
    streamlit run scripts/dashboard.py
"""

import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from database import get_engine, ensure_schema, load_all

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "YouTube Trend Analyzer",
    page_icon  = "📺",
    layout     = "wide",
)

# ── Colour palette ─────────────────────────────────────────────────────────────
POSITIVE_COLOR = "#2ecc71"
NEUTRAL_COLOR  = "#f39c12"
NEGATIVE_COLOR = "#e74c3c"
YOUTUBE_RED    = "#FF0000"

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "this","that","these","those","i","you","he","she","it","we","they","my",
    "your","his","her","its","our","their","me","him","us","them","what","how",
    "when","where","why","who","which","all","just","not","no","so","up","out",
    "if","about","from","by","as","into","through","than","then","more","also",
    "new","get","got","via","s","ep","ft","official","video","full","episode",
    "part","season","vs","amp","1","2","3","4","5","2024","2025","2026",
}


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_db_engine():
    engine = get_engine()
    ensure_schema(engine)
    return engine


@st.cache_data(ttl=120)
def load_data() -> pd.DataFrame:
    engine = get_db_engine()
    df = load_all(engine)
    if df.empty:
        return df
    df["fetched_date"]  = pd.to_datetime(df["fetched_date"])
    df["view_count"]    = pd.to_numeric(df["view_count"],    errors="coerce").fillna(0).astype(int)
    df["like_count"]    = pd.to_numeric(df["like_count"],    errors="coerce").fillna(0).astype(int)
    df["comment_count"] = pd.to_numeric(df["comment_count"], errors="coerce").fillna(0).astype(int)
    return df


def extract_keywords(titles: pd.Series, top_n: int = 15) -> pd.DataFrame:
    """Extract the most frequent meaningful words from a series of titles."""
    words = []
    for title in titles.dropna():
        tokens = re.findall(r"[a-zA-Z]{3,}", title.lower())
        words.extend([w for w in tokens if w not in STOPWORDS])
    counts = Counter(words).most_common(top_n)
    return pd.DataFrame(counts, columns=["keyword", "count"])


# ── App ────────────────────────────────────────────────────────────────────────
st.title("📺 YouTube Trend Analyzer")
st.caption(
    f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
    "Auto-refreshes every 2 min"
)

df_raw = load_data()

if df_raw.empty:
    st.warning(
        "No data yet — run the pipeline first:  "
        "`python scripts/pipeline.py`"
    )
    st.stop()

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# Country
countries = ["All"] + sorted(df_raw["country"].unique().tolist())
sel_country = st.sidebar.selectbox("Country", countries)

# Category
categories = ["All"] + sorted(df_raw["category_name"].dropna().unique().tolist())
sel_category = st.sidebar.selectbox("Category", categories)

# Date range
min_date = df_raw["fetched_date"].min().date()
max_date = df_raw["fetched_date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(max(min_date, max_date - timedelta(days=30)), max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Sentiment
sel_sentiment = st.sidebar.multiselect(
    "Sentiment",
    options=["Positive", "Neutral", "Negative"],
    default=["Positive", "Neutral", "Negative"],
)

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ── Apply filters ──────────────────────────────────────────────────────────────
df = df_raw.copy()
if sel_country   != "All":
    df = df[df["country"] == sel_country]
if sel_category  != "All":
    df = df[df["category_name"] == sel_category]
if sel_sentiment:
    df = df[df["sentiment_label"].isin(sel_sentiment)]
df = df[
    (df["fetched_date"].dt.date >= start_date) &
    (df["fetched_date"].dt.date <= end_date)
]

if df.empty:
    st.info("No data matches the current filters.")
    st.stop()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
st.markdown("### Key Metrics")
k1, k2, k3, k4, k5 = st.columns(5)

total_videos    = len(df)
total_views     = df["view_count"].sum()
avg_sentiment   = df["sentiment_score"].mean()
top_category    = df["category_name"].value_counts().idxmax()
positive_pct    = round((df["sentiment_label"] == "Positive").mean() * 100, 1)

k1.metric("Videos Tracked",  f"{total_videos:,}")
k2.metric("Total Views",     f"{total_views / 1_000_000:.1f}M")
k3.metric("Avg Sentiment",   f"{avg_sentiment:+.3f}")
k4.metric("Top Category",    top_category)
k5.metric("Positive Titles", f"{positive_pct}%")

st.divider()

# ── Row 1: Sentiment by category + Top channels ────────────────────────────────
st.markdown("### Insights")
col1, col2 = st.columns(2)

with col1:
    sent_cat = (
        df.groupby("category_name")["sentiment_score"]
        .mean()
        .reset_index()
        .sort_values("sentiment_score", ascending=True)
        .rename(columns={"category_name": "Category", "sentiment_score": "Avg Sentiment"})
    )
    fig_sent = px.bar(
        sent_cat, x="Avg Sentiment", y="Category", orientation="h",
        title="Avg Sentiment Score by Category",
        color="Avg Sentiment",
        color_continuous_scale=["#e74c3c", "#f39c12", "#2ecc71"],
        range_color=[-0.5, 0.5],
    )
    fig_sent.update_layout(coloraxis_showscale=False, height=380)
    st.plotly_chart(fig_sent, use_container_width=True)

with col2:
    top_channels = (
        df.groupby("channel_title")["view_count"]
        .sum()
        .reset_index()
        .sort_values("view_count", ascending=False)
        .head(10)
        .rename(columns={"channel_title": "Channel", "view_count": "Total Views"})
    )
    top_channels["Total Views (M)"] = (top_channels["Total Views"] / 1_000_000).round(2)
    fig_ch = px.bar(
        top_channels, x="Total Views (M)", y="Channel", orientation="h",
        title="Top 10 Channels by Total Views",
        color="Total Views (M)", color_continuous_scale="Reds",
    )
    fig_ch.update_layout(coloraxis_showscale=False, height=380, yaxis={"autorange": "reversed"})
    st.plotly_chart(fig_ch, use_container_width=True)

# ── Row 2: Daily trend + Category distribution ─────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    daily = (
        df.groupby(["fetched_date", "sentiment_label"])
        .size()
        .reset_index(name="count")
    )
    fig_trend = px.line(
        daily, x="fetched_date", y="count", color="sentiment_label",
        title="Daily Video Count by Sentiment",
        markers=True,
        color_discrete_map={
            "Positive": POSITIVE_COLOR,
            "Neutral":  NEUTRAL_COLOR,
            "Negative": NEGATIVE_COLOR,
        },
    )
    fig_trend.update_layout(height=350, xaxis_title="Date", yaxis_title="Videos")
    st.plotly_chart(fig_trend, use_container_width=True)

with col4:
    cat_dist = df["category_name"].value_counts().reset_index()
    cat_dist.columns = ["Category", "Count"]
    fig_pie = px.pie(
        cat_dist, names="Category", values="Count",
        title="Video Distribution by Category",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig_pie.update_layout(height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Row 3: Trending keywords ───────────────────────────────────────────────────
st.markdown("### Trending Keywords in Video Titles")
kw_df = extract_keywords(df["title"])
if not kw_df.empty:
    fig_kw = px.bar(
        kw_df, x="count", y="keyword", orientation="h",
        title=f"Top {len(kw_df)} Keywords",
        color="count",
        color_continuous_scale="Blues",
    )
    fig_kw.update_layout(coloraxis_showscale=False, height=400,
                         yaxis={"autorange": "reversed"})
    st.plotly_chart(fig_kw, use_container_width=True)

st.divider()

# ── Row 4: Video table ─────────────────────────────────────────────────────────
st.markdown("### Video Explorer")
search = st.text_input("Search titles or channels", placeholder="e.g. cricket, music, news...")

display_cols = ["title", "channel_title", "category_name", "country",
                "view_count", "like_count", "sentiment_label",
                "sentiment_score", "fetched_date"]

table_df = df[display_cols].copy()
table_df["fetched_date"] = table_df["fetched_date"].dt.strftime("%Y-%m-%d")
table_df = table_df.sort_values("view_count", ascending=False)

if search:
    mask = (
        table_df["title"].str.contains(search, case=False, na=False) |
        table_df["channel_title"].str.contains(search, case=False, na=False)
    )
    table_df = table_df[mask]

st.dataframe(
    table_df.rename(columns={
        "title":          "Title",
        "channel_title":  "Channel",
        "category_name":  "Category",
        "country":        "Country",
        "view_count":     "Views",
        "like_count":     "Likes",
        "sentiment_label":"Sentiment",
        "sentiment_score":"Score",
        "fetched_date":   "Date",
    }),
    use_container_width=True,
    height=400,
)

st.caption(f"Showing {len(table_df):,} of {len(df):,} videos")
