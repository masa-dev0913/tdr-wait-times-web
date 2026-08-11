import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from common.db import get_connection, init_db
from scraper.fetch import fetch_html
from scraper.parse import parse_attractions, parse_restaurants

JST = ZoneInfo("Asia/Tokyo")
PARKS = ["land", "sea"]
ATTRACTION_URL = "https://tokyodisneyresort.info/realtime.php?park={park}&order=area"
RESTAURANT_URL = "https://tokyodisneyresort.info/restwait.php?park={park}"


def run() -> None:
    conn = get_connection()
    init_db(conn)
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

    for park in PARKS:
        attraction_html = fetch_html(ATTRACTION_URL.format(park=park))
        for item in parse_attractions(attraction_html):
            conn.execute(
                "INSERT INTO attractions (timestamp_jst, park, area, name, status, wait_minutes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (now, park, item["area"], item["name"], item["status"], item["wait_minutes"]),
            )

        restaurant_html = fetch_html(RESTAURANT_URL.format(park=park))
        for item in parse_restaurants(restaurant_html):
            conn.execute(
                "INSERT INTO restaurants (timestamp_jst, park, area, name, status, wait_min, wait_max) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, park, item["area"], item["name"], item["status"], item["wait_min"], item["wait_max"]),
            )

    conn.commit()
    conn.close()
    print(f"[{now}] scrape ok")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001 - want any failure logged and surfaced to cron
        print(f"scrape failed: {exc}", file=sys.stderr)
        sys.exit(1)
