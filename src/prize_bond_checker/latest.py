"""Find the latest published draw date for a denomination."""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from prize_bond_checker.constants import SUPPORTED_DENOMINATIONS

HOMEPAGE_URL = "https://allprizebond.pk/"
DRAW_LINK_PATTERN = re.compile(r"/draw/(?P<denomination>\d+)/(?P<date>\d{4}-\d{2}-\d{2})")


def fetch_latest_draw_date(denomination: int, timeout: int = 30) -> str:
    if denomination not in SUPPORTED_DENOMINATIONS:
        raise ValueError(f"Unsupported denomination: {denomination}")

    response = requests.get(HOMEPAGE_URL, timeout=timeout)
    response.raise_for_status()

    dates = _extract_draw_dates(response.text, denomination)
    if not dates:
        raise ValueError(
            f"Could not find any Rs. {denomination} draw dates on allprizebond.pk. "
            "Use --date YYYY-MM-DD instead."
        )

    return max(dates)


def _extract_draw_dates(html: str, denomination: int) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    dates: set[str] = set()

    for tag in soup.find_all(["a", "option"]):
        href = tag.get("href") or tag.get("value") or ""
        text = tag.get_text(" ", strip=True)
        for source in (href, text):
            for match in DRAW_LINK_PATTERN.finditer(source):
                if int(match.group("denomination")) == denomination:
                    dates.add(match.group("date"))

    return dates
