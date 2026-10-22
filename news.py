import time, difflib, calendar
import feedparser
from config import FEEDS, MAX_AGE_DAYS

def fetch_candidates(limit=12):
    """Pull RSS from trusted sources, dedupe by title, rank, return the top `limit`."""
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    items = []
    for source, (url, trust) in FEEDS.items():
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:15]:
            ts = calendar.timegm(e.published_parsed) if getattr(e, "published_parsed", None) else 0
            if ts < cutoff:
                continue
            items.append({"title": e.get("title", "").strip(), "url": e.get("link", ""),
                          "source": source, "trust": trust, "ts": ts,
                          "summary": (e.get("summary", "") or "")[:400], "coverage": 1})

    # merge near-identical titles and count how many outlets covered the story
    unique = []
    for it in sorted(items, key=lambda x: -x["trust"]):
        for u in unique:
            if difflib.SequenceMatcher(None, it["title"].lower(), u["title"].lower()).ratio() > 0.75:
                u["coverage"] += 1
                break
        else:
            unique.append(it)

    now = time.time()
    for u in unique:
        recency = max(0, 1 - (now - u["ts"]) / (MAX_AGE_DAYS * 86400))
        u["score"] = u["trust"] * 2 + recency * 10 + u["coverage"] * 3
    unique.sort(key=lambda x: -x["score"])
    return unique[:limit]