import httpx

from config import env


def api(method: str, **data) -> dict:
    r = httpx.post(
        f"https://api.telegram.org/bot{env('TELEGRAM_TOKEN')}/{method}",
        json=data,
        timeout=70,
    )
    r.raise_for_status()
    return r.json()


def send(text: str, buttons: list | None = None) -> dict:
    data = {"chat_id": env("TELEGRAM_CHAT_ID"), "text": text}
    if buttons:
        data["reply_markup"] = {"inline_keyboard": [buttons]}
    return api("sendMessage", **data)


def draft_message(item: dict, text: str) -> str:
    head = item.get("headline", item["title"])
    return f"📰 {head} ({item['source']})\n\n{text}\n\nSource: {item['url']}"


def post_edit_buttons(token: str) -> list:
    return [
        {"text": "Post", "callback_data": f"post:{token}"},
        {"text": "Edit", "callback_data": f"edit:{token}"},
    ]


def send_draft(token: str, item: dict, text: str) -> None:
    send(draft_message(item, text), post_edit_buttons(token))


def send_card(item: dict, text: str) -> None:
    """Draft message with Post and Edit buttons. No database needed."""
    send(draft_message(item, text), [
        {"text": "Post", "callback_data": "post"},
        {"text": "Edit", "callback_data": "edit"},
    ])


def parse_card(message_text: str):
    """Recover the story and draft from a card message. Returns None if it isn't a card."""
    if not message_text.startswith("📰 ") or "\n\nSource: " not in message_text:
        return None
    first, rest = message_text.split("\n\n", 1)
    body, url = rest.rsplit("\n\nSource: ", 1)
    headline, source = first[2:].strip().rsplit(" (", 1)
    return {"headline": headline, "source": source.rstrip(")"),
            "url": url.strip(), "text": body.strip()}