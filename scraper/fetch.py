import requests

USER_AGENT = "tdr-wait-times-personal-logger/1.0 (personal use; polls every 15 minutes)"
TIMEOUT_SECONDS = 15


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text
