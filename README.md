# CordeSortie

Bot Discord de veille sur des items Pokémon en vente sur des sites marchands français
(Carrefour, JouéClub, Leclerc, Auchan, Cultura), avec filtres configurables par
commande Discord et alertes en temps quasi réel dans des salons dédiés.

*CordeSortie* : la corde qui te sort de la galère de surveiller les sites toi-même.

## Statut

Fonctionnel, testé en usage réel. Tourne en local pour l'instant — voir
[docs/TASKS.md](docs/TASKS.md) pour la roadmap détaillée et l'état d'avancement par
phase.

## Fonctionnalités

- **Création de filtre guidée** (`/filtre add`) : menu à cocher pour les sites, puis un
  formulaire ("doit contenir tous ces mots" / "au moins un de ces mots" / "ne doit pas
  contenir") — le bot compose l'expression texte automatiquement, rien à taper à la
  main. Recherche insensible à la casse et aux accents ("pokemon" = "Pokémon").
  L'expression texte reste éditable à la main (`ET`/`OU`/`NON`, parenthèses) via
  `/filtre edit` et testable via `/filtre test` pour les cas avancés. Modifiable après
  coup (`/filtre edit`) sans supprimer/recréer.
- **Multi-sites** : Carrefour, JouéClub, Leclerc, Auchan, Cultura fonctionnels. Fnac et
  King Jouet bloqués par un CAPTCHA Datadome (pas d'adapter, volontairement — voir
  [docs/SITES.md](docs/SITES.md) pour le détail, y compris les sites évalués et écartés).
- **Un salon Discord dédié par filtre**, auto-créé/supprimé, pour ne jamais mélanger
  les alertes de plusieurs profils. Optionnellement privé (`private:true`, visible
  uniquement par le créateur + les admins).
- **Salon tableau de bord**, **salon d'aide** et **salon log** auto-créés et toujours à
  jour (flux d'évènements en direct + résumé périodique pour ce dernier) — rien à
  configurer à la main.
- **`/stats`** : statistiques de scrape sur une période + total d'alertes par profil.
- **Anti-détection** : intervalle de scrape jitté, plancher dur à 1 minute (non
  contournable), backoff exponentiel sur erreur, détection de CAPTCHA/challenge.
- **`/pause`/`/resume`** (global) et **`/filtre pause`/`/filtre resume`** (par profil)
  pour couper le scraping en cas de doute.

## Stack

Python 3.13, discord.py, Playwright (Chromium), SQLite (aiosqlite), Pydantic. Détails
dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Installation

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash) — .venv/bin/activate sur Linux/Mac
pip install -r requirements.txt
playwright install chromium
```

Copie `.env.example` vers `.env` et renseigne `DISCORD_TOKEN` (voir section suivante
pour l'obtenir).

## Créer et inviter le bot Discord

1. https://discord.com/developers/applications → **New Application**.
2. Onglet **Bot** → **Reset Token**, copie-le dans `.env`. Désactive **Public Bot**
   (usage perso).
3. Onglet **Installation** → **Install Link** → **None** (obligatoire pour une appli
   privée).
4. Onglet **OAuth2** → **URL Generator** → coche les scopes `bot` **et**
   `applications.commands` (les deux, sinon les commandes n'apparaissent jamais côté
   Discord) → coche au minimum `Send Messages`, `Manage Channels`, `Embed Links`,
   `Read Message History` dans les permissions bot.
5. Ouvre l'URL générée, choisis ton serveur, autorise.

## Lancer le bot

```bash
python -m cordesortie
```

Au premier démarrage, le bot crée automatiquement une catégorie **CordeSortie** avec
un salon tableau de bord, un salon d'aide (`cordesortie-aide` liste toutes les
commandes disponibles, toujours à jour) et un salon log (flux d'évènements du bot).

## Premiers pas

1. `/filtre add name:test` — choisis les sites dans le menu, puis remplis juste
   "Doit contenir TOUS ces mots" avec `pokemon` dans le formulaire qui s'ouvre (large,
   pour voir le système fonctionner).
2. `/filtre dry-run name:test` — scrape en direct et montre ce qui matcherait, sans
   créer d'alertes ni toucher à la dédup.
3. Une fois convaincu, affine les conditions avec `/filtre edit` et laisse tourner —
   les alertes arrivent dans le salon dédié au filtre.
4. `/sites` pour voir le statut de chaque site, `/pause` pour tout arrêter en urgence.
5. Le salon log (créé automatiquement) suit l'activité du bot ; `/config
   set-log-channel` permet de le rediriger vers un autre salon si besoin.

Liste complète des commandes : salon `cordesortie-aide` une fois le bot lancé, ou
`docs/`.

## Déploiement

Un `Dockerfile` prêt à l'emploi existe (`docker build -t cordesortie .`), testé en
local avec Playwright fonctionnel dedans. Le déploiement cloud (Render/Railway/Oracle
Cloud) est en pause — voir [docs/TASKS.md](docs/TASKS.md) Phase 8 pour le pourquoi et
l'état des options explorées.

## Documentation

- [docs/PRD.md](docs/PRD.md) — fonctionnalités et périmètre
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — design technique
- [docs/SITES.md](docs/SITES.md) — sites cibles et leur statut
- [docs/TASKS.md](docs/TASKS.md) — roadmap détaillée, à jour
- [docs/RISKS.md](docs/RISKS.md) — critique, risques légaux/techniques
- [CLAUDE.md](CLAUDE.md) — guide pour contribuer avec Claude Code

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Usage prévu

Outil de veille personnelle, pas un outil d'achat automatique. Voir la section
"Risque légal" de [docs/RISKS.md](docs/RISKS.md) avant tout déploiement à plus grande
échelle.
