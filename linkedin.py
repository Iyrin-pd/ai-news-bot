import datetime

import httpx

from config import env


def days_left() -> int:
    """Days until the token expires. Returns 999 (no warning) if no expiry date is set."""
    exp = env("LINKEDIN_TOKEN_EXPIRES")
    if not exp:
        return 999
    return (datetime.date.fromisoformat(exp) - datetime.date.today()).days


def _escape(text: str) -> str:
    # LinkedIn reserves these characters. '#' is left alone so hashtags still work.
    for ch in "\\|{}@[]()<>*_~":
        text = text.replace(ch, "\\" + ch)
    return text


def publish(text: str, link: str, title: str) -> str:
    token, person = env("LINKEDIN_TOKEN"), env("LINKEDIN_PERSON_ID")
    if not token or not person:
        raise RuntimeError("LINKEDIN_TOKEN or LINKEDIN_PERSON_ID is missing in .env")
    r = httpx.post(
        "https://api.linkedin.com/rest/posts",
        timeout=30,
        json={
            "author": f"urn:li:person:{person}",
            "commentary": _escape(text),
            "visibility": "PUBLIC",
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {"article": {"source": link, "title": title[:200]}},
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": env("LI_API_VERSION", "202609"),
        },
    )
    if r.status_code != 201:
        raise RuntimeError(f"LinkedIn said {r.status_code}: {r.text}")
    return r.headers.get("x-restli-id", "")