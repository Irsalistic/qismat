"""Load a prize-bond portfolio from a local text file.

Backward compatible with a flat list of numbers. Optional sections group
bonds by denomination and owner:

    [200]
    477670

    [750:parents]
    123456
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from prize_bond_checker.bonds import normalize_bond
from prize_bond_checker.constants import DEFAULT_DENOMINATION, SUPPORTED_DENOMINATIONS

SECTION_RE = re.compile(r"^\[(?P<denom>\d{3,5})(?::(?P<owner>[^\]]+))?\]\s*$")


@dataclass(frozen=True)
class BondHolding:
    number: str
    denomination: int | None = None
    owner: str | None = None


@dataclass
class Portfolio:
    holdings: list[BondHolding]
    path: Path

    def __bool__(self) -> bool:
        return bool(self.holdings)

    @property
    def has_sections(self) -> bool:
        return any(item.denomination is not None for item in self.holdings)

    def holdings_for(self, denomination: int, include_unsectioned: bool) -> list[BondHolding]:
        items: list[BondHolding] = []
        for item in self.holdings:
            if item.denomination == denomination:
                items.append(item)
            elif item.denomination is None and include_unsectioned:
                items.append(item)
        return items

    def grouped(self, default_denomination: int = DEFAULT_DENOMINATION) -> dict[int, list[BondHolding]]:
        denoms = {item.denomination for item in self.holdings if item.denomination is not None}
        if any(item.denomination is None for item in self.holdings):
            denoms.add(default_denomination)
        if not denoms:
            denoms.add(default_denomination)

        groups: dict[int, list[BondHolding]] = {}
        for denom in sorted(denoms):
            include_unsectioned = denom == default_denomination
            holdings = self.holdings_for(denom, include_unsectioned)
            if holdings:
                groups[denom] = holdings
        return groups

    def numbers_for(self, denomination: int, default_denomination: int = DEFAULT_DENOMINATION) -> set[str]:
        return {item.number for item in self.grouped(default_denomination).get(denomination, [])}

    def owners_for(self, denomination: int, default_denomination: int = DEFAULT_DENOMINATION) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for item in self.grouped(default_denomination).get(denomination, []):
            if item.owner and item.number not in mapping:
                mapping[item.number] = item.owner
        return mapping

    def denominations(self, default_denomination: int = DEFAULT_DENOMINATION) -> list[int]:
        return list(self.grouped(default_denomination).keys())


def load_portfolio(path: Path) -> Portfolio:
    if not path.exists():
        raise FileNotFoundError(f"Bond file not found: {path}")

    holdings: list[BondHolding] = []
    denomination: int | None = None
    owner: str | None = None

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        section = SECTION_RE.match(line)
        if section:
            denomination = int(section.group("denom"))
            if denomination not in SUPPORTED_DENOMINATIONS:
                supported = ", ".join(map(str, SUPPORTED_DENOMINATIONS))
                raise ValueError(
                    f"{path}:{line_no}: unsupported denomination {denomination}. Supported: {supported}"
                )
            label = (section.group("owner") or "").strip()
            owner = label or None
            continue

        holdings.append(
            BondHolding(
                number=normalize_bond(line),
                denomination=denomination,
                owner=owner,
            )
        )

    if not holdings:
        raise ValueError(f"No bond numbers found in {path}")

    return Portfolio(holdings=holdings, path=path)


def add_holding(
    path: Path,
    number: str,
    denomination: int,
    owner: str | None = None,
) -> bool:
    """Append a bond to the matching section. Returns False if it is already present."""
    if denomination not in SUPPORTED_DENOMINATIONS:
        supported = ", ".join(map(str, SUPPORTED_DENOMINATIONS))
        raise ValueError(f"Unsupported denomination {denomination}. Supported: {supported}")

    number = normalize_bond(number)
    owner = owner.strip() if owner else None
    header = f"[{denomination}:{owner}]" if owner else f"[{denomination}]"

    if path.exists():
        try:
            existing = load_portfolio(path)
        except ValueError:
            existing = None
        if existing:
            for item in existing.holdings:
                if item.number == number and (item.denomination or denomination) == denomination:
                    if (item.owner or None) == owner:
                        return False
    else:
        path.write_text(
            "# Prize bond portfolio — one number per line.\n"
            "# Optional sections: [200] or [200:parents]\n\n",
            encoding="utf-8",
        )

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    header_index = _find_section_index(lines, denomination, owner)

    if header_index is None:
        suffix = [] if not lines or not lines[-1].strip() else [""]
        new_lines = lines + suffix + [header, number, ""]
        path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
        return True

    insert_at = _section_append_index(lines, header_index)
    lines.insert(insert_at, number)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def remove_holding(path: Path, number: str, denomination: int | None = None) -> bool:
    """Remove matching bond lines. Returns True if anything was removed."""
    if not path.exists():
        return False

    target = normalize_bond(number)
    original = path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    current_denom: int | None = None
    removed = False

    for raw in original:
        stripped = raw.strip()
        section = SECTION_RE.match(stripped)
        if section:
            current_denom = int(section.group("denom"))
            kept.append(raw)
            continue
        if not stripped or stripped.startswith("#"):
            kept.append(raw)
            continue
        try:
            candidate = normalize_bond(stripped)
        except ValueError:
            kept.append(raw)
            continue
        if candidate == target and (denomination is None or (current_denom or denomination) == denomination):
            removed = True
            continue
        kept.append(raw)

    if removed:
        cleaned = _drop_empty_sections(kept)
        path.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
    return removed


def _drop_empty_sections(lines: list[str]) -> list[str]:
    kept: list[str] = []
    index = 0
    while index < len(lines):
        match = SECTION_RE.match(lines[index].strip())
        if not match:
            kept.append(lines[index])
            index += 1
            continue

        end = index + 1
        has_bond = False
        while end < len(lines) and not SECTION_RE.match(lines[end].strip()):
            stripped = lines[end].strip()
            if stripped and not stripped.startswith("#"):
                has_bond = True
            end += 1

        if has_bond:
            kept.extend(lines[index:end])
        index = end
    while kept and not kept[-1].strip():
        kept.pop()
    return kept


def _find_section_index(lines: list[str], denomination: int, owner: str | None) -> int | None:
    wanted_owner = owner or None
    for index, raw in enumerate(lines):
        match = SECTION_RE.match(raw.strip())
        if not match:
            continue
        label = (match.group("owner") or "").strip() or None
        if int(match.group("denom")) == denomination and label == wanted_owner:
            return index
    return None


def _section_append_index(lines: list[str], header_index: int) -> int:
    index = header_index + 1
    last_content = header_index + 1
    while index < len(lines):
        stripped = lines[index].strip()
        if SECTION_RE.match(stripped):
            break
        if stripped and not stripped.startswith("#"):
            last_content = index + 1
        index += 1
    return last_content
