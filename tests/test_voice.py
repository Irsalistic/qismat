from pathlib import Path

import pytest

from qismat.actions import add_from_speech
from qismat.voice import parse_spoken_add


def test_spoken_digit_words():
    parsed = parse_spoken_add("four seven seven six seven zero")
    assert parsed.numbers == ["477670"]
    assert parsed.denomination is None


def test_spoken_oh_for_leading_zero():
    parsed = parse_spoken_add("oh two two six six seven")
    assert parsed.numbers == ["022667"]


def test_spoken_numeric_string():
    parsed = parse_spoken_add("add 477670")
    assert parsed.numbers == ["477670"]


def test_spoken_denomination_and_owner():
    parsed = parse_spoken_add("two hundred bond four seven seven six seven zero for parents")
    assert parsed.numbers == ["477670"]
    assert parsed.denomination == 200
    assert parsed.owner == "parents"


def test_spoken_prefix_denomination_digits():
    parsed = parse_spoken_add("200 477670")
    assert parsed.numbers == ["477670"]
    assert parsed.denomination == 200


def test_spoken_double_and_urdu():
    parsed = parse_spoken_add("double four saat saat char do do")
    assert parsed.numbers == ["447742"]


def test_spoken_five_digits_pads_zero():
    parsed = parse_spoken_add("two two six six seven")
    assert parsed.numbers == ["022667"]
    assert parsed.warnings


def test_spoken_two_bonds():
    parsed = parse_spoken_add("477670 022667")
    assert parsed.numbers == ["477670", "022667"]


def test_spoken_urdu_script_digits():
    parsed = parse_spoken_add("۴۷۷۶۷۰")
    assert parsed.numbers == ["477670"]


def test_spoken_empty_raises():
    with pytest.raises(ValueError, match="did not hear"):
        parse_spoken_add("   ")


def test_add_from_speech_writes_file(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    result = add_from_speech(path, "four seven seven six seven zero for ali", 200)
    assert result.added == ["477670"]
    assert result.owner == "ali"
    assert "Added 477670" in result.message
    text = path.read_text(encoding="utf-8")
    assert "477670" in text
    assert "[200:ali]" in text

    again = add_from_speech(path, "477670 for ali", 200)
    assert again.added == []
    assert again.skipped == ["477670"]
