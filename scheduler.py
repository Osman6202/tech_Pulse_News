import zoneinfo
import datetime
import threading
import time
import schedule

from config import SCHEDULE_TZ
from logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    def __init__(self) -> None:
        self._running = False

    def start(self, on_full, on_alert) -> None:
        tz = zoneinfo.ZoneInfo(SCHEDULE_TZ)
        now_local = datetime.datetime.now()
        now_tz = datetime.datetime.now(tz).replace(tzinfo=None)
        offset = round((now_local - now_tz).total_seconds() / 3600)
        logger.info(f"Scheduler: {SCHEDULE_TZ} offset from local = {offset:+d}h")

        for myt_hour in (8, 20):
            local_hour = (myt_hour + offset) % 24
            schedule.every().day.at(f"{local_hour:02d}:00").do(
                lambda f=on_full: threading.Thread(target=f, daemon=True).start()
            ).tag("full")
            logger.info(f"Full briefing scheduled at local {local_hour:02d}:00 ({myt_hour:02d}:00 MYT)")

        schedule.every().hour.do(
            lambda a=on_alert: threading.Thread(target=a, daemon=True).start()
        ).tag("alert")
        logger.info("Alert scan scheduled every hour")

        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        schedule.clear()

    def _loop(self) -> None:
        while self._running:
            schedule.run_pending()
            time.sleep(30)

    def next_run_times(self) -> list[datetime.datetime]:
        return sorted(j.next_run for j in schedule.jobs if j.next_run)

    def next_full_run(self) -> datetime.datetime | None:
        jobs = [j for j in schedule.jobs if "full" in j.tags]
        return min((j.next_run for j in jobs), default=None)

    def next_alert_run(self) -> datetime.datetime | None:
        jobs = [j for j in schedule.jobs if "alert" in j.tags]
        return min((j.next_run for j in jobs), default=None)
