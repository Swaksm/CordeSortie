"""Schéma de la configuration par serveur Discord.

Ce fichier JSON (un par serveur) est la source de vérité de la config — voir
docs/ARCHITECTURE.md. Les profils de filtre arrivent en phase 3 ; pour l'instant
seuls les salons et l'intervalle de log sont modélisés.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChannelRole(str, Enum):
    CONFIG = "config"
    ALERTE = "alerte"
    LOG = "log"


class GuildConfig(BaseModel):
    channels: dict[ChannelRole, int] = Field(default_factory=dict)
    log_interval_minutes: int = 15

    def channel_id(self, role: ChannelRole) -> int | None:
        return self.channels.get(role)
