"""Parse natural-language commands into CLI settings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from prize_bond_checker.ai.client import AIProvider, extract_json_object
from prize_bond_checker.constants import SUPPORTED_DENOMINATIONS

DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
DENOM_PATTERN = re.compile(r"\b(100|200|750|1500|7500|15000|25000|40000)\b")


@dataclass
class ParsedCommand:
    denomination: int
    draw_date: str | None
    use_latest: bool
    want_summary: bool


def parse_natural_language(text: str, provider: AIProvider | None) -> ParsedCommand:
    if provider is not None:
        try:
            return _parse_with_ai(text, provider)
        except Exception:
            pass

    return _parse_with_rules(text)


def _parse_with_ai(text: str, provider: AIProvider) -> ParsedCommand:
    supported = ", ".join(map(str, SUPPORTED_DENOMINATIONS))
    prompt = (
        "Convert the user's request into JSON with exactly these keys:\n"
        "{\n"
        '  "denomination": 200,\n'
        '  "draw_date": "2026-03-16" or null,\n'
        '  "use_latest": true or false,\n'
        '  "want_summary": true or false\n'
        "}\n\n"
        f"Supported denominations: {supported}\n"
        "If the user says latest/recent/newest draw, set use_latest=true and draw_date=null.\n"
        "If no date is given, prefer use_latest=true.\n"
        "Return JSON only.\n\n"
        f"User request: {text}"
    )
    system = "You extract structured CLI settings from prize bond check requests."

    raw = provider.complete(prompt, system=system)
    data = extract_json_object(raw)

    denomination = int(data["denomination"])
    if denomination not in SUPPORTED_DENOMINATIONS:
        raise ValueError(f"Unsupported denomination: {denomination}")

    draw_date = data.get("draw_date")
    if draw_date is not None:
        draw_date = str(draw_date)

    return ParsedCommand(
        denomination=denomination,
        draw_date=draw_date,
        use_latest=bool(data.get("use_latest", draw_date is None)),
        want_summary=bool(data.get("want_summary", True)),
    )


def _parse_with_rules(text: str) -> ParsedCommand:
    lowered = text.lower()

    denom_match = DENOM_PATTERN.search(text)
    if not denom_match:
        raise ValueError(
            "Could not detect bond denomination. Example: "
            "'check my 200 bonds for the latest draw'"
        )

    denomination = int(denom_match.group(1))
    use_latest = any(word in lowered for word in ("latest", "recent", "newest", "last"))
    want_summary = "summary" in lowered or "summarize" in lowered

    date_match = DATE_PATTERN.search(text)
    draw_date = date_match.group(1) if date_match else None

    if draw_date is None and not use_latest:
        use_latest = True

    return ParsedCommand(
        denomination=denomination,
        draw_date=draw_date,
        use_latest=use_latest,
        want_summary=want_summary,
    )
