"""users.watch() registration and its daily renewal.

Gmail expires a watch after 7 days, so a daily job leaves six days of headroom
for transient failures before notifications actually stop arriving.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from pipeline.auth.gmail_auth import get_gmail_service
from pipeline.config import get_settings
from pipeline.storage import db

log = logging.getLogger(__name__)

WATCH_JOB_ID = "gmail_watch"


def start_watch(service=None, settings=None) -> int:
    settings = settings or get_settings()
    settings.require("PUBSUB_TOPIC")
    service = service or get_gmail_service(settings)

    response = (
        service.users()
        .watch(
            userId="me",
            body={
                "topicName": settings.pubsub_topic,
                "labelIds": ["INBOX"],
                "labelFilterBehavior": "include",
            },
        )
        .execute()
    )

    history_id = int(response["historyId"])
    # Seed only if unset: clobbering a live cursor on every restart would
    # silently skip everything that arrived since the last notification.
    if db.set_state_if_absent("last_history_id", str(history_id), settings):
        log.info("seeded history cursor at %s", history_id)
    log.info("watch registered, expires %s", response.get("expiration"))
    return history_id


def schedule_watch_renewal(scheduler=None, settings=None) -> BackgroundScheduler:
    settings = settings or get_settings()
    scheduler = scheduler or BackgroundScheduler()
    scheduler.add_job(
        start_watch,
        "interval",
        hours=24,
        id=WATCH_JOB_ID,
        replace_existing=True,
        max_instances=1,
        kwargs={"settings": settings},
    )
    if not scheduler.running:
        scheduler.start()
    return scheduler
