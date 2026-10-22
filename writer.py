import json
import re
import time

import httpx

from config import env
from style import style_prompt

URL = "https://api.groq.com/openai/v1/chat/completions"

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0000FE0F\U0000200D]+"
)


def clean(text: str) -> str:
    """Remove emojis, dashes and markdown so the post reads like plain human writing."""
    text = EMOJI.sub("", text)
    text = text.replace("\u2014", ", ").replace("\u2013", "-")
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^[\-\*\u2022]\s+", "", text, flags=re.M)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _ask(system: str, user: str, json_mode: bool = False) -> str:
    body = {
        "model": env("GROQ_MODEL", "openai/gpt-oss-120b"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    for _ in range(6):
        r = httpx.post(
            URL,
            json=body,
            headers={"Authorization": f"Bearer {env('GROQ_API_KEY')}"},
            timeout=60,
        )
        if r.status_code == 429:   # too many tokens this minute: wait, then try again
            m = re.search(r"try again in ([\d.]+)s", r.text)
            time.sleep(float(m.group(1)) + 2 if m else 15)
            continue
        break

    if r.status_code != 200:
        raise RuntimeError(f"Groq error {r.status_code}: {r.text}")
    return r.json()["choices"][0]["message"]["content"].strip()

def _parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def pick_top4(candidates: list[dict]) -> list[dict]:
    """The model chooses the 4 best stories and writes a short headline and summary for each."""
    listing = [
        {"idx": i, "title": c["title"], "source": c["source"], "snippet": c["summary"]}
        for i, c in enumerate(candidates)
    ]
    system = (
        "You curate AI news for a tech professional's LinkedIn audience. "
        "Pick the 4 most important, distinct, credible stories. Use at most 2 "
        "stories from the same source. "
        "The headline and summary must be plain text with no emojis. "
        'Reply ONLY with JSON: {"picks":[{"idx":int,"headline":str (max 70 chars),'
        '"summary":str (max 140 chars)}]}'
    )
    picks = _parse_json(_ask(system, json.dumps(listing), json_mode=True))["picks"][:4]

    out = []
    for p in picks:
        item = dict(candidates[p["idx"]])
        item["headline"] = clean(p["headline"])
        item["short"] = clean(p["summary"])
        out.append(item)
    return out


def draft_post(item: dict) -> str:
    """Write the LinkedIn post using your lead's style rules and example posts."""
    system = style_prompt() + "\n\nReturn only the post text, nothing else."
    user = (
        f"Title: {item['title']}\n"
        f"Source: {item['source']}\n"
        f"Snippet: {item['summary']}"
    )
    return clean(_ask(system, user))