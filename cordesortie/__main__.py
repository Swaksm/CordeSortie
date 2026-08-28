from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .bot import CordeSortieBot


def main() -> None:
    load_dotenv()

    # Sur Windows, la console utilise l'encodage de la page de code active
    # (souvent cp1252/cp850), pas UTF-8 : les accents dans les logs (ex.
    # "Connecté") ressortent alors mal encodés. reconfigure() n'existe que sur
    # les flux qui le supportent (pas toujours le cas si stdout est redirigé).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

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
