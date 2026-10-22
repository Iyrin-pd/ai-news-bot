import threading
import time

import db
import linkedin
import pipeline
import tg
from config import env


def is_me(chat_id) -> bool:
    return str(chat_id) == str(env("TELEGRAM_CHAT_ID"))


def do_post(token: str, d: dict, message: dict) -> None:
    item = d["item"]
    try:
        urn = linkedin.publish(d["text"], item["url"], item.get("headline", item["title"]))
    except Exception as e:
        tg.send(f"❌ Posting failed: {e}")
        return
    db.update_draft(token, status="posted", post_urn=urn)
    db.set_batch_status(d["batch_id"], "picked")
    tg.api("editMessageReplyMarkup", chat_id=message["chat"]["id"],
           message_id=message["message_id"], reply_markup={"inline_keyboard": []})
    tg.send(f"✅ Posted to LinkedIn: https://www.linkedin.com/feed/update/{urn}")


def handle_callback(cb: dict) -> None:
    message = cb["message"]
    if not is_me(message["chat"]["id"]):
        return
    tg.api("answerCallbackQuery", callback_query_id=cb["id"])
    action, token = cb["data"].split(":", 1)
    d = db.get_draft(token)
    if not d:
        tg.send("That draft was not found.")
        return
    if d["status"] != "pending":
        tg.send(f"That draft is already {d['status']}.")
        return
    if action == "post":
        do_post(token, d, message)
    elif action == "edit":
        db.kv_set("editing", token)
        tg.send("✏️ Send your edited post text as your next message.")


def handle_message(msg: dict) -> None:
    if not is_me(msg["chat"]["id"]):
        return
    text = msg.get("text", "")
    if text.startswith("/run"):
        tg.send("Fetching the news and writing drafts. This takes about a minute...")
        threading.Thread(target=pipeline.run_digest, daemon=True).start()
        return
    token = db.kv_get("editing")
    if token and text:
        d = db.get_draft(token)
        if d and d["status"] == "pending":
            db.update_draft(token, text=text)
            db.kv_set("editing", None)
            tg.send_draft(token, d["item"], text)
            return
    tg.send("Hi! I will send your AI news picks on schedule. Send /run to get them now.")


def main() -> None:
    db.init()
    pipeline.start()
    print("Bot is running. Press Ctrl+C to stop.")
    offset = None
    while True:
        params = {"timeout": 50}
        if offset:
            params["offset"] = offset
        try:
            updates = tg.api("getUpdates", **params)["result"]
        except Exception as e:
            print("Telegram error:", e)
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                if "callback_query" in u:
                    handle_callback(u["callback_query"])
                elif "message" in u:
                    handle_message(u["message"])
            except Exception as e:
                print("Error handling update:", e)


if __name__ == "__main__":
    main()