import os
from dotenv import load_dotenv
load_dotenv()

def env(key, default=""):
    return os.getenv(key, default)

DB_PATH = env("DB_PATH", "bot.db")
BASE_URL = env("BASE_URL").rstrip("/")
MODEL = env("CLAUDE_MODEL", "claude-sonnet-5-5")

# Trusted sources: name -> (rss url, trust score 1-10)
FEEDS = {
    "OpenAI":          ("https://openai.com/news/rss.xml", 10),
    "Google DeepMind": ("https://deepmind.google/blog/rss.xml", 10),
    "Microsoft AI":    ("https://blogs.microsoft.com/ai/feed/", 9),
    "MIT Tech Review": ("https://www.technologyreview.com/topic/artificial-intelligence/feed", 9),
    "TechCrunch":      ("https://techcrunch.com/category/artificial-intelligence/feed/", 8),
    "The Verge":       ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", 8),
    "VentureBeat":     ("https://venturebeat.com/category/ai/feed/", 7),
}
MAX_AGE_DAYS = 3