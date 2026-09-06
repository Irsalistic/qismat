"""MCP server so agents can add bonds, check draws, and read history.

Run with:

    python -m qismat.mcp_server

Cursor config lives in .cursor/mcp.json. Bond numbers stay on this machine.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from qismat.actions import (
    add_from_speech,
    add_numbers,
    history_file_for,
    history_payload,
    portfolio_payload,
    remove_number,
    resolve_bonds_file,
)
from qismat.constants import DEFAULT_DENOMINATION, SUPPORTED_DENOMINATIONS
from qismat.envfile import load_dotenv
from qismat.history import HistoryStore
from qismat.portfolio import load_portfolio
from qismat.service import check_portfolio

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "MCP SDK 2.x is required. Run: pip install -e \".[mcp]\""
    ) from exc

mcp = MCPServer(
    name="qismat",
    title="Qismat",
    instructions=(
        "Local Pakistani prize-bond helper. Bond numbers never leave this computer. "
        "Use add_bond or add_bonds_from_speech to save numbers, list_bonds to inspect "
        "the portfolio, check_latest_draws to match them against allprizebond.pk, and "
        "get_history / get_wins for the local ledger. Denominations: "
        + ", ".join(map(str, SUPPORTED_DENOMINATIONS))
        + "."
    ),
)


def _bonds_file() -> Path:
    return resolve_bonds_file(None)


def _ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def _err(message: str, *, hint: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"ok": False, "error": message}
    if hint:
        body["hint"] = hint
    return body


@mcp.tool()
def add_bond(
    number: str,
    denomination: int = DEFAULT_DENOMINATION,
    owner: str = "",
) -> dict[str, Any]:
    """Add one prize bond to the local portfolio.

    Args:
        number: 6-digit bond number, for example 477670 or 022667.
        denomination: Face value. One of 100, 200, 750, 1500, 7500, 15000, 25000, 40000.
        owner: Optional family label, for example parents or ali.
    """
    if denomination not in SUPPORTED_DENOMINATIONS:
        return _err(
            f"Unsupported denomination {denomination}.",
            hint="Use one of: " + ", ".join(map(str, SUPPORTED_DENOMINATIONS)),
        )
    try:
        result = add_numbers(_bonds_file(), [number], denomination, owner.strip() or None)
    except ValueError as exc:
        return _err(str(exc), hint="Pass a 6-digit number such as 477670.")
    return _ok(
        added=result.added,
        skipped=result.skipped,
        denomination=result.denomination,
        owner=result.owner,
        message=result.message,
    )


@mcp.tool()
def add_bonds_from_speech(
    transcript: str,
    denomination: int = DEFAULT_DENOMINATION,
    owner: str = "",
) -> dict[str, Any]:
    """Parse spoken digits (English or Urdu) and add the bond numbers.

    Example transcript: "four seven seven six seven zero for parents".
    """
    try:
        result = add_from_speech(_bonds_file(), transcript, denomination, owner.strip() or None)
    except ValueError as exc:
        return _err(
            str(exc),
            hint="Say six digits, like 'four seven seven six seven zero'.",
        )
    return _ok(
        added=result.added,
        skipped=result.skipped,
        denomination=result.denomination,
        owner=result.owner,
        heard=result.heard,
        warnings=result.warnings,
        confirmation=result.confirmation,
        message=result.message,
    )


@mcp.tool()
def list_bonds() -> dict[str, Any]:
    """List every prize bond stored on this computer."""
    return _ok(**portfolio_payload(_bonds_file()))


@mcp.tool()
def remove_bond(number: str, denomination: int | None = None) -> dict[str, Any]:
    """Remove a prize bond number from the local portfolio."""
    try:
        removed = remove_number(_bonds_file(), number, denomination)
    except ValueError as exc:
        return _err(str(exc))
    if not removed:
        return _err("Bond not found.", hint="Call list_bonds to see stored numbers.")
    return _ok(removed=number, denomination=denomination, message=f"Removed {number}.")


@mcp.tool()
def check_latest_draws(force: bool = False) -> dict[str, Any]:
    """Check the latest published draw for every denomination in the portfolio.

    Args:
        force: If true, re-fetch even when that draw is already in history.
    """
    path = _bonds_file()
    try:
        portfolio = load_portfolio(path)
    except FileNotFoundError:
        return _err("No bonds.txt found.", hint="Add a bond first with add_bond.")
    except ValueError as exc:
        return _err(str(exc))

    outcomes = check_portfolio(
        portfolio,
        check_all=True,
        use_latest=True,
        history=HistoryStore(history_file_for(path)),
        skip_checked=not force,
    )
    return _ok(results=[item.to_dict() for item in outcomes])


@mcp.tool()
def get_history(limit: int = 20) -> dict[str, Any]:
    """Return recent draw checks and recorded wins from local history."""
    limit = max(1, min(limit, 100))
    return _ok(**history_payload(_bonds_file(), limit))


@mcp.tool()
def get_wins(limit: int = 50) -> dict[str, Any]:
    """Return only recorded winning bonds from local history."""
    limit = max(1, min(limit, 100))
    payload = history_payload(_bonds_file(), limit)
    return _ok(wins=payload["wins"], win_count=payload["win_count"])


@mcp.resource("prizebonds://portfolio")
def portfolio_resource() -> str:
    """Current local prize-bond list as JSON."""
    import json

    return json.dumps(portfolio_payload(_bonds_file()), indent=2)


@mcp.resource("prizebonds://history")
def history_resource() -> str:
    """Local check ledger as JSON."""
    import json

    return json.dumps(history_payload(_bonds_file()), indent=2)


def main() -> None:
    load_dotenv()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
