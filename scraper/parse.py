import re

from bs4 import BeautifulSoup, Tag

_WAIT_NUMBER_RE = re.compile(r"(\d+)\s*分")
DEFAULT_AREA = "その他"


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
    """(area, name, condition_text) を文書順に返す。
    エリア見出し(h3.area_name)と施設ブロック(.realtime-attr)は同じ階層に
    並んでいるので、見出しに出会うたびに「現在のエリア」を更新しながら進む。"""
    soup = BeautifulSoup(html, "lxml")
    current_area = DEFAULT_AREA
    for el in soup.select("h3.area_name, .realtime-attr"):
        if el.name == "h3":
            text = el.get_text(strip=True)
            current_area = text if text else DEFAULT_AREA
            continue
        name_div = el.select_one(".realtime-attr-name")
        cond_div = el.select_one(".realtime-attr-condition")
        if name_div is None or cond_div is None:
            continue
        yield current_area, _direct_text(name_div), _condition_text(cond_div)


def parse_attractions(html: str) -> list[dict]:
    """realtime.php(order=area)を[{"area","name","status","wait_minutes"}, ...]に変換する。"""
    results = []
    for area, name, condition_text in _iter_blocks(html):
        numbers = [int(n) for n in _WAIT_NUMBER_RE.findall(condition_text)]
        if numbers:
            status, wait_minutes = "運営中", numbers[0]
        else:
            status, wait_minutes = condition_text or "不明", None
        results.append({"area": area, "name": name, "status": status, "wait_minutes": wait_minutes})
    return results


def parse_restaurants(html: str) -> list[dict]:
    """restwait.phpを[{"area","name","status","wait_min","wait_max"}, ...]に変換する。
    レストランの待ち時間は「10分 〜 30分」のような範囲表記のことが多い。"""
    results = []
    for area, name, condition_text in _iter_blocks(html):
        numbers = [int(n) for n in _WAIT_NUMBER_RE.findall(condition_text)]
        if numbers:
            status = "営業中"
            wait_min = numbers[0]
            wait_max = numbers[1] if len(numbers) > 1 else numbers[0]
        else:
            status = condition_text or "不明"
            wait_min = wait_max = None
        results.append(
            {"area": area, "name": name, "status": status, "wait_min": wait_min, "wait_max": wait_max}
        )
    return results
