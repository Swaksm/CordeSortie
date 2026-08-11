"""Accès SQLite asynchrone : historique des items vus (dédup) et runs de scrape.

Un seul fichier DB pour tout le bot (pas par serveur).

La dédup est scopée par (alert_channel_id, site, item_key) et non par (site,
item_key) seul : deux profils de filtre différents qui matchent le même item
doivent chacun recevoir leur propre alerte dans leur propre salon, avec leur
propre historique de dédup — alert_channel_id est un identifiant stable et
unique par profil (voir docs/ARCHITECTURE.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from .models import UpsertResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_items (
    alert_channel_id INTEGER NOT NULL,
    site TEXT NOT NULL,
    item_key TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL,
    available INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (alert_channel_id, site, item_key)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    items_found INTEGER NOT NULL DEFAULT 0,
    matched INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() n'a pas été appelé")
        return self._conn

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> Database:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def upsert_seen_item(
        self,
        *,
        alert_channel_id: int,
        site: str,
        item_key: str,
        title: str,
        price: float | None,
        available: bool,
    ) -> UpsertResult:
        """Insère ou met à jour un item. Ne redéclenche `changed` que si le prix
        a changé ou si l'item redevient disponible après une rupture — voir
        docs/PRD.md §3.5 (anti-doublon)."""
        now = _now()
        async with self.conn.execute(
            """SELECT price, available FROM seen_items
               WHERE alert_channel_id = ? AND site = ? AND item_key = ?""",
            (alert_channel_id, site, item_key),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            await self.conn.execute(
                """INSERT INTO seen_items
                   (alert_channel_id, site, item_key, title, price, available,
                    first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (alert_channel_id, site, item_key, title, price, int(available), now, now),
            )
            await self.conn.commit()
            return UpsertResult(is_new=True, changed=True)

        previous_price, previous_available = row["price"], bool(row["available"])
        became_available = available and not previous_available
        price_changed = price is not None and previous_price != price
        changed = became_available or price_changed

        await self.conn.execute(
            """UPDATE seen_items
               SET title = ?, price = ?, available = ?, last_seen_at = ?
               WHERE alert_channel_id = ? AND site = ? AND item_key = ?""",
            (title, price, int(available), now, alert_channel_id, site, item_key),
        )
        await self.conn.commit()
        return UpsertResult(is_new=False, changed=changed)

    async def record_scrape_run(
        self,
        *,
        site: str,
        started_at: str,
        finished_at: str | None,
        items_found: int,
        matched: int,
        error: str | None = None,
    ) -> None:
        await self.conn.execute(
            """INSERT INTO scrape_runs
               (site, started_at, finished_at, items_found, matched, error)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (site, started_at, finished_at, items_found, matched, error),
        )
        await self.conn.commit()

    async def runs_since(self, since_iso: str) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            """SELECT site, items_found, matched, error FROM scrape_runs
               WHERE started_at >= ? ORDER BY started_at""",
            (since_iso,),
        ) as cursor:
            return await cursor.fetchall()
