import asyncio
import tempfile
from pathlib import Path

from cordesortie.storage import Database


def run(coro):
    return asyncio.run(coro)


def test_upsert_new_item_notifies():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            result = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            await db.close()
            return result

    result = run(scenario())
    assert result.is_new
    assert result.should_notify


def test_upsert_unchanged_item_does_not_notify():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            result = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            await db.close()
            return result

    result = run(scenario())
    assert not result.is_new
    assert not result.should_notify


def test_upsert_price_change_notifies():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            result = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=40.0, available=True,
            )
            await db.close()
            return result

    result = run(scenario())
    assert result.should_notify


def test_upsert_out_of_stock_does_not_notify_but_restock_does():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            out_of_stock = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=False,
            )
            restocked = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            await db.close()
            return out_of_stock, restocked

    out_of_stock, restocked = run(scenario())
    assert not out_of_stock.should_notify
    assert restocked.should_notify


def test_dedup_is_scoped_per_alert_channel():
    """Deux profils differents (donc deux salons differents) qui matchent le meme
    item doivent chacun etre notifies independamment - voir docs/ARCHITECTURE.md."""

    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            first = await db.upsert_seen_item(
                alert_channel_id=1, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            second = await db.upsert_seen_item(
                alert_channel_id=2, site="carrefour", item_key="abc",
                title="Coffret", price=50.0, available=True,
            )
            await db.close()
            return first, second

    first, second = run(scenario())
    assert first.should_notify
    assert second.should_notify


def test_record_and_query_scrape_runs():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.db")
            await db.connect()
            await db.record_scrape_run(
                site="carrefour", started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:05+00:00", items_found=10, matched=2,
            )
            rows = await db.runs_since("2026-01-01T00:00:00+00:00")
            await db.close()
            return rows

    rows = run(scenario())
    assert len(rows) == 1
    assert rows[0]["site"] == "carrefour"
    assert rows[0]["items_found"] == 10
