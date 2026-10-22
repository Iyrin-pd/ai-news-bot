import sys

import linkedin
import news
import tg
import writer
from config import env


def is_me(chat_id) -> bool:
    return str(chat_id) == str(env("TELEGRAM_CHAT_ID"))


def digest() -> None:
    """Fetch the news, write 4 drafts, send them to Telegram."""
    left = linkedin.days_left()
    if left < 7:
        tg.send(f"⚠️ The LinkedIn token expires in {left} days. Please generate a new one.")
    items = writer.pick_top4(news.fetch_candidates())
    tg.send("Your top 4 AI news picks are ready. Tap Post or Edit under the one you want:")
    for item in items:
        tg.send_card(item, writer.draft_post(item))


def remove_buttons(message: dict) -> None:
    try:
        tg.api("editMessageReplyMarkup", chat_id=message["chat"]["id"],
               message_id=message["message_id"], reply_markup={"inline_keyboard": []})
    except Exception:
        pass   # buttons already removed


def on_callback(cb: dict) -> None:
    msg = cb["message"]
    if not is_me(msg["chat"]["id"]):
        return

    # Telegram only accepts this confirmation for about a minute after the tap.
    # Taps handled later (like every 5 minutes on GitHub) are too old, so ignore that error.
    try:
        tg.api("answerCallbackQuery", callback_query_id=cb["id"])
    except Exception:
        pass

    card = tg.parse_card(msg.get("text", ""))
    if not card:
        return

    if cb["data"] == "edit":
        tg.api("sendMessage", chat_id=msg["chat"]["id"], reply_to_message_id=msg["message_id"],
               text="✏️ Long-press the draft above, tap Reply, and send your edited text.")
    elif cb["data"] == "post":
        try:
            urn = linkedin.publish(card["text"], card["url"], card["headline"])
        except Exception as e:
            tg.send(f"❌ Posting failed: {e}")
            return
        remove_buttons(msg)
        tg.send(f"✅ Posted to LinkedIn: https://www.linkedin.com/feed/update/{urn}")


def on_message(msg: dict) -> None:
    if not is_me(msg["chat"]["id"]):
        return
    text = msg.get("text", "")

    if text.startswith("/run"):
        tg.send("Fetching the news and writing drafts. This takes about a minute...")
        digest()
        return

    original = msg.get("reply_to_message")
    if original and text:
        card = tg.parse_card(original.get("text", ""))
        if card:
            remove_buttons(original)
            tg.send_card(
                {"headline": card["headline"], "title": card["headline"],
                 "source": card["source"], "url": card["url"]},
                text,
            )
            return

    tg.send("Hi! I send your AI news picks on schedule. Send /run to get them now.")


def poll() -> None:
    """Handle any button taps or messages waiting in Telegram, then stop."""
    updates = tg.api("getUpdates", timeout=0)["result"]
    if not updates:
        return
    # Confirm them first, so a crash can never cause a double post.
    tg.api("getUpdates", offset=updates[-1]["update_id"] + 1, timeout=0)
    for u in updates:
        try:
            if "callback_query" in u:
                on_callback(u["callback_query"])
            elif "message" in u:
                on_message(u["message"])
        except Exception as e:
            print("Error handling update:", type(e).__name__)   # no URL, so no token is printed


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "digest":
        digest()
    elif mode == "poll":
        poll()
    else:
        print("Usage: python runner.py digest   or   python runner.py poll")