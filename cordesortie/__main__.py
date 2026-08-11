from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .bot import CordeSortieBot


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit(
            "DISCORD_TOKEN manquant : copie .env.example vers .env et renseigne-le."
        )

    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    bot = CordeSortieBot(data_dir=data_dir)
    bot.run(token)


if __name__ == "__main__":
    main()
