"""Lecture/écriture de la config JSON par serveur.

Le fichier vit sous ``<DATA_DIR>/<guild_id>/config.json``. En prod (Railway/Render),
DATA_DIR doit pointer vers un volume persistant — voir docs/ARCHITECTURE.md §6.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .models import GuildConfig


class ConfigError(Exception):
    """Le fichier de config existe mais ne respecte pas le schéma attendu."""


class ConfigStore:
    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)

    def _path(self, guild_id: int) -> Path:
        return self.data_dir / str(guild_id) / "config.json"

    def load(self, guild_id: int) -> GuildConfig:
        path = self._path(guild_id)
        if not path.exists():
            config = GuildConfig()
            self.save(guild_id, config)
            return config

        try:
            return GuildConfig.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            raise ConfigError(
                f"Config invalide pour le serveur {guild_id} ({path}) : {exc}"
            ) from exc

    def save(self, guild_id: int, config: GuildConfig) -> None:
        path = self._path(guild_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
