# CordeSortie

Bot Discord de veille sur des items Pokémon en vente sur des sites marchands français
(Carrefour, JouéClub, Leclerc, Auchan, Cultura, Ludifolie, Micromania, La Taverne
de Dream), avec filtres configurables par
commande Discord et alertes en temps quasi réel dans des salons dédiés.

*CordeSortie* : la corde qui te sort de la galère de surveiller les sites toi-même.

## Statut

Fonctionnel, testé en usage réel. Tourne en local pour l'instant — voir
[docs/TASKS.md](docs/TASKS.md) pour la roadmap détaillée et l'état d'avancement par
phase.

## Fonctionnalités

- **Création et modification de filtre guidées** (`/filtre add`, `/filtre edit`) : menu
  à cocher pour les sites (jamais de nom de site à taper à la main), puis un formulaire
  ("doit contenir tous ces mots" / "au moins un de ces mots" / "ne doit pas contenir")
  — le bot compose l'expression texte automatiquement. `/filtre edit` pré-remplit tout
  avec les valeurs actuelles du profil (modifiable sans supprimer/recréer). Recherche
  insensible à la casse et aux accents ("pokemon" = "Pokémon"). Expression en texte
  libre (`ET`/`OU`/`NON`, parenthèses) toujours possible via `/filtre test` pour un cas
  plus avancé.
- **Multi-sites** : Carrefour, JouéClub, Leclerc, Auchan, Cultura, Ludifolie, Micromania,
  La Taverne de Dream, Dracaustore fonctionnels. Fnac, King Jouet et Outpost Brussels bloqués par un
  antibot (CAPTCHA Datadome / Cloudflare) — voir [docs/SITES.md](docs/SITES.md) pour le
  détail complet, y compris les sites évalués, écartés ou trop instables pour être
  activés malgré un adapter écrit.
- **Un salon Discord dédié par filtre**, auto-créé/supprimé, pour ne jamais mélanger
  les alertes de plusieurs profils. Optionnellement privé (`private:true`, visible
  uniquement par le créateur + les admins). Chaque alerte ghost ping le créateur du
  profil (ping + suppression immédiate, x5) pour une notification garantie sans
  polluer le salon de mentions qui restent.
- **Salon tableau de bord**, **salon d'aide** et **salon log** auto-créés et toujours à
  jour (flux d'évènements en direct + résumé périodique pour ce dernier) — rien à
  configurer à la main. Salons orphelins/dupliqués nettoyés automatiquement à chaque
  connexion.
- **`/stats`** : statistiques de scrape sur une période + total d'alertes par profil.
- **Anti-détection** : intervalle de scrape jitté, plancher dur à 1 minute (non
  contournable), backoff exponentiel sur erreur, détection de CAPTCHA/challenge.
- **`/pause`/`/resume`** (global) et **`/filtre pause`/`/filtre resume`** (par profil)
  pour couper le scraping en cas de doute.

## Stack

Python 3.12+, discord.py, Playwright (Chromium), SQLite (aiosqlite), Pydantic. Détails
dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Créer le bot Discord (à faire avant l'installation)

1. https://discord.com/developers/applications → **New Application**.
2. Onglet **Bot** → **Reset Token**, garde-le de côté (jamais commité, jamais partagé).
   Désactive **Public Bot** (usage perso).
3. Onglet **Installation** → **Install Link** → **None** (obligatoire pour une appli
   privée).
4. Onglet **OAuth2** → **URL Generator** → coche les scopes `bot` **et**
   `applications.commands` (les deux, sinon les commandes n'apparaissent jamais côté
   Discord) → coche au minimum `Send Messages`, `Manage Channels`, `Embed Links`,
   `Read Message History` dans les permissions bot.
5. Ouvre l'URL générée, choisis ton serveur, autorise.

## Installation

Deux façons de faire tourner le bot : **Docker** (recommandé — même procédure partout,
Windows/Mac/Linux/Raspberry Pi, pas de version de Python à gérer) ou **installation
manuelle** (Python directement, utile pour développer sur le code).

Dans les deux cas, commence par :

```bash
git clone https://github.com/Swaksm/CordeSortie.git
cd CordeSortie
cp .env.example .env
```

Puis édite `.env` et renseigne `DISCORD_TOKEN` (récupéré à l'étape précédente).

### Option A — Docker (recommandé, marche aussi sur Raspberry Pi 64 bits)

```bash
docker compose up -d --build
```

C'est tout. Le bot tourne en arrière-plan, redémarre automatiquement si le process
crash ou si la machine reboot (`restart: unless-stopped`), et sa config/DB persiste
dans `./data` sur l'hôte (`docker-compose.yml`).

```bash
docker compose logs -f      # suivre les logs en direct
docker compose down         # arrêter
docker compose up -d --build   # relancer après une mise à jour du code
```

Build et démarrage testés en local (Windows + Docker Desktop) : connexion Discord,
sync des commandes et persistance du volume `./data` vérifiées de bout en bout.

**Raspberry Pi** : nécessite un **OS 64 bits** (Raspberry Pi OS Bookworm 64 bits ou
équivalent) — Playwright/Chromium n'a pas de build pour l'ARM 32 bits. Un Pi 4 ou 5 est
recommandé (Chromium headless est gourmand en RAM, un Pi 3 fonctionnera mais lentement).
Installe Docker avec le script officiel puis suis exactement la même procédure :

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # puis se reconnecter (ou `newgrp docker`)
git clone https://github.com/Swaksm/CordeSortie.git
cd CordeSortie
cp .env.example .env   # puis éditer DISCORD_TOKEN
docker compose up -d --build
```

Non testé sur du vrai matériel ARM dans ce dépôt (validé sur x86_64 uniquement) — mais
l'image de base (`python:3.13-slim`) et les binaires Chromium de Playwright sont tous
les deux distribués en multi-architecture (x86_64/arm64), donc `docker compose` doit
récupérer automatiquement les bonnes variantes sans rien à changer à la config.

### Option B — Installation manuelle (Python direct)

Nécessite Python 3.12+. Sur Debian/Raspberry Pi OS Bookworm, le `python3` par défaut
est en 3.11 — installe une version plus récente via [pyenv](https://github.com/pyenv/pyenv)
ou utilise plutôt l'option Docker ci-dessus, plus simple sur ce point.

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash) — .venv/bin/activate sur Linux/Mac/RPi
pip install -r requirements.txt
playwright install --with-deps chromium   # --with-deps installe aussi les libs système
```

Puis lance :

```bash
python -m cordesortie
```

Pour le faire tourner en permanence sur un Raspberry Pi sans Docker (démarre au boot,
redémarre s'il crash), un service systemd (adapte `User=` et les chemins à ton
installation — les Raspberry Pi OS récents ne créent plus d'utilisateur `pi` par
défaut, vérifie avec `whoami`) :

```ini
# /etc/systemd/system/cordesortie.service
[Unit]
Description=CordeSortie Discord bot
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/CordeSortie
ExecStart=/home/pi/CordeSortie/.venv/bin/python -m cordesortie
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cordesortie
journalctl -u cordesortie -f   # suivre les logs
```

## Premiers pas

Au premier démarrage, le bot crée automatiquement une catégorie **CordeSortie** avec
un salon tableau de bord, un salon d'aide (`cordesortie-aide` liste toutes les
commandes disponibles, toujours à jour) et un salon log (flux d'évènements du bot).

1. `/filtre add name:test` — choisis les sites dans le menu, puis remplis juste
   "Doit contenir TOUS ces mots" avec `pokemon` dans le formulaire qui s'ouvre (large,
   pour voir le système fonctionner).
2. `/filtre dry-run name:test` — scrape en direct et montre ce qui matcherait, sans
   créer d'alertes ni toucher à la dédup.
3. Une fois convaincu, affine les conditions avec `/filtre edit` et laisse tourner —
   les alertes arrivent dans le salon dédié au filtre (avec ghost ping).
4. `/sites` pour voir le statut de chaque site, `/pause` pour tout arrêter en urgence.

Liste complète des commandes : salon `cordesortie-aide` une fois le bot lancé, ou
`docs/`.

## Déploiement cloud

Le déploiement sur une plateforme cloud (Render/Railway/Oracle Cloud) est en pause,
priorité donnée à la fiabilité en local/Raspberry Pi d'abord — voir
[docs/TASKS.md](docs/TASKS.md) Phase 8 pour le pourquoi et l'état des options
explorées. Le même `Dockerfile`/`docker-compose.yml` s'y prêteraient directement le
jour où c'est repris.

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

CI GitHub Actions sur chaque push (lint + tests + couverture) — voir
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## Usage prévu

Outil de veille personnelle, pas un outil d'achat automatique. Voir la section
"Risque légal" de [docs/RISKS.md](docs/RISKS.md) avant tout déploiement à plus grande
échelle.
