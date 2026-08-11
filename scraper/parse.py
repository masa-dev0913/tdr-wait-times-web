import re

from bs4 import BeautifulSoup, Tag

_WAIT_NUMBER_RE = re.compile(r"(\d+)\s*分")


def _direct_text(tag: Tag) -> str:
    """Text of tag's own direct text nodes, ignoring text inside nested tags
    (e.g. the "(caramel flavor)" <span> next to a restaurant name)."""
    for piece in tag.find_all(string=True, recursive=False):
        stripped = piece.strip()
        if stripped:
            return stripped
    return tag.get_text(strip=True)


def _condition_text(tag: Tag) -> str:
    """Text of the wait-time/status box, excluding the nested opening-hours
    block that some restaurant entries embed inside the same element."""
    for nested in tag.select(".greeting_timetable"):
        nested.extract()
    return tag.get_text(separator=" ", strip=True)


def _iter_blocks(html: str):
    soup = BeautifulSoup(html, "lxml")
    for block in soup.select(".realtime-attr"):
        name_div = block.select_one(".realtime-attr-name")
        cond_div = block.select_one(".realtime-attr-condition")
        if name_div is None or cond_div is None:
            continue
        yield _direct_text(name_div), _condition_text(cond_div)


def parse_attractions(html: str) -> list[dict]:
    """Parse an attraction realtime.php page into
    [{"name", "status", "wait_minutes"}, ...]."""
    results = []
    for name, condition_text in _iter_blocks(html):
        numbers = [int(n) for n in _WAIT_NUMBER_RE.findall(condition_text)]
        if numbers:
            status, wait_minutes = "運営中", numbers[0]
        else:
            status, wait_minutes = condition_text or "不明", None
        results.append({"name": name, "status": status, "wait_minutes": wait_minutes})
    return results


def parse_restaurants(html: str) -> list[dict]:
    """Parse a restwait.php page into
    [{"name", "status", "wait_min", "wait_max"}, ...].
    Restaurant waits are often a range like "10分 〜 30分"."""
    results = []
    for name, condition_text in _iter_blocks(html):
        numbers = [int(n) for n in _WAIT_NUMBER_RE.findall(condition_text)]
        if numbers:
            status = "営業中"
            wait_min = numbers[0]
            wait_max = numbers[1] if len(numbers) > 1 else numbers[0]
        else:
            status = condition_text or "不明"
            wait_min = wait_max = None
        results.append({"name": name, "status": status, "wait_min": wait_min, "wait_max": wait_max})
    return results
