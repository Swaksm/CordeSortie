# CordeSortie

Bot Discord de veille sur des items Pokémon en vente sur des sites marchands français
(Carrefour, JouéClub, Leclerc, Auchan), avec filtres configurables par commande Discord
et alertes en temps quasi réel dans des salons dédiés.

*CordeSortie* : la corde qui te sort de la galère de surveiller les sites toi-même.

## Statut

Fonctionnel, testé en usage réel. Tourne en local pour l'instant — voir
[docs/TASKS.md](docs/TASKS.md) pour la roadmap détaillée et l'état d'avancement par
phase.

## Fonctionnalités

- **Filtres par commande Discord** : expressions `contient("X") ET/OU/NON contient("Y")`
  avec parenthèses, plus prix min/max et disponibilité.
- **Multi-sites** : Carrefour, JouéClub, Leclerc, Auchan fonctionnels. Fnac bloqué par
  un CAPTCHA Datadome (pas d'adapter, volontairement — voir [docs/SITES.md](docs/SITES.md)).
- **Un salon Discord dédié par filtre**, auto-créé/supprimé, pour ne jamais mélanger
  les alertes de plusieurs profils.
- **Salon tableau de bord** et **salon d'aide** auto-générés et toujours à jour.
- **Salon log** : flux d'évènements en direct + résumé périodique.
- **Anti-détection** : intervalle de scrape jitté, plancher dur à 1 minute (non
  contournable), backoff exponentiel sur erreur, détection de CAPTCHA/challenge.
- **`/pause` et `/resume`** pour couper le scraping immédiatement en cas de doute.

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
un salon info et un salon d'aide (`cordesortie-aide` liste toutes les commandes
disponibles, toujours à jour).

## Premiers pas

1. `/config set-log-channel channel:#un-salon` — pour suivre l'activité du bot.
2. `/filtre add name:test sites:carrefour,joueclub expression:contient("pokemon")` —
   crée un premier filtre (large, pour voir le système fonctionner).
3. `/filtre dry-run name:test` — scrape en direct et montre ce qui matcherait, sans
   créer d'alertes ni toucher à la dédup.
4. Une fois convaincu, affine avec une expression plus précise et laisse tourner —
   les alertes arrivent dans le salon dédié au filtre.
5. `/sites` pour voir le statut de chaque site, `/pause` pour tout arrêter en urgence.

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
