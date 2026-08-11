# CLAUDE.md

Ce fichier guide Claude Code (et tout futur contributeur IA) sur ce dépôt.

## Le projet en une phrase

**CordeSortie** est un bot Discord qui scrape en continu des sites marchands (Auchan,
Leclerc, Carrefour, Fnac, etc.) à la recherche d'items Pokémon correspondant à des
filtres définis par l'utilisateur (texte contenu, prix, disponibilité), et alerte sur un
salon Discord dédié quand un item matche.

Nom du projet : *CordeSortie* = "la corde qui te sort de la galère de chercher un item
en rupture / une bonne affaire toi-même".

## Stack retenue

- **Langage** : Python 3.12+
- **Bot Discord** : `discord.py` (slash commands)
- **Scraping** : Playwright (navigateur headless) pour tous les sites — nécessaire face
  aux antibots type Cloudflare/Datadome présents sur la plupart des enseignes visées.
  Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour la discussion coût/perf.
- **Stockage** : SQLite (fichier local, via `sqlite3`/`sqlalchemy` ou `aiosqlite`)
- **Config utilisateur** : double interface — commandes slash Discord qui lisent/écrivent
  un fichier de config lisible (JSON) par serveur. Le fichier reste la source de vérité,
  les commandes sont une couche UX au-dessus.
- **Scheduler** : boucle asyncio interne avec délai *jitteré* (jamais un intervalle fixe)
  et plancher dur à 60s pour éviter le ban antibot.

## Documents de cadrage

- [docs/PRD.md](docs/PRD.md) — fonctionnalités, périmètre, UX des filtres et des salons.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — découpage technique, schéma DB, moteur
  de scraping, moteur de filtres, anti-détection.
- [docs/SITES.md](docs/SITES.md) — liste des sites cibles et notes par site (antibot,
  structure, statut de l'adapter).
- [docs/TASKS.md](docs/TASKS.md) — liste de tâches par phase, à cocher au fur et à mesure.
- [docs/RISKS.md](docs/RISKS.md) — critique du projet, risques légaux/techniques,
  pistes d'amélioration.

Lire le PRD et l'ARCHITECTURE avant toute implémentation. Mettre à jour TASKS.md en
cochant les tâches complétées au fur et à mesure — c'est la source de vérité sur l'état
d'avancement, pas la mémoire de la conversation.

## Conventions de travail

- Un **adapter par site** (`sites/auchan.py`, `sites/leclerc.py`, ...) implémentant une
  interface commune (`fetch_items() -> list[Item]`). Ne jamais mettre de logique
  site-spécifique ailleurs que dans son adapter.
- Le **moteur de filtres** est générique et ne connaît aucun site : il reçoit des `Item`
  normalisés (titre, prix, dispo, url, site) et évalue une expression de filtre
  (AND/OR sur des `contains`) fournie par l'utilisateur.
- Toute requête HTTP/navigateur doit passer par le rate limiter central — pas d'appel
  direct à un site depuis un adapter en dehors du scheduler.
- Ne jamais committer de secrets (token Discord, cookies de session) : `.env` est
  gitignore, utiliser `.env.example` comme référence.
- Pas de dépendances lourdes non justifiées : l'objectif annoncé est un outil **léger et
  performant**. Toute nouvelle dépendance doit se justifier dans le PR/commit.

## Commandes utiles (à compléter au fur et à mesure du setup)

```bash
# Installation
pip install -r requirements.txt
playwright install chromium

# Lancer le bot
python -m cordesortie
```

## État du projet

Projet en phase de cadrage (pas encore de code). Voir [docs/TASKS.md](docs/TASKS.md)
pour la roadmap.
