"""Liste des sites supportés — voir docs/SITES.md pour le détail par site.

Un profil de filtre peut référencer un site ici même si son adapter de scraping
n'existe pas encore (cordesortie/scraper/registry.py) — il ne renverra juste aucun
item tant que Phase 4 n'est pas terminée pour ce site.
"""

from __future__ import annotations

SUPPORTED_SITES: tuple[str, ...] = (
    "auchan",
    "leclerc",
    "carrefour",
    "fnac",
    "joueclub",
    "cultura",
    "kingjouet",
    "philibert",
    "ludifolie",
    "micromania",
    "comptoirdesecoliers",
    "latavernededream",
    "outpost",
    "dracaustore",
)

# Notes affichées par /sites pour les cas particuliers (voir docs/SITES.md).
SITE_NOTES: dict[str, str] = {
    "fnac": "bloqué par un CAPTCHA Datadome, pas d'adapter prévu",
    "kingjouet": "bloqué par un CAPTCHA Datadome, pas d'adapter prévu",
    "outpost": "bloqué par Cloudflare, pas d'adapter prévu",
    "comptoirdesecoliers": "site instable pendant le scrape (rechargement en plein milieu), adapter désactivé",
    "philibert": "moteur de recherche instable en automatisation, adapter désactivé",
}
