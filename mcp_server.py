import json
import os
import re
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")   # must run before the imports below

import news                          # noqa: E402
from style import style_prompt       # noqa: E402

mcp = FastMCP("ai-news-linkedin")

DRAFTS = BASE / "drafts"
DRAFTS.mkdir(exist_ok=True)

LINKEDIN_VERSION = os.getenv("LI_API_VERSION", "202609")  # YYYYMM; 426 error = try a newer month


@mcp.tool()
def fetch_ai_news(limit: int = 8) -> list[dict]:
    """Fetch the latest AI news from trusted sources, deduplicated and ranked best-first."""
    items = news.fetch_candidates(limit)
    return [{"source": i["source"], "title": i["title"], "link": i["url"],
             "summary": i["summary"]} for i in items]


@mcp.tool()
def save_draft(text: str, source_url: str, source_title: str = "") -> str:
    """Save a LinkedIn post draft to disk. Returns the draft id."""
    draft_id = uuid.uuid4().hex[:8]
    (DRAFTS / f"{draft_id}.json").write_text(
        json.dumps({"text": text, "source_url": source_url, "source_title": source_title},
                   indent=2),
        encoding="utf-8",
    )
    return draft_id


@mcp.tool()
def list_drafts() -> list[dict]:
    """List all saved drafts that have not been posted yet."""
    out = []
    for f in sorted(DRAFTS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append({"id": f.stem, **d})
    return out


def escape_linkedin(text: str) -> str:
    """Escape LinkedIn formatting characters. '#' is left alone so hashtags still work."""
    return re.sub(r"([\\|{}@\[\]()<>*_~])", r"\\\1", text)


@mcp.tool()
def publish_to_linkedin(draft_id: str, confirmed: bool = False, visibility: str = "PUBLIC") -> str:
    """Publish a saved draft to LinkedIn. Only call with confirmed=True after the
    user has explicitly approved the exact final text in this conversation."""
    if not confirmed:
        return "Not posted. Show the draft to the user and ask for approval first."

    if not re.fullmatch(r"[0-9a-f]{8}", draft_id):
        return "Invalid draft id."
    path = DRAFTS / f"{draft_id}.json"
    if not path.exists():
        return f"No draft found with id {draft_id}."

    token, person = os.getenv("LINKEDIN_TOKEN"), os.getenv("LINKEDIN_PERSON_ID")
    if not token or not person:
        return "LINKEDIN_TOKEN or LINKEDIN_PERSON_ID is missing in the .env file."

    draft = json.loads(path.read_text(encoding="utf-8"))
    body = {
        "author": f"urn:li:person:{person}",
        "commentary": escape_linkedin(draft["text"].strip()),
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if draft.get("source_url"):
        body["content"] = {"article": {
            "source": draft["source_url"],
            "title": (draft.get("source_title") or "Read the full story")[:200],
        }}

    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    r = httpx.post("https://api.linkedin.com/rest/posts", json=body, headers=headers, timeout=30)
    if r.status_code == 201:
        path.rename(path.with_suffix(".posted"))
        return f"Posted. Post id: {r.headers.get('x-restli-id', 'unknown')}"
    return f"Failed: {r.status_code} {r.text}"


@mcp.prompt()
def linkedin_post_style() -> str:
    """Writing rules for LinkedIn posts, with the user's own examples."""
    return style_prompt()


if __name__ == "__main__":
    mcp.run()