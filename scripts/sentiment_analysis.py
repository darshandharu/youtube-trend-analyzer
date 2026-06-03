"""
sentiment_analysis.py
---------------------
Runs VADER sentiment analysis on YouTube video titles.

VADER (Valence Aware Dictionary and sEntiment Reasoner) is purpose-built
for short social-media text — perfect for video titles. No training needed.

Sentiment labels:
  compound >= 0.05  -> Positive
  compound <= -0.05 -> Negative
  otherwise         -> Neutral
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyser = SentimentIntensityAnalyzer()


def score(text: str) -> dict:
    """
    Return sentiment scores for a piece of text.

    Returns:
        {
            'sentiment_score': float,   # compound: -1.0 to +1.0
            'sentiment_label': str,     # Positive / Neutral / Negative
        }
    """
    if not text or not text.strip():
        return {"sentiment_score": 0.0, "sentiment_label": "Neutral"}

    compound = _analyser.polarity_scores(text)["compound"]

    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return {"sentiment_score": round(compound, 4), "sentiment_label": label}


def enrich(records: list[dict]) -> list[dict]:
    """Add sentiment_score and sentiment_label to each record (in-place)."""
    for rec in records:
        result = score(rec.get("title", ""))
        rec["sentiment_score"] = result["sentiment_score"]
        rec["sentiment_label"] = result["sentiment_label"]
    return records


if __name__ == "__main__":
    samples = [
        "Amazing new iPhone revealed — fans go crazy!",
        "Tragic flooding kills dozens in coastal city",
        "Minecraft lets play episode 42",
        "BREAKING: stock market crashes amid inflation fears",
        "Cute dog does backflip compilation",
    ]
    for s in samples:
        r = score(s)
        print(f"  [{r['sentiment_label']:8s}] {r['sentiment_score']:+.4f}  {s}")
