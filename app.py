import html
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

import db
import linkedin
import pipeline
import whatsapp
from config import env


@asynccontextmanager
async def lifespan(app):
    db.init()
    pipeline.start()
    yield
    pipeline.scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


# ---------- WhatsApp webhook ----------
@app.get("/webhook")
def verify(request: Request):
    q = request.query_params
    if q.get("hub.verify_token") == env("WA_VERIFY_TOKEN"):
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


@app.post("/webhook")
async def incoming(request: Request):
    data = await request.json()
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        return {"ok": True}                      # delivery receipts etc.
    if msg["from"] != env("LEAD_PHONE"):
        return {"ok": True}                      # ignore everyone else

    batch = db.latest_batch()
    if msg["type"] == "button" and msg["button"].get("payload") == "REVIEW" and batch:
        whatsapp.send_news_list(batch["items"])
    elif msg["type"] == "interactive" and batch:
        rid = msg["interactive"].get("list_reply", {}).get("id", "")
        if rid.startswith("news_"):
            token = pipeline.create_draft_for(batch, int(rid[5:]))
            whatsapp.send_text(
                f"Your draft is ready. Edit and post here (valid 24h):\n{env('BASE_URL')}/edit/{token}"
            )
    elif msg["type"] == "text":
        whatsapp.send_text("Hi! I'll send your AI news picks on schedule.")
    return {"ok": True}


# ---------- Edit / approve page ----------
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Review post</title>
<style>
:root{{--bg:#f6f7f9;--fg:#1a1a1a;--card:#fff;--mut:#666;--bd:#d5d8dd}}
@media(prefers-color-scheme:dark){{:root{{--bg:#15171a;--fg:#eee;--card:#1f2226;--mut:#9aa;--bd:#3a3f46}}}}
body{{font:16px system-ui;background:var(--bg);color:var(--fg);margin:0;padding:16px}}
.c{{max-width:640px;margin:auto;background:var(--card);padding:20px;border-radius:12px}}
textarea{{width:100%;height:320px;box-sizing:border-box;padding:12px;font:inherit;
background:var(--bg);color:var(--fg);border:1px solid var(--bd);border-radius:8px}}
button{{padding:12px 20px;border:0;border-radius:8px;font:inherit;cursor:pointer;margin-right:8px}}
.p{{background:#0a66c2;color:#fff}}.r{{background:var(--bd);color:var(--fg)}}
small{{color:var(--mut)}}
</style></head><body><div class="c">
<h2>{title}</h2>
<small>Source: <a href="{url}">{source}</a> (added to the post as a link card)</small>
{body}
</div></body></html>"""


def _page(d: dict, body: str) -> str:
    it = d["item"]
    return PAGE.format(
        title=html.escape(it.get("headline", it["title"])),
        url=html.escape(it["url"]),
        source=html.escape(it["source"]),
        body=body,
    )


def _load(token: str) -> dict:
    d = db.get_draft(token)
    if not d or time.time() - d["created"] > 86400:
        raise HTTPException(404, "This link has expired")
    return d


@app.get("/edit/{token}", response_class=HTMLResponse)
def edit(token: str):
    d = _load(token)
    if d["status"] != "pending":
        return _page(d, f"<p>This draft is already <b>{d['status']}</b>.</p>")
    return _page(d, f"""<form method="post" action="/edit/{token}/post">
<textarea name="text">{html.escape(d['text'])}</textarea><br><br>
<button class="p" type="submit">Approve &amp; Post to LinkedIn</button>
<button class="r" type="submit" formaction="/edit/{token}/reject">Reject</button>
</form>""")


@app.post("/edit/{token}/post", response_class=HTMLResponse)
def post(token: str, text: str = Form(...)):
    d = _load(token)
    if d["status"] != "pending":
        return _page(d, "<p>Already handled.</p>")
    try:
        urn = linkedin.publish(text, d["item"]["url"], d["item"].get("headline", d["item"]["title"]))
    except Exception as e:
        return _page(d, f"<p>Posting failed: {html.escape(str(e))}</p>")
    db.update_draft(token, text=text, status="posted", post_urn=urn)
    link = f"https://www.linkedin.com/feed/update/{urn}"
    try:
        whatsapp.send_text(f"Posted to LinkedIn: {link}")
    except Exception:
        pass   # WhatsApp not connected yet


@app.post("/edit/{token}/reject", response_class=HTMLResponse)
def reject(token: str):
    d = _load(token)
    db.update_draft(token, status="rejected")
    return _page(d, "<p>Rejected. Nothing was posted.</p>")


# ---------- LinkedIn login ----------
@app.get("/linkedin/login")
def li_login():
    return RedirectResponse(linkedin.auth_url())


@app.get("/linkedin/callback")
def li_callback(code: str):
    linkedin.handle_callback(code)
    return PlainTextResponse("LinkedIn connected. You can close this tab.")


# ---------- Manual test trigger ----------
@app.post("/admin/run-now")
def run_now():
    pipeline.run_digest()
    return {"ok": True}