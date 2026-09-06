"""Turn spoken English or Urdu into prize-bond numbers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from qismat.bonds import normalize_bond
from qismat.constants import DEFAULT_DENOMINATION, SUPPORTED_DENOMINATIONS

WORD_TO_DIGIT = {
    "nought": "0",
    "zero": "0",
    "oh": "0",
    "nil": "0",
    "sifar": "0",
    "sifer": "0",
    "صفر": "0",
    "one": "1",
    "aik": "1",
    "ek": "1",
    "یک": "1",
    "ایک": "1",
    "two": "2",
    "do": "2",
    "دو": "2",
    "three": "3",
    "teen": "3",
    "تین": "3",
    "four": "4",
    "char": "4",
    "چار": "4",
    "five": "5",
    "panch": "5",
    "paanch": "5",
    "پانچ": "5",
    "six": "6",
    "chhe": "6",
    "che": "6",
    "chay": "6",
    "چھ": "6",
    "seven": "7",
    "saat": "7",
    "سات": "7",
    "eight": "8",
    "aath": "8",
    "ath": "8",
    "آٹھ": "8",
    "nine": "9",
    "nau": "9",
    "نو": "9",
}

INDIC_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

REPEAT_WORDS = {
    "double": 2,
    "dabal": 2,
    "دوگنا": 2,
    "triple": 3,
    "tirpal": 3,
}

SKIP_WORDS = {
    "add",
    "bond",
    "bonds",
    "prize",
    "number",
    "numbers",
    "please",
    "my",
    "the",
    "a",
    "an",
    "rs",
    "rupee",
    "rupees",
    "rupay",
    "rupe",
    "denomination",
    "latest",
    "check",
    "and",
    "then",
}

DENOM_PHRASES: list[tuple[str, int]] = [
    ("forty thousand", 40000),
    ("40 thousand", 40000),
    ("twenty five thousand", 25000),
    ("twenty-five thousand", 25000),
    ("25 thousand", 25000),
    ("fifteen thousand", 15000),
    ("15 thousand", 15000),
    ("seven thousand five hundred", 7500),
    ("7 thousand 5 hundred", 7500),
    ("fifteen hundred", 1500),
    ("15 hundred", 1500),
    ("one thousand five hundred", 1500),
    ("seven hundred fifty", 750),
    ("seven fifty", 750),
    ("two hundred", 200),
    ("do sau", 200),
    ("one hundred", 100),
    ("ek sau", 100),
]

OWNER_PATTERNS = [
    re.compile(r"\b(?:for|owner|belongs to|of)\s+([a-zA-Z][a-zA-Z0-9 _-]{0,40})\b", re.I),
    re.compile(r"\b(?:کے لیے|کی)\s+(\S+)", re.I),
]


@dataclass
class SpokenAdd:
    numbers: list[str]
    denomination: int | None = None
    owner: str | None = None
    heard: str = ""
    warnings: list[str] = field(default_factory=list)


def parse_spoken_add(transcript: str) -> SpokenAdd:
    """Parse a voice transcript into one or more 6-digit bond numbers."""
    raw = (transcript or "").strip()
    if not raw:
        raise ValueError("I did not hear anything. Say the six digits of the bond.")

    text = raw.translate(INDIC_DIGITS)
    text = text.replace("-", " ").replace(",", " ")
    text = re.sub(r"[.!?]+", " ", text)
    lowered = text.lower()

    denomination = _extract_denomination(lowered)
    owner = _extract_owner(lowered)
    digits = _tokens_to_digits(lowered, denomination)
    numbers, warnings = _digits_to_bonds(digits, denomination)

    if not numbers:
        raise ValueError(
            f"I heard {raw!r} but could not find a 6-digit bond number. "
            "Try: 'four seven seven six seven zero'."
        )

    return SpokenAdd(
        numbers=numbers,
        denomination=denomination,
        owner=owner,
        heard=raw,
        warnings=warnings,
    )


def spoken_confirmation(parsed: SpokenAdd, denomination: int) -> str:
    parts = []
    for number in parsed.numbers:
        spaced = " ".join(number)
        parts.append(spaced)
    label = ", ".join(parts)
    text = f"Added bond {label}, {denomination} rupees"
    if parsed.owner:
        text += f", for {parsed.owner}"
    return text + "."


def _extract_denomination(text: str) -> int | None:
    for phrase, value in DENOM_PHRASES:
        if phrase in text:
            return value
    match = re.search(r"\b(?:rs|rupees?|rupay)?\s*(" + "|".join(map(str, SUPPORTED_DENOMINATIONS)) + r")\b", text)
    if match:
        return int(match.group(1))
    return None


def _extract_owner(text: str) -> str | None:
    for pattern in OWNER_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        owner = match.group(1).strip(" .")
        owner = re.sub(r"\b(bond|bonds|please|rupees?|rs)\b", "", owner, flags=re.I).strip()
        if owner and owner not in SKIP_WORDS and owner not in WORD_TO_DIGIT:
            return owner
    return None


def _tokens_to_digits(text: str, denomination: int | None) -> str:
    cleaned = text
    for phrase, _value in DENOM_PHRASES:
        cleaned = cleaned.replace(phrase, " ")
    cleaned = re.sub(r"\b(?:for|owner|belongs to|of)\s+[a-zA-Z][a-zA-Z0-9 _-]{0,40}", " ", cleaned)
    if denomination is not None:
        cleaned = re.sub(rf"\b{denomination}\b", " ", cleaned)

    tokens = re.findall(r"[a-zA-Z]+|\d+", cleaned)
    digits: list[str] = []
    repeat = 1
    for token in tokens:
        if token in SKIP_WORDS:
            continue
        if token in REPEAT_WORDS:
            repeat = REPEAT_WORDS[token]
            continue
        if token.isdigit():
            digits.append(token * repeat if len(token) == 1 else token)
            repeat = 1
            continue
        digit = WORD_TO_DIGIT.get(token)
        if digit is not None:
            digits.append(digit * repeat)
            repeat = 1
    return "".join(digits)


def _digits_to_bonds(digits: str, denomination: int | None) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if not digits:
        return [], warnings

    if denomination is None:
        for denom in sorted(SUPPORTED_DENOMINATIONS, reverse=True):
            prefix = str(denom)
            rest = digits[len(prefix) :] if digits.startswith(prefix) else ""
            if rest and len(rest) % 6 == 0 and len(digits) > 6:
                denomination = denom
                digits = rest
                break

    if len(digits) == 5:
        warnings.append("Heard 5 digits; padded a leading zero.")
        digits = digits.zfill(6)

    if len(digits) < 6:
        return [], warnings

    leftover = len(digits) % 6
    if leftover:
        warnings.append(f"Ignored leftover digit(s): {digits[-leftover:]}")
        digits = digits[: len(digits) - leftover]

    numbers = [normalize_bond(digits[index : index + 6]) for index in range(0, len(digits), 6)]
    return numbers, warnings
