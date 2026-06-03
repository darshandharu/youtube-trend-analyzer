"""
generate_charts.py
------------------
Generates offline PNG charts from the database for the README.
No Streamlit or browser required — runs anywhere Python + matplotlib is installed.

Charts produced:
  screenshots/sentiment_by_category.png
  screenshots/top_channels.png
  screenshots/sentiment_distribution.png
  screenshots/dashboard_preview.png   (combined 2x2 grid)

Usage:
    python scripts/generate_charts.py
"""

import os
import sys
from collections import Counter
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from database import get_engine, load_all

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "screenshots")

COLORS = {
    "Positive": "#2ecc71",
    "Neutral":  "#f39c12",
    "Negative": "#e74c3c",
}
BAR_COLOR  = "#3498db"
CHART_BG   = "#fafafa"
STOPWORDS  = {
    "the","a","an","and","or","in","on","at","to","for","of","with","is","are",
    "was","were","be","been","have","has","do","does","did","this","that","i",
    "you","he","she","it","we","they","new","get","via","s","ep","ft","official",
    "video","full","episode","part","season","vs","2024","2025","2026","amp",
}


def load_df() -> pd.DataFrame:
    engine = get_engine()
    return load_all(engine)


def chart_sentiment_by_category(df: pd.DataFrame, ax=None, save_path=None):
    sent = (
        df.groupby("category_name")["sentiment_score"]
        .mean()
        .sort_values()
    )
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))
    colors = [COLORS["Positive"] if v >= 0.05 else COLORS["Negative"] if v <= -0.05
              else COLORS["Neutral"] for v in sent.values]
    ax.barh(sent.index, sent.values, color=colors)
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Avg Sentiment Score by Category", fontweight="bold", fontsize=11)
    ax.set_xlabel("Compound Score")
    ax.spines[["top", "right"]].set_visible(False)
    if standalone:
        fig.tight_layout()
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def chart_top_channels(df: pd.DataFrame, ax=None, save_path=None):
    top = (
        df.groupby("channel_title")["view_count"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
    )
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top.index[::-1], (top.values[::-1] / 1_000_000), color=BAR_COLOR)
    ax.set_title("Top Channels by Total Views", fontweight="bold", fontsize=11)
    ax.set_xlabel("Total Views (M)")
    ax.spines[["top", "right"]].set_visible(False)
    if standalone:
        fig.tight_layout()
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def chart_sentiment_distribution(df: pd.DataFrame, ax=None, save_path=None):
    counts = df["sentiment_label"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    clrs   = [COLORS.get(l, "#95a5a6") for l in labels]
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(5, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=clrs, autopct="%1.0f%%",
        startangle=90, wedgeprops=dict(edgecolor="white", linewidth=1.5),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    ax.set_title("Sentiment Distribution", fontweight="bold", fontsize=11)
    if standalone:
        fig.tight_layout()
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def chart_keywords(df: pd.DataFrame, ax=None, save_path=None):
    words = []
    for title in df["title"].dropna():
        tokens = re.findall(r"[a-zA-Z]{3,}", title.lower())
        words.extend([w for w in tokens if w not in STOPWORDS])
    top = Counter(words).most_common(12)
    if not top:
        return
    kws, cnts = zip(*top)
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(list(kws)[::-1], list(cnts)[::-1], color="#9b59b6")
    ax.set_title("Top Keywords in Trending Titles", fontweight="bold", fontsize=11)
    ax.set_xlabel("Frequency")
    ax.spines[["top", "right"]].set_visible(False)
    if standalone:
        fig.tight_layout()
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def chart_combined_preview(df: pd.DataFrame, save_path: str):
    fig = plt.figure(figsize=(14, 9))
    fig.suptitle("YouTube Trend Analyzer — Dashboard Preview",
                 fontsize=15, fontweight="bold", y=1.01)
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    chart_sentiment_by_category(df,  ax=fig.add_subplot(gs[0, 0]))
    chart_top_channels(df,           ax=fig.add_subplot(gs[0, 1]))
    chart_sentiment_distribution(df, ax=fig.add_subplot(gs[1, 0]))
    chart_keywords(df,               ax=fig.add_subplot(gs[1, 1]))

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_df()

    if df.empty:
        print("No data in DB — run pipeline.py first.")
        return

    print(f"Generating charts from {len(df)} records...")

    chart_sentiment_by_category(df, save_path=os.path.join(OUT_DIR, "sentiment_by_category.png"))
    chart_top_channels(df,          save_path=os.path.join(OUT_DIR, "top_channels.png"))
    chart_sentiment_distribution(df,save_path=os.path.join(OUT_DIR, "sentiment_distribution.png"))
    chart_keywords(df,              save_path=os.path.join(OUT_DIR, "trending_keywords.png"))
    chart_combined_preview(df,      save_path=os.path.join(OUT_DIR, "dashboard_preview.png"))

    print(f"Done. Charts saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
