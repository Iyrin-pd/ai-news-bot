import httpx

from config import env


def _send(payload: dict) -> dict:
    url = f"https://graph.facebook.com/v21.0/{env('WA_PHONE_NUMBER_ID')}/messages"
    r = httpx.post(
        url,
        json={"messaging_product": "whatsapp", "to": env("LEAD_PHONE"), **payload},
        headers={"Authorization": f"Bearer {env('WA_TOKEN')}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_text(body: str) -> dict:
    return _send({"type": "text", "text": {"body": body, "preview_url": True}})


def send_digest_template() -> dict:
    """Opens the chat. The template must have a quick-reply button with payload REVIEW."""
    return _send({
        "type": "template",
        "template": {
            "name": env("WA_TEMPLATE", "ai_news_digest"),
            "language": {"code": "en"},
            "components": [{
                "type": "button",
                "sub_type": "quick_reply",
                "index": "0",
                "parameters": [{"type": "payload", "payload": "REVIEW"}],
            }],
        },
    })


def send_news_list(items: list[dict]) -> dict:
    """The 4-headline popup list, like the Meta AI chatbot style."""
    body = "Today's top AI news. Tap a story to draft your post:\n\n" + "\n\n".join(
        f"{i + 1}. {it['headline']} ({it['source']})" for i, it in enumerate(items)
    )
    rows = [
        {
            "id": f"news_{i}",
            "title": f"{i + 1}. {it['source']}"[:24],
            "description": it["headline"][:72],
        }
        for i, it in enumerate(items)
    ]
    return _send({
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body[:1024]},
            "action": {"button": "Choose story", "sections": [{"title": "Top 4", "rows": rows}]},
        },
    })