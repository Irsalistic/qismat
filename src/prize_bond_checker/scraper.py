"""Fetch and parse draw results from allprizebond.pk."""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from prize_bond_checker.constants import BASE_URL
from prize_bond_checker.models import DrawResult

BOND_PATTERN = re.compile(r"\b\d{6}\b")
DRAW_META_PATTERN = re.compile(
    r"Draw\s*#\s*(?P<number>\d+)\s+Result\s+(?P<city>[A-Za-z]+)",
    re.IGNORECASE,
)


def fetch_draw_html(denomination: int, draw_date: str, timeout: int = 30) -> str:
    url = BASE_URL.format(denomination=denomination, draw_date=draw_date)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _numbers_in(element) -> set[str]:
    if element is None:
        return set()
    return {match.group(0) for match in BOND_PATTERN.finditer(element.get_text())}


def parse_draw_html(html: str, denomination: int, draw_date: str) -> DrawResult:
    soup = BeautifulSoup(html, "html.parser")
    result = DrawResult(denomination=denomination, draw_date=draw_date)

    title = soup.find("h1")
    if title:
        meta = DRAW_META_PATTERN.search(title.get_text(" ", strip=True))
        if meta:
            result.draw_number = meta.group("number")
            result.city = meta.group("city")

    for heading in soup.find_all("h2"):
        label = heading.get_text(" ", strip=True).lower()

        if "first prize" in label:
            result.prizes["1st"] = _numbers_in(heading.find_next("h3"))
        elif "second prize" in label:
            result.prizes["2nd"] = _numbers_in(heading.find_next("h3"))
        elif "third prize" in label:
            table = heading.find_next("table")
            cells = table.find_all("td") if table else []
            result.prizes["3rd"] = {
                match.group(0)
                for cell in cells
                for match in BOND_PATTERN.finditer(cell.get_text())
            }

    if not any(result.prizes.values()):
        raise ValueError("Could not parse winning numbers. The website layout may have changed.")

    return result
