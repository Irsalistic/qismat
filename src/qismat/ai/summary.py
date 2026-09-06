"""Generate human-friendly check summaries with optional AI."""

from __future__ import annotations

from qismat.ai.client import AIProvider
from qismat.models import DrawResult, Win


def fallback_summary(bond_count: int, draw: DrawResult, wins: list[Win]) -> str:
    draw_label = _draw_label(draw)

    if wins:
        lines = [
            f"Checked {bond_count} bond(s) against {draw_label}.",
            f"You have {len(wins)} winning bond(s):",
        ]
        for win in wins:
            lines.append(f"- {win.bond}: {win.tier} prize ({win.amount})")
        return "\n".join(lines)

    return (
        f"Checked {bond_count} bond(s) against {draw_label}. "
        "No matches found this time."
    )


def generate_summary(
    bond_count: int,
    draw: DrawResult,
    wins: list[Win],
    provider: AIProvider | None,
) -> tuple[str, bool]:
    """Return (summary_text, used_ai)."""
    facts = _build_facts(bond_count, draw, wins)

    if provider is None:
        return fallback_summary(bond_count, draw, wins), False

    prompt = (
        "Write a short, friendly summary (2-4 sentences) for a Pakistani prize bond owner.\n"
        "Use only the facts provided. Do not predict future wins or lucky numbers.\n"
        "If there are wins, congratulate them and mention prize tier and amount.\n"
        "If there are no wins, be brief and encouraging.\n\n"
        f"Facts:\n{facts}"
    )
    system = "You summarize prize bond draw check results clearly and honestly."

    try:
        text = provider.complete(prompt, system=system)
        return text.strip(), True
    except Exception:
        return fallback_summary(bond_count, draw, wins), False


def _draw_label(draw: DrawResult) -> str:
    parts = [f"Rs. {draw.denomination} draw on {draw.draw_date}"]
    if draw.draw_number:
        parts.append(f"Draw #{draw.draw_number}")
    if draw.city:
        parts.append(draw.city)
    return " · ".join(parts)


def _build_facts(bond_count: int, draw: DrawResult, wins: list[Win]) -> str:
    lines = [
        f"Bonds checked: {bond_count}",
        f"Denomination: Rs. {draw.denomination}",
        f"Draw date: {draw.draw_date}",
    ]
    if draw.draw_number:
        lines.append(f"Draw number: {draw.draw_number}")
    if draw.city:
        lines.append(f"City: {draw.city}")
    lines.append(f"Total winning numbers in draw: {draw.total_winners}")

    if wins:
        lines.append("Matches:")
        for win in wins:
            lines.append(f"- Bond {win.bond}: {win.tier} prize, {win.amount}")
    else:
        lines.append("Matches: none")

    return "\n".join(lines)
