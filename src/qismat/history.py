"""Local SQLite ledger of checks and wins."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from qismat.models import DrawResult, Win


@dataclass(frozen=True)
class HistoryWin:
    bond: str
    tier: str
    amount: str
    owner: str | None
    denomination: int
    draw_date: str
    checked_at: str


@dataclass(frozen=True)
class HistoryCheck:
    id: int
    checked_at: str
    denomination: int
    draw_date: str
    draw_number: str | None
    city: str | None
    bond_count: int
    win_count: int
    source_url: str | None


@dataclass(frozen=True)
class HistoryStats:
    check_count: int
    win_count: int
    last_checked_at: str | None
    denominations: list[int]


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY,
                    checked_at TEXT NOT NULL,
                    denomination INTEGER NOT NULL,
                    draw_date TEXT NOT NULL,
                    draw_number TEXT,
                    city TEXT,
                    bond_count INTEGER NOT NULL,
                    win_count INTEGER NOT NULL,
                    source_url TEXT
                );
                CREATE TABLE IF NOT EXISTS wins (
                    id INTEGER PRIMARY KEY,
                    check_id INTEGER NOT NULL REFERENCES checks(id),
                    owner TEXT,
                    bond TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    amount TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_checks_draw
                    ON checks (denomination, draw_date);
                """
            )

    def has_check(self, denomination: int, draw_date: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM checks WHERE denomination = ? AND draw_date = ? LIMIT 1",
                (denomination, draw_date),
            ).fetchone()
        return row is not None

    def record(
        self,
        draw: DrawResult,
        bond_count: int,
        wins: list[Win],
        source_url: str | None = None,
        checked_at: str | None = None,
    ) -> int:
        stamp = checked_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO checks (
                    checked_at, denomination, draw_date, draw_number, city,
                    bond_count, win_count, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stamp,
                    draw.denomination,
                    draw.draw_date,
                    draw.draw_number,
                    draw.city,
                    bond_count,
                    len(wins),
                    source_url,
                ),
            )
            check_id = int(cursor.lastrowid)
            connection.executemany(
                "INSERT INTO wins (check_id, owner, bond, tier, amount) VALUES (?, ?, ?, ?, ?)",
                [(check_id, win.owner, win.bond, win.tier, win.amount) for win in wins],
            )
        return check_id

    def recent_checks(self, limit: int = 50) -> list[HistoryCheck]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM checks ORDER BY checked_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._check_from_row(row) for row in rows]

    def all_wins(self, limit: int = 100) -> list[HistoryWin]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    wins.bond, wins.tier, wins.amount, wins.owner,
                    checks.denomination, checks.draw_date, checks.checked_at
                FROM wins
                JOIN checks ON checks.id = wins.check_id
                ORDER BY checks.checked_at DESC, wins.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            HistoryWin(
                bond=row["bond"],
                tier=row["tier"],
                amount=row["amount"],
                owner=row["owner"],
                denomination=row["denomination"],
                draw_date=row["draw_date"],
                checked_at=row["checked_at"],
            )
            for row in rows
        ]

    def stats(self) -> HistoryStats:
        with self._connect() as connection:
            check_count = connection.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
            win_count = connection.execute("SELECT COUNT(*) FROM wins").fetchone()[0]
            last = connection.execute(
                "SELECT checked_at FROM checks ORDER BY checked_at DESC, id DESC LIMIT 1"
            ).fetchone()
            denoms = connection.execute(
                "SELECT DISTINCT denomination FROM checks ORDER BY denomination"
            ).fetchall()
        return HistoryStats(
            check_count=int(check_count),
            win_count=int(win_count),
            last_checked_at=last["checked_at"] if last else None,
            denominations=[int(row["denomination"]) for row in denoms],
        )

    @staticmethod
    def _check_from_row(row: sqlite3.Row) -> HistoryCheck:
        return HistoryCheck(
            id=row["id"],
            checked_at=row["checked_at"],
            denomination=row["denomination"],
            draw_date=row["draw_date"],
            draw_number=row["draw_number"],
            city=row["city"],
            bond_count=row["bond_count"],
            win_count=row["win_count"],
            source_url=row["source_url"],
        )
