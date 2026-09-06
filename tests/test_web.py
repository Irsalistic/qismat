from pathlib import Path

from qismat.models import Win
from qismat.service import CheckOutcome
from qismat.web.app import create_app


def test_dashboard_lists_bonds(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n[750:parents]\n111111\n", encoding="utf-8")
    client = create_app(bonds).test_client()

    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "022667" in body
    assert "parents" in body
    assert "Speak a number" in body
    assert "Qismat" in body


def test_add_bond_from_dashboard(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n", encoding="utf-8")
    client = create_app(bonds).test_client()

    response = client.post(
        "/bonds",
        data={"number": "436083", "denomination": "200", "owner": "ali"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "436083" in response.get_data(as_text=True)
    assert "ali" in bonds.read_text(encoding="utf-8")


def test_check_route_uses_service(monkeypatch, tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n", encoding="utf-8")

    fake = [
        CheckOutcome(
            denomination=200,
            bond_count=1,
            draw_date="2026-03-16",
            wins=[Win(bond="022667", tier="3rd", amount="Rs. 1,250")],
        )
    ]
    monkeypatch.setattr("qismat.web.app.check_portfolio", lambda *a, **k: fake)
    client = create_app(bonds).test_client()
    response = client.post("/check", data={"notify": "0"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "You won" in body
    assert "022667" in body


def test_voice_add_from_transcript(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n", encoding="utf-8")
    client = create_app(bonds).test_client()

    response = client.post(
        "/bonds/voice",
        data={"transcript": "four seven seven six seven zero for ali", "denomination": "200"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "477670" in body
    assert "ali" in body
    assert "477670" in bonds.read_text(encoding="utf-8")


def test_voice_add_rejects_blank(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n", encoding="utf-8")
    client = create_app(bonds).test_client()
    response = client.post("/bonds/voice", data={"transcript": "hello there"}, follow_redirects=True)
    assert response.status_code == 200
    assert "could not find a 6-digit" in response.get_data(as_text=True)
