import datetime
import secrets

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import db
import linkedin
import news
import tg
import writer
from config import env

scheduler = BackgroundScheduler(timezone=env("TZ", "Asia/Kolkata"))


def run_digest():
    """Fetch the news, pick the top 4, write all 4 drafts, send them to Telegram."""
    left = linkedin.days_left()
    if left < 7:
        tg.send(f"⚠️ The LinkedIn token expires in {left} days. Please generate a new one.")

    items = writer.pick_top4(news.fetch_candidates())
    batch_id = db.new_batch(items)
    tg.send("Your top 4 AI news picks are ready. Tap Post or Edit under the one you want:")
    for item in items:
        token = secrets.token_hex(4)
        text = writer.draft_post(item)
        db.new_draft(token, batch_id, item, text)
        tg.send_draft(token, item, text)

    hours = float(env("REMINDER_HOURS", "4"))
    run_at = datetime.datetime.now(scheduler.timezone) + datetime.timedelta(hours=hours)
    scheduler.add_job(remind, "date", run_date=run_at, args=[batch_id], id=f"remind_{batch_id}")


def remind(batch_id: int):
    if db.batch_status(batch_id) == "sent":
        tg.send("Reminder: today's AI news picks are still waiting above.")
        db.set_batch_status(batch_id, "expired")   # one reminder, then skip


def start():
    trigger = CronTrigger(
        day_of_week=env("SCHEDULE_DAYS", "mon,wed,fri"),
        hour=int(env("SCHEDULE_HOUR", "9")),
        minute=int(env("SCHEDULE_MINUTE", "0")),
        timezone=env("TZ", "Asia/Kolkata"),
    )
    scheduler.add_job(run_digest, trigger, id="digest", replace_existing=True)
    scheduler.start()