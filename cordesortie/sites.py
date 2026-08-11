"""Liste des sites supportés — voir docs/SITES.md pour le détail par site.

Reste une simple liste de noms tant que les adapters de scraping (Phase 4)
n'existent pas encore ; un profil de filtre référence un site par son nom ici.
"""

from __future__ import annotations

SUPPORTED_SITES: tuple[str, ...] = ("auchan", "leclerc", "carrefour", "fnac")
