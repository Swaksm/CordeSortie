"""Vérifie qu'un arrêt du bot (close(), déclenché par Ctrl+C en usage réel) ferme
proprement tout ce qui a été ouvert : navigateur Playwright, connexion SQLite,
tâches asyncio du scheduler. Pas de vérification via signal OS (pas de TTY
interactif en test) — on appelle close() directement et on vérifie l'état.
"""

import asyncio
import tempfile
from pathlib import Path

from cordesortie.bot import CordeSortieBot


def run(coro):
    return asyncio.run(coro)


def test_close_stops_browser_and_db():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            bot = CordeSortieBot(data_dir=Path(d))
            await bot._async_setup_hook()
            await bot.setup_hook()

            page = await bot.browser.new_page()
            await page.close()

            db_connected = bot.db._conn is not None
            browser_started = bot.browser._browser is not None

            await bot.close()

            return db_connected, browser_started, bot.db._conn, bot.browser._browser

    db_connected, browser_started, db_after, browser_after = run(scenario())
    assert db_connected
    assert browser_started
    assert db_after is None
    assert browser_after is None


def test_close_cancels_active_scheduler_tasks():
    async def scenario():
        with tempfile.TemporaryDirectory() as d:
            bot = CordeSortieBot(data_dir=Path(d))
            await bot._async_setup_hook()
            await bot.setup_hook()

            async def dummy_loop():
                await asyncio.sleep(3600)

            task = asyncio.create_task(dummy_loop())
            bot.scheduler._site_tasks[(123, "carrefour")] = task

            await bot.close()
            await asyncio.sleep(0.1)
            return task

    task = run(scenario())
    assert task.cancelled()
